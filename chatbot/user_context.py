"""
Let It Flow chatbot - user context (Stage 8)

Builds a small dictionary of RECORDED FACTS about the logged-in user, straight
from the database.  The chatbot only ever states these as facts; everything
else it says is labelled as general information.

SAFETY: build_user_context(user_id) only reads rows WHERE user_id = that
user (through snapshot.py / repository.py).  There is no code path that can
mix two accounts.
"""
from datetime import timedelta

from snapshot import build_snapshot


def _avg(values):
    values = [v for v in values if v is not None]
    return (sum(values) / len(values), len(values)) if values else (None, 0)


def build_user_context(user_id):
    snap = build_snapshot(user_id)
    today = snap["today"]
    last14 = today - timedelta(days=14)
    last30 = today - timedelta(days=30)

    sym14 = [s for s in snap["symptoms"] if s["log_date"] >= last14]
    sym30 = [s for s in snap["symptoms"] if s["log_date"] >= last30]
    life14 = [l for l in snap["lifestyle"] if l["log_date"] >= last14]

    usable = [i for i in snap["intervals"] if 15 <= i <= 60]
    ctx = {
        "snapshot": snap,
        "name": (snap["user"]["name"] or "").split(" ")[0] or "there",
        "starts": snap["starts"],
        "last_start": snap["last_start"],
        "usable_intervals": usable,
        "mean_cycle": round(sum(usable) / len(usable), 1) if usable else None,
        "days_since_last": (today - snap["last_start"]).days if snap["last_start"] else None,
        "prediction": snap["prediction"],
        "analysis": snap["analysis"],
        "phase": snap["phase"], "cycle_day": snap["cycle_day"],
        "pain": _avg([s["pain_severity"] for s in sym14]),
        "sym30": sym30,
        "sleep": _avg([float(l["sleep_hours"]) if l["sleep_hours"] is not None else None for l in life14]),
        "stress": _avg([l["stress_level"] for l in life14]),
        "exercise": _avg([l["exercise_minutes"] for l in life14]),
        "profile": snap["profile"], "diet_pref": snap["diet_pref"], "exercise_pref": snap["exercise_pref"],
    }
    return ctx


def days_logged(ctx, key):
    """How many of the last 30 days had this symptom at level 2 or 3 ('moderate'/'strong')."""
    return sum(1 for s in ctx["sym30"] if (s.get(key) or 0) >= 2)
