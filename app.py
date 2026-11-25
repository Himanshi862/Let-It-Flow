"""
Let It Flow - main Flask application.

Run:   python app.py              (starts the website on http://127.0.0.1:5000)
Other: python app.py --init-db    (only create the database tables)

Security summary (also explained in README.md)
  * Passwords are hashed (Werkzeug, salted) - never stored as plain text.
  * login_required protects every private page; user id comes from the signed
    SESSION, never from the URL or the form.
  * Every SQL query is parameterised and filtered by user_id (see repository.py).
  * CSRF token is required on every POST request.
  * Session cookie is HttpOnly + SameSite=Lax; session is cleared on login/logout.
  * Basic login throttling, security headers, and a Content-Security-Policy.
"""
import calendar
import csv
import io
import json
import math
import os
import re
import secrets
import sys
import time
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (Flask, Response, abort, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import repository as repo
from chatbot.chatbot import reply as chatbot_reply
from config import Config
from database import close_db, init_db, is_integrity_error
from insights.lifestyle import build_insights
from insights.recommendations import PHASE_TEXT, build_recommendations
from prediction.cycle_prediction import PHASES
from reports.generate_report import generate_pdf
from snapshot import build_snapshot

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config.from_object(Config)
app.teardown_appcontext(close_db)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# =========================================================== small helpers
def load_metrics():
    path = os.path.join(BASE_DIR, "models", "metrics.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def parse_date(value):
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def to_int(value, lo, hi):
    """Return an int within [lo, hi] or None if empty/invalid."""
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return n if lo <= n <= hi else None


def to_float(value, lo, hi):
    try:
        n = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return n if lo <= n <= hi else None


def clean_text(value, limit=255):
    return (value or "").strip()[:limit] or None


def valid_period_start(d):
    """A period start must not be in the future or absurdly old."""
    today = date.today()
    return d is not None and d <= today and d >= today - timedelta(days=365 * 6)


# ============================================================= security
def current_user_id():
    return session.get("user_id")


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        uid = current_user_id()
        if not uid or repo.get_user(uid) is None:
            session.clear()
            flash("Please log in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@app.before_request
def protect_post_requests():
    """Reject any POST that does not carry the session's secret CSRF token."""
    if request.method == "POST":
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
            abort(400, "Your session expired. Please go back, refresh the page and try again.")


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data:; frame-ancestors 'none'")
    if current_user_id():                       # private pages must not be cached
        resp.headers["Cache-Control"] = "no-store"
    return resp


_failed_logins = {}                             # (ip, email) -> [timestamps]


def too_many_attempts(key):
    now = time.time()
    attempts = [t for t in _failed_logins.get(key, []) if now - t < 600]
    _failed_logins[key] = attempts
    return len(attempts) >= 5


# ============================================================ templating
app.jinja_env.globals["csrf_token"] = csrf_token      # also visible inside macros


@app.context_processor
def inject_globals():
    uid = current_user_id()
    user = repo.get_user(uid) if uid else None
    return {"current_user": user, "today": date.today(),
            "PHASES": PHASES, "app_name": "Let It Flow"}


ICON_NAMES = set()


@app.template_global("icon")
def icon(name, cls="icon"):
    """Inline SVG icon from the sprite defined in templates/base.html."""
    from markupsafe import Markup, escape
    return Markup(f'<svg class="{escape(cls)}" aria-hidden="true"><use href="#i-{escape(name)}"/></svg>')


@app.template_filter("d")
def fmt_date(value):
    return value.strftime("%d %b %Y") if value else "-"


@app.template_filter("ds")
def fmt_short(value):
    return value.strftime("%d %b") if value else "-"


# ============================================================ public pages
@app.route("/")
def landing():
    if current_user_id():
        return redirect(url_for("dashboard"))
    # the ring on the landing page is only an ILLUSTRATION (day 12 of a 29-day cycle)
    return render_template("landing.html", dial=dial_geometry(12, 29, 5))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = clean_text(request.form.get("name"), 100)
        age = to_int(request.form.get("age"), 12, 60)
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        errors = []
        if not name:
            errors.append("Please enter your name.")
        if age is None:
            errors.append("Please enter a valid age (12-60).")
        if not EMAIL_RE.match(email) or len(email) > 190:
            errors.append("Please enter a valid email address.")
        if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            errors.append("Password needs at least 8 characters, with letters and numbers.")
        if password != request.form.get("password2"):
            errors.append("The two passwords do not match.")
        if not errors:
            try:
                uid = repo.create_user(name, age, email, generate_password_hash(password))
            except Exception as exc:                          # duplicate email
                if is_integrity_error(exc):
                    errors.append("An account with this email already exists. Try logging in.")
                else:
                    raise
            else:
                session.clear()
                session["user_id"] = uid
                session.permanent = True
                flash("Welcome to Let It Flow! Let's set things up - skip anything you don't know.", "success")
                return redirect(url_for("onboarding"))
        for e in errors:
            flash(e, "error")
        return render_template("register.html", form=request.form), 400
    return render_template("register.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        key = (request.remote_addr, email)
        if too_many_attempts(key):
            flash("Too many failed attempts. Please wait 10 minutes and try again.", "error")
            return render_template("login.html"), 429
        user = repo.get_user_by_email(email) if email else None
        if user and check_password_hash(user["password_hash"], password):
            nxt = request.args.get("next", "")
            session.clear()                                   # prevents session fixation
            session["user_id"] = user["id"]
            session.permanent = True
            _failed_logins.pop(key, None)
            profile = repo.get_profile(user["id"])
            if not profile["onboarding_done"]:
                return redirect(url_for("onboarding"))
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
        _failed_logins.setdefault(key, []).append(time.time())
        flash("Email or password is not correct.", "error")      # same message for both cases
        return render_template("login.html"), 401
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("landing"))


# ============================================================ onboarding
ONBOARDING_STEPS = 3


@app.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    uid = current_user_id()
    step = to_int(request.args.get("step", 1), 1, ONBOARDING_STEPS) or 1
    if request.method == "POST":
        action = request.form.get("action", "save")
        if action == "save":
            if step == 1:
                added = 0
                for key in request.form.getlist("past_dates"):
                    d = parse_date(key)
                    if valid_period_start(d) and repo.add_cycle(uid, d):
                        added += 1
                if added:
                    flash(f"Saved {added} period date(s).", "success")
            elif step == 2:
                save_cycle_profile(uid, request.form)
            elif step == 3:
                save_college_profile(uid, request.form)
        if step >= ONBOARDING_STEPS:
            repo.save_profile(uid, onboarding_done=1)
            flash("You're all set. You can add or change anything later in Profile.", "success")
            return redirect(url_for("dashboard"))
        return redirect(url_for("onboarding", step=step + 1))
    return render_template("onboarding.html", step=step, steps=ONBOARDING_STEPS,
                           profile=repo.get_profile(uid), diet=repo.get_diet_pref(uid),
                           exercise=repo.get_exercise_pref(uid), cycles=repo.list_cycles(uid))


def save_cycle_profile(uid, form):
    missed = form.get("has_missed_periods")
    repo.save_profile(
        uid,
        typical_cycle_length=to_int(form.get("typical_cycle_length"), 15, 90),
        period_duration=to_int(form.get("period_duration"), 1, 15),
        self_regularity=form.get("self_regularity") if form.get("self_regularity") in
        ("regular", "slightly_irregular", "highly_irregular") else None,
        has_missed_periods={"yes": 1, "no": 0}.get(missed))


def save_college_profile(uid, form):
    repo.save_profile(
        uid,
        residence=form.get("residence") if form.get("residence") in ("hostel", "day_scholar") else None,
        sleep_routine=form.get("sleep_routine") if form.get("sleep_routine") in
        ("regular", "irregular", "night_owl") else None,
        attendance_impact=form.get("attendance_impact") if form.get("attendance_impact") in
        ("never", "sometimes", "often") else None)
    diet = form.get("diet_type")
    repo.save_diet_pref(uid, diet if diet in ("vegetarian", "eggetarian", "non_vegetarian", "vegan") else None,
                        clean_text(form.get("dislikes")),
                        {"yes": 1, "no": 0}.get(form.get("skips_meals_often")))
    ex = form.get("preferred_exercise")
    act = form.get("activity_level")
    repo.save_exercise_pref(uid, ex if ex in ("walking", "yoga", "gym", "home", "cardio") else None,
                            act if act in ("sedentary", "moderate", "high") else None)


# ============================================================ dashboard
def dial_geometry(day, expected_len, period_len):
    """Numbers the SVG cycle ring needs (4 coloured arcs + a marker for today)."""
    C = 2 * math.pi * 66
    expected_len = max(expected_len or 29, 20)
    period_len = min(max(period_len or 5, 2), 10)
    mid = max(period_len + 2, expected_len - 14)
    parts = [("menstrual", period_len), ("follicular", mid - 1 - period_len),
             ("ovulatory", 3), ("luteal", expected_len - (mid + 2))]
    parts = [(k, max(v, 1)) for k, v in parts]
    total = sum(v for _, v in parts)
    arcs, start = [], 0.0
    for key, v in parts:
        length = C * v / total
        arcs.append({"key": key, "dash": round(length - 3, 2), "gap": round(C - length + 3, 2),
                     "offset": round(-start, 2)})
        start += length
    marker = None
    if day:
        frac = min(day / total, 1.0)
        ang = 2 * math.pi * frac - math.pi / 2
        marker = {"x": round(80 + 66 * math.cos(ang), 1), "y": round(80 + 66 * math.sin(ang), 1)}
    return {"arcs": arcs, "marker": marker, "circumference": round(C, 1)}


def greeting():
    h = datetime.now().hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"


@app.route("/dashboard")
@login_required
def dashboard():
    uid = current_user_id()
    snap = build_snapshot(uid)
    rec = build_recommendations(
        snap["phase"] or "follicular", snap["diet_pref"].get("diet_type"), snap["diet_pref"].get("dislikes"),
        snap["exercise_pref"].get("activity_level"), snap["exercise_pref"].get("preferred_exercise"),
        snap["diet_pref"].get("skips_meals_often"), snap["symptoms"])
    day = snap["cycle_day"]
    dial = dial_geometry(day, snap["expected_length"], snap["period_length"]) if day else None
    last_life = snap["lifestyle"][0] if snap["lifestyle"] else None
    today_log = repo.get_day(uid, date.today())
    return render_template("dashboard.html", snap=snap, rec=rec, dial=dial, greeting=greeting(),
                           last_life=last_life, today_log=today_log, pred=snap["prediction"],
                           analysis=snap["analysis"])


@app.route("/quick-log", methods=["POST"])
@login_required
def quick_log():
    """Dashboard 'Today's check-in': chips + pain level -> today's symptom log."""
    uid = current_user_id()
    chosen = set(request.form.getlist("sym"))
    pain = to_int(request.form.get("pain"), 0, 10)
    symptoms = {"pain_severity": pain}
    for key in ("mood", "fatigue", "bloating", "acne", "headache"):
        symptoms[key] = 2 if key in chosen else 0
    if pain is None and not chosen:
        flash("Pick at least one thing to log, or use the full Daily Log.", "info")
        return redirect(url_for("dashboard"))
    existing = repo.get_day(uid, date.today())["symptoms"]
    if existing:                                  # keep notes already written today
        symptoms["notes"] = existing.get("notes")
    repo.save_daily_log(uid, date.today(), symptoms=symptoms)
    flash("Today's check-in saved.", "success")
    return redirect(url_for("dashboard"))


# ============================================================ tracker
def month_grid(year, month, snap, selected):
    """Build the calendar weeks with CSS classes for logged / predicted days."""
    cal = calendar.Calendar(firstweekday=0)               # Monday first
    pred = snap["prediction"]
    avg_len = int(round(snap["period_length"] or 5))
    period_days, assumed_days = set(), set()
    for c in snap["cycles"]:
        if c.get("period_end") and c["period_end"] >= c["period_start"]:
            d = c["period_start"]
            while d <= c["period_end"]:
                period_days.add(d)
                d += timedelta(days=1)
        else:
            period_days.add(c["period_start"])
            for i in range(1, avg_len):
                assumed_days.add(c["period_start"] + timedelta(days=i))
    for f in snap["flows"]:
        period_days.add(f["log_date"])
    log_days = {s["log_date"] for s in snap["symptoms"]} | {l["log_date"] for l in snap["lifestyle"]}
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        row = []
        for d in week:
            cls = []
            if d.month != month:
                cls.append("other")
            if d in period_days:
                cls.append("period")
            elif d in assumed_days:
                cls.append("period-assumed")
            if pred["available"]:
                if d == pred["next_start"]:
                    cls.append("predicted")
                elif pred["range_start"] <= d <= pred["range_end"]:
                    cls.append("predicted-window")
            if d == date.today():
                cls.append("today")
            if d == selected:
                cls.append("selected")
            row.append({"date": d, "cls": " ".join(cls), "has_log": d in log_days})
        weeks.append(row)
    return weeks


@app.route("/tracker")
@login_required
def tracker():
    uid = current_user_id()
    snap = build_snapshot(uid)
    today = date.today()
    sel = parse_date(request.args.get("day")) or today
    ym = request.args.get("month")
    try:
        year, month = (int(x) for x in ym.split("-")) if ym else (sel.year, sel.month)
        date(year, month, 1)
    except (ValueError, AttributeError):
        year, month = today.year, today.month
    first = date(year, month, 1)
    prev_month = (first - timedelta(days=1)).replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)
    day_info = repo.get_day(uid, sel)
    sel_cycle = next((c for c in snap["cycles"] if c["period_start"] == sel), None)
    # table rows: gap since previous start
    rows, ordered = [], sorted(snap["cycles"], key=lambda c: c["period_start"])
    for i, c in enumerate(ordered):
        gap = (c["period_start"] - ordered[i - 1]["period_start"]).days if i else None
        rows.append({**c, "gap": gap,
                     "bleed": ((c["period_end"] - c["period_start"]).days + 1) if c.get("period_end") else None})
    rows.reverse()
    return render_template("tracker.html", snap=snap, weeks=month_grid(year, month, snap, sel),
                           month_label=first.strftime("%B %Y"), prev_month=prev_month.strftime("%Y-%m"),
                           next_month=next_month.strftime("%Y-%m"), sel=sel, day_info=day_info,
                           sel_cycle=sel_cycle, rows=rows, pred=snap["prediction"])


def _read_cycle_form(form):
    start = parse_date(form.get("period_start"))
    end = parse_date(form.get("period_end")) if form.get("period_end") else None
    if not valid_period_start(start):
        return None, None, "Please choose a valid period start date (not in the future)."
    if end and (end < start or (end - start).days > 14):
        return None, None, "The end date must be on or after the start date, within 15 days."
    return start, end, None


@app.route("/tracker/add", methods=["POST"])
@login_required
def tracker_add():
    uid = current_user_id()
    start, end, err = _read_cycle_form(request.form)
    if err:
        flash(err, "error")
    elif repo.add_cycle(uid, start, end, clean_text(request.form.get("notes"))):
        flash(f"Period starting {start:%d %b %Y} saved.", "success")
    else:
        flash("That start date is already in your history.", "info")
    return redirect(request.referrer or url_for("tracker"))


@app.route("/tracker/start-today", methods=["POST"])
@login_required
def tracker_start_today():
    uid = current_user_id()
    if repo.add_cycle(uid, date.today()):
        flash("Marked today as the first day of your period.", "success")
    else:
        flash("Today is already logged as a period start.", "info")
    return redirect(url_for("dashboard"))


@app.route("/tracker/<int:cycle_id>/edit", methods=["POST"])
@login_required
def tracker_edit(cycle_id):
    uid = current_user_id()
    if not repo.get_cycle(uid, cycle_id):
        abort(404)
    start, end, err = _read_cycle_form(request.form)
    if err:
        flash(err, "error")
    elif repo.update_cycle(uid, cycle_id, start, end, clean_text(request.form.get("notes"))):
        flash("Period entry updated.", "success")
    else:
        flash("Another entry already uses that start date.", "error")
    return redirect(url_for("tracker"))


@app.route("/tracker/<int:cycle_id>/delete", methods=["POST"])
@login_required
def tracker_delete(cycle_id):
    uid = current_user_id()
    if not repo.get_cycle(uid, cycle_id):
        abort(404)
    repo.delete_cycle(uid, cycle_id)
    flash("Period entry deleted.", "info")
    return redirect(url_for("tracker"))


# ============================================================ prediction
@app.route("/prediction")
@login_required
def prediction_page():
    snap = build_snapshot(current_user_id())
    metrics = load_metrics()
    m3 = metrics["models"]["lags3"] if metrics else None
    return render_template("prediction.html", snap=snap, pred=snap["prediction"], metrics=metrics, m3=m3,
                           history=[{"label": i["end"].strftime("%d %b"), "days": i["days"]}
                                    for i in snap["analysis"]["intervals"] if 15 <= i["days"] <= 90])


# ===================================================== cycle intelligence
@app.route("/intelligence")
@login_required
def intelligence():
    uid = current_user_id()
    snap = build_snapshot(uid)
    ana = snap["analysis"]
    stats = ana["stats"]
    repo.save_analysis_snapshot(
        uid, ana["status"], stats.get("n_cycles"), stats.get("mean"), stats.get("std"),
        snap["prediction"]["next_start"] if snap["prediction"]["available"] else None,
        ana["headline"][:1000])
    chart = [{"label": i["end"].strftime("%d %b"), "days": i["days"], "flag": i["flag"]}
             for i in ana["intervals"]]
    return render_template("intelligence.html", snap=snap, ana=ana, chart=chart,
                           history=repo.list_analysis_history(uid))


# ============================================================ daily log
@app.route("/log", methods=["GET", "POST"])
@login_required
def daily_log():
    uid = current_user_id()
    log_date = parse_date(request.values.get("date")) or date.today()
    if log_date > date.today():
        log_date = date.today()
    if request.method == "POST":
        f = request.form
        symptoms = {
            "pain_severity": to_int(f.get("pain_severity"), 0, 10),
            "mood": to_int(f.get("mood"), 0, 3), "fatigue": to_int(f.get("fatigue"), 0, 3),
            "bloating": to_int(f.get("bloating"), 0, 3), "acne": to_int(f.get("acne"), 0, 3),
            "headache": to_int(f.get("headache"), 0, 3), "notes": clean_text(f.get("notes")),
        }
        lifestyle = {
            "sleep_hours": to_float(f.get("sleep_hours"), 0, 24), "stress_level": to_int(f.get("stress_level"), 1, 5),
            "exercise_minutes": to_int(f.get("exercise_minutes"), 0, 600),
            "exercise_type": clean_text(f.get("exercise_type"), 60),
            "meals_skipped": to_int(f.get("meals_skipped"), 0, 5),
            "water_litres": to_float(f.get("water_litres"), 0, 10),
            "exam_period": 1 if f.get("exam_period") else 0, "note": clean_text(f.get("life_note")),
        }
        flow = to_int(f.get("flow"), 1, 5)
        has_sym = any(v is not None for k, v in symptoms.items())
        has_life = any(v not in (None, 0) for v in lifestyle.values())
        if not (has_sym or has_life or flow):
            flash("Nothing to save yet - fill in at least one field.", "info")
        else:
            repo.save_daily_log(uid, log_date, symptoms if has_sym else None,
                                lifestyle if has_life else None, flow)
            flash(f"Log for {log_date:%d %b %Y} saved.", "success")
        return redirect(url_for("daily_log", date=log_date.isoformat()))
    day = repo.get_day(uid, log_date)
    recent = sorted(set([s["log_date"] for s in repo.list_symptoms(uid, 30)] +
                       [l["log_date"] for l in repo.list_lifestyle(uid, 30)] +
                       [f["log_date"] for f in repo.list_flow(uid, 30)]), reverse=True)[:10]
    # blank defaults so the form template can safely read every field
    s = day["symptoms"] or {k: None for k in ("pain_severity", "mood", "fatigue", "bloating", "acne", "headache", "notes")}
    l = day["lifestyle"] or {k: None for k in ("sleep_hours", "stress_level", "exercise_minutes", "exercise_type",
                                                "meals_skipped", "water_litres", "exam_period", "note")}
    f = day["flow"] or {"flow_intensity": None}
    return render_template("log.html", log_date=log_date, day=day, recent=recent, s=s, l=l, f=f)


@app.route("/log/delete", methods=["POST"])
@login_required
def delete_log():
    d = parse_date(request.form.get("date"))
    if d:
        repo.delete_day(current_user_id(), d)
        flash(f"Log for {d:%d %b %Y} deleted.", "info")
    return redirect(url_for("daily_log"))


# ============================================================ insights etc.
@app.route("/insights")
@login_required
def insights_page():
    snap = build_snapshot(current_user_id())
    return render_template("insights.html", snap=snap, ins=build_insights(snap))


@app.route("/nutrition")
@login_required
def nutrition():
    snap = build_snapshot(current_user_id())
    phase = request.args.get("phase")
    if phase not in PHASE_TEXT:
        phase = snap["phase"] or "follicular"
    rec = build_recommendations(
        phase, snap["diet_pref"].get("diet_type"), snap["diet_pref"].get("dislikes"),
        snap["exercise_pref"].get("activity_level"), snap["exercise_pref"].get("preferred_exercise"),
        snap["diet_pref"].get("skips_meals_often"), snap["symptoms"],
        extra_dislikes=request.args.get("exclude", "")[:120])
    return render_template("nutrition.html", snap=snap, rec=rec, phase=phase,
                           exclude=request.args.get("exclude", "")[:120])


@app.route("/learn")
@login_required
def learn():
    return render_template("learn.html")


# ============================================================ chatbot
@app.route("/assistant")
@login_required
def assistant():
    uid = current_user_id()
    conv_id = to_int(request.args.get("c"), 1, 10 ** 9)
    conv = repo.get_conversation(uid, conv_id) if conv_id else None   # None if not YOUR chat
    messages = repo.list_messages(uid, conv["id"]) if conv else []
    return render_template("assistant.html", conv=conv, messages=messages,
                           conversations=repo.list_conversations(uid), snap_name=repo.get_user(uid)["name"].split(" ")[0])


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    uid = current_user_id()
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()[:500]
    if not message:
        return jsonify(error="Please type a message."), 400
    conv_id = to_int(data.get("conversation_id"), 1, 10 ** 9)
    conv = repo.get_conversation(uid, conv_id) if conv_id else None
    if conv is None:
        conv_id = repo.create_conversation(uid, message)
        history = []
    else:
        history = [{"role": m["role"], "content": m["content"]} for m in repo.list_messages(uid, conv_id)][-6:]
    answer, intent = chatbot_reply(uid, message, conv_id, history)
    repo.add_message(uid, conv_id, "user", message)
    repo.add_message(uid, conv_id, "bot", answer, intent)
    return jsonify(reply=answer, conversation_id=conv_id, intent=intent)


@app.route("/assistant/<int:conv_id>/delete", methods=["POST"])
@login_required
def delete_conversation(conv_id):
    repo.delete_conversation(current_user_id(), conv_id)
    flash("Conversation deleted.", "info")
    return redirect(url_for("assistant"))


# ============================================================ reports
@app.route("/reports")
@login_required
def reports():
    snap = build_snapshot(current_user_id())
    return render_template("reports.html", snap=snap, ana=snap["analysis"], pred=snap["prediction"])


@app.route("/reports/download.pdf")
@login_required
def report_pdf():
    pdf = generate_pdf(build_snapshot(current_user_id()))
    return Response(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=let-it-flow-report-{date.today().isoformat()}.pdf"})


@app.route("/reports/download.csv")
@login_required
def report_csv():
    """All of the user's own records in one 'long format' CSV."""
    uid = current_user_id()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["record_type", "date", "field", "value"])
    for c in reversed(repo.list_cycles(uid)):
        w.writerow(["period", c["period_start"], "period_end", c["period_end"] or ""])
    for s in reversed(repo.list_symptoms(uid)):
        for k in ("pain_severity", "mood", "fatigue", "bloating", "acne", "headache", "notes"):
            if s.get(k) is not None:
                w.writerow(["symptom", s["log_date"], k, s[k]])
    for f in reversed(repo.list_flow(uid)):
        w.writerow(["flow", f["log_date"], "flow_intensity", f["flow_intensity"]])
    for l in reversed(repo.list_lifestyle(uid)):
        for k in ("sleep_hours", "stress_level", "exercise_minutes", "exercise_type", "meals_skipped",
                  "water_litres", "exam_period", "note"):
            if l.get(k) is not None:
                w.writerow(["lifestyle", l["log_date"], k, l[k]])
    return Response(out.getvalue(), mimetype="text/csv", headers={
        "Content-Disposition": "attachment; filename=let-it-flow-my-data.csv"})


# ======================================================= profile & settings
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    uid = current_user_id()
    if request.method == "POST":
        section = request.form.get("section")
        if section == "basic":
            name = clean_text(request.form.get("name"), 100)
            age = to_int(request.form.get("age"), 12, 60)
            if name and age:
                repo.update_user_basic(uid, name, age)
                flash("Basic details updated.", "success")
            else:
                flash("Please enter a name and a valid age (12-60).", "error")
        elif section == "cycle":
            save_cycle_profile(uid, request.form)
            flash("Cycle details updated.", "success")
        elif section == "college":
            save_college_profile(uid, request.form)
            flash("College and lifestyle details updated.", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=repo.get_user(uid), profile=repo.get_profile(uid),
                           diet=repo.get_diet_pref(uid), exercise=repo.get_exercise_pref(uid))


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", metrics=load_metrics())


@app.route("/settings/password", methods=["POST"])
@login_required
def change_password():
    uid = current_user_id()
    user = repo.get_user_by_email(repo.get_user(uid)["email"])
    new = request.form.get("new_password") or ""
    if not check_password_hash(user["password_hash"], request.form.get("current_password") or ""):
        flash("Current password is not correct.", "error")
    elif len(new) < 8 or not re.search(r"[A-Za-z]", new) or not re.search(r"\d", new):
        flash("New password needs at least 8 characters, with letters and numbers.", "error")
    elif new != request.form.get("new_password2"):
        flash("The new passwords do not match.", "error")
    else:
        repo.update_password(uid, generate_password_hash(new))
        flash("Password changed.", "success")
    return redirect(url_for("settings"))


def _password_ok(uid, password):
    user = repo.get_user_by_email(repo.get_user(uid)["email"])
    return check_password_hash(user["password_hash"], password or "")


@app.route("/settings/delete-logs", methods=["POST"])
@login_required
def delete_logs():
    uid = current_user_id()
    if not _password_ok(uid, request.form.get("password")):
        flash("Password is not correct - nothing was deleted.", "error")
    else:
        repo.delete_all_logs(uid)
        flash("All your period dates, logs, analysis history and chats were deleted.", "info")
    return redirect(url_for("settings"))


@app.route("/settings/delete-account", methods=["POST"])
@login_required
def delete_account():
    uid = current_user_id()
    if request.form.get("confirm") != "DELETE" or not _password_ok(uid, request.form.get("password")):
        flash("Type DELETE and enter your password to delete your account.", "error")
        return redirect(url_for("settings"))
    repo.delete_user(uid)
    session.clear()
    flash("Your account and all of its data were deleted.", "info")
    return redirect(url_for("landing"))


# ============================================================ errors
@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, message=getattr(e, "description", "Bad request")), 400


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="We couldn't find that page."), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="Something went wrong on our side."), 500


# ============================================================ start-up
def prepare_database():
    try:
        init_db(app)
    except Exception as exc:                                      # friendly message for beginners
        print("\n[Let It Flow] Could not set up the database:", exc)
        if app.config["DB_BACKEND"] == "mysql":
            print("  -> Is MySQL running? Check MYSQL_USER / MYSQL_PASSWORD in your .env file.")
            print("  -> Want a quick test without MySQL?  set DB_BACKEND=sqlite in .env\n")
        sys.exit(1)


if __name__ == "__main__":
    prepare_database()
    if "--init-db" in sys.argv:
        print("Database ready.")
        sys.exit(0)
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
