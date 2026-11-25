"""
Let It Flow - Student Lifestyle Insights (Stage 7)

Looks for ASSOCIATIONS between what a user logs (sleep, stress, exam periods,
exercise, skipped meals) and (a) how she feels (pain, fatigue, headache,
bloating) and (b) how long her cycles are.

IMPORTANT HONESTY RULES
  * Correlation is not cause.  Every message says "associated with".
  * Small samples are flagged as tentative.
  * With too little data we say so instead of showing a number.
  * The primary-survey numbers describe 33 students only - they are NOT
    established medical facts.
"""
import json
import os

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_PAIRED_DAYS = 10          # fewer paired days than this -> no correlation shown
MIN_CYCLES = 4                # fewer cycles with lifestyle data -> no cycle-level analysis


def _spearman(x, y):
    """Spearman rank correlation without needing scipy."""
    x, y = pd.Series(x).rank(), pd.Series(y).rank()
    if x.std() == 0 or y.std() == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _strength(rho):
    a = abs(rho)
    return "weak" if a < 0.3 else "moderate" if a < 0.5 else "fairly strong"


def load_primary_summary():
    path = os.path.join(BASE_DIR, "models", "primary_summary.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


# (lifestyle column, human label, symptom column, human label)
PAIRS = [
    ("stress_level", "stress", "pain_severity", "period pain"),
    ("stress_level", "stress", "fatigue", "fatigue"),
    ("sleep_hours", "sleep hours", "pain_severity", "period pain"),
    ("sleep_hours", "sleep hours", "fatigue", "fatigue"),
    ("sleep_hours", "sleep hours", "headache", "headaches"),
    ("meals_skipped", "skipped meals", "fatigue", "fatigue"),
    ("meals_skipped", "skipped meals", "headache", "headaches"),
    ("exercise_minutes", "exercise minutes", "pain_severity", "period pain"),
    ("exercise_minutes", "exercise minutes", "bloating", "bloating"),
]


def daily_associations(lifestyle_logs, symptom_logs):
    """Day-level: join lifestyle and symptom logs by date and correlate."""
    if not lifestyle_logs or not symptom_logs:
        return [], 0
    life = pd.DataFrame(lifestyle_logs).set_index("log_date")
    sym = pd.DataFrame(symptom_logs).set_index("log_date")
    joined = life.join(sym, how="inner", lsuffix="_l", rsuffix="_s")
    n_days = len(joined)
    results = []
    if n_days < MIN_PAIRED_DAYS:
        return results, n_days
    for lcol, llabel, scol, slabel in PAIRS:
        if lcol not in joined or scol not in joined:
            continue
        sub = joined[[lcol, scol]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(sub) < MIN_PAIRED_DAYS:
            continue
        rho = _spearman(sub[lcol], sub[scol])
        if rho is None or abs(rho) < 0.2:
            continue
        direction = "higher" if rho > 0 else "lower"
        results.append({
            "title": f"{llabel.capitalize()} and {slabel}",
            "text": (f"On days when your {llabel} was higher, your {slabel} tended to be "
                     f"{direction} ({_strength(rho)} association, {len(sub)} days compared)."),
            "rho": round(rho, 2), "n": len(sub),
            "tentative": len(sub) < 20,
        })
    results.sort(key=lambda r: -abs(r["rho"]))
    return results, n_days


def cycle_level_associations(starts, lifestyle_logs):
    """Cycle-level: average lifestyle inside each cycle vs that cycle's length."""
    if len(starts) < MIN_CYCLES + 1 or not lifestyle_logs:
        return [], 0
    life = pd.DataFrame(lifestyle_logs)
    life["log_date"] = pd.to_datetime(life["log_date"])
    rows = []
    for i in range(len(starts) - 1):
        a, b = pd.Timestamp(starts[i]), pd.Timestamp(starts[i + 1])
        length = (b - a).days
        if not 15 <= length <= 60:
            continue
        chunk = life[(life["log_date"] >= a) & (life["log_date"] < b)]
        if len(chunk) < 5:                        # need some logging inside the cycle
            continue
        rows.append({
            "length": length,
            "stress": pd.to_numeric(chunk["stress_level"], errors="coerce").mean(),
            "sleep": pd.to_numeric(chunk["sleep_hours"], errors="coerce").mean(),
            "exam_days": int(pd.to_numeric(chunk["exam_period"], errors="coerce").fillna(0).sum()),
            "skipped": pd.to_numeric(chunk["meals_skipped"], errors="coerce").mean(),
        })
    n = len(rows)
    results = []
    if n < MIN_CYCLES:
        return results, n
    df = pd.DataFrame(rows)
    for col, label in [("stress", "average stress"), ("sleep", "average sleep"),
                       ("exam_days", "number of exam days"), ("skipped", "skipped meals")]:
        sub = df[["length", col]].dropna()
        if len(sub) < MIN_CYCLES:
            continue
        rho = _spearman(sub["length"], sub[col])
        if rho is None or abs(rho) < 0.3:
            continue
        direction = "longer" if rho > 0 else "shorter"
        results.append({
            "title": f"{label.capitalize()} and cycle length",
            "text": (f"Cycles with higher {label} tended to be {direction} "
                     f"({_strength(rho)} association across {len(sub)} cycles)."),
            "rho": round(rho, 2), "n": len(sub), "tentative": True,
        })
    return results, n


def exam_vs_normal(starts, lifestyle_logs):
    """Compare average cycle length: cycles that included exam days vs cycles that did not."""
    if len(starts) < 4 or not lifestyle_logs:
        return None
    life = pd.DataFrame(lifestyle_logs)
    life["log_date"] = pd.to_datetime(life["log_date"])
    exam, normal = [], []
    for i in range(len(starts) - 1):
        a, b = pd.Timestamp(starts[i]), pd.Timestamp(starts[i + 1])
        length = (b - a).days
        if not 15 <= length <= 60:
            continue
        chunk = life[(life["log_date"] >= a) & (life["log_date"] < b)]
        if len(chunk) < 5:
            continue
        (exam if pd.to_numeric(chunk["exam_period"], errors="coerce").fillna(0).sum() > 0
         else normal).append(length)
    if len(exam) >= 2 and len(normal) >= 2:
        diff = np.mean(exam) - np.mean(normal)
        return {"exam_mean": round(float(np.mean(exam)), 1), "normal_mean": round(float(np.mean(normal)), 1),
                "diff": round(float(diff), 1), "n_exam": len(exam), "n_normal": len(normal)}
    return None


def build_insights(snapshot):
    """Everything the Student Insights page needs."""
    life, sym, starts = snapshot["lifestyle"], snapshot["symptoms"], snapshot["starts"]
    daily, n_days = daily_associations(life, sym)
    cyc, n_cyc = cycle_level_associations(starts, life)
    return {
        "daily": daily, "paired_days": n_days,
        "cycle_level": cyc, "cycles_with_data": n_cyc,
        "exam": exam_vs_normal(starts, life),
        "lifestyle_days": len(life), "symptom_days": len(sym),
        "min_paired_days": MIN_PAIRED_DAYS, "min_cycles": MIN_CYCLES,
        "survey": load_primary_summary(),
    }
