"""
Let It Flow - user snapshot.

Gathers everything about ONE user (profile, cycles, ML estimate, irregularity
analysis, current phase, recent logs) into a single dictionary.  The dashboard,
chatbot and PDF report all use this, so they always agree with each other.
"""
from datetime import date, timedelta

import repository as repo
from prediction.cycle_prediction import (cycle_day_and_phase, cycle_intervals,
                                          predict_next_period)
from prediction.irregularity_analysis import analyze_cycles


def average_period_length(cycles):
    """Average bleeding days from logged start/end dates (None if no end dates)."""
    lengths = [(c["period_end"] - c["period_start"]).days + 1 for c in cycles
               if c.get("period_end") and c["period_end"] >= c["period_start"]]
    return round(sum(lengths) / len(lengths), 1) if lengths else None


def build_snapshot(user_id, today=None):
    today = today or date.today()
    user = repo.get_user(user_id)
    profile = repo.get_profile(user_id)
    cycles = repo.list_cycles(user_id)                       # newest first
    starts = sorted(c["period_start"] for c in cycles)

    prediction = predict_next_period(starts, profile.get("typical_cycle_length"), today)

    symptoms = repo.list_symptoms(user_id, limit=60)
    flows = repo.list_flow(user_id, limit=60)
    lifestyle = repo.list_lifestyle(user_id, limit=90)
    flow_by_date = {f["log_date"]: f["flow_intensity"] for f in flows}

    # recent (last 45 days) pain / bleeding values for the safety rules
    cutoff = today - timedelta(days=45)
    recent = [{"pain_severity": s["pain_severity"], "bleeding_intensity": flow_by_date.get(s["log_date"])}
              for s in symptoms if s["log_date"] >= cutoff]
    recent += [{"pain_severity": None, "bleeding_intensity": v}
               for d, v in flow_by_date.items() if d >= cutoff and d not in {s["log_date"] for s in symptoms}]

    avg_period = average_period_length(cycles)
    period_len = avg_period or profile.get("period_duration")

    analysis = analyze_cycles(
        starts, age=user.get("age"), today=today, period_length=period_len,
        self_regularity=profile.get("self_regularity"),
        self_missed=(None if profile.get("has_missed_periods") is None
                     else bool(profile["has_missed_periods"])),
        recent_symptoms=recent)

    expected_len = (prediction["predicted_length"] or profile.get("typical_cycle_length") or 29)
    last_start = starts[-1] if starts else None
    cycle_day, phase = cycle_day_and_phase(last_start, expected_len, period_len or 5, today)

    return {
        "today": today, "user": user, "profile": profile, "cycles": cycles, "starts": starts,
        "intervals": cycle_intervals(starts), "prediction": prediction, "analysis": analysis,
        "avg_period_length": avg_period, "period_length": period_len,
        "expected_length": expected_len, "last_start": last_start,
        "cycle_day": cycle_day, "phase": phase,
        "symptoms": symptoms, "flows": flows, "lifestyle": lifestyle,
        "diet_pref": repo.get_diet_pref(user_id), "exercise_pref": repo.get_exercise_pref(user_id),
    }
