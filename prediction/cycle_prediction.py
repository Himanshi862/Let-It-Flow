"""
Let It Flow - cycle prediction module (Stage 5)

Public functions
----------------
cycle_intervals(period_starts)           -> list of day gaps between period starts
predict_next_period(period_starts, ...)  -> dict with estimate, range, method, confidence
cycle_day_and_phase(last_start, ...)     -> (cycle_day, phase_key)

HONEST DESIGN NOTES
-------------------
* The trained model needs the last 3 usable cycle lengths.
* In our evaluation the model was only marginally better than "average of your
  recent cycles".  With fewer than 3 cycles (or when ML did not beat that
  baseline) the app uses the plain average and says so.
* Everything returned is an ESTIMATE, never a guaranteed date.
"""

import os
from datetime import date, timedelta

import joblib
import numpy as np
import pandas as pd

from prediction.features import MAX_VALID, MIN_VALID, build_feature_row, feature_names

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")

_model_cache = {}


def _load_bundle(n_lags):
    """Load a saved model once and keep it in memory."""
    if n_lags not in _model_cache:
        path = os.path.join(MODELS_DIR, f"cycle_model_lags{n_lags}.joblib")
        bundle = None
        if os.path.exists(path):
            try:
                bundle = joblib.load(path)
            except Exception as exc:          # e.g. different scikit-learn version on this PC
                print(f"[Let It Flow] Could not load {path}: {exc}\n"
                      "  -> run  python prediction/train_model.py  to rebuild the model. "
                      "Until then the app uses the plain average of your cycles.")
        _model_cache[n_lags] = bundle
    return _model_cache[n_lags]


def cycle_intervals(period_starts):
    """Days between consecutive period start dates (oldest -> newest)."""
    s = sorted(set(period_starts))
    return [(s[i + 1] - s[i]).days for i in range(len(s) - 1)]


def usable_intervals(intervals):
    """
    Intervals we trust as real cycle lengths for the model.
    < 15 days is probably a typing mistake; > 60 days is probably a missed
    period or a forgotten entry.  They are NOT deleted from the user's data,
    just left out of the prediction (and flagged on the Cycle Intelligence page).
    """
    return [i for i in intervals if MIN_VALID <= i <= MAX_VALID]


def predict_next_period(period_starts, typical_length=None, today=None):
    """
    period_starts  : list of datetime.date (any order)
    typical_length : optional number the user typed during onboarding
    Returns a dict (see keys below) - always safe to show to the user.
    """
    today = today or date.today()
    starts = sorted(set(period_starts))
    result = {
        "available": False, "method": None, "method_label": "", "confidence": "none",
        "predicted_length": None, "next_start": None, "range_start": None, "range_end": None,
        "halfwidth": None, "n_usable": 0, "last_start": starts[-1] if starts else None,
        "days_until": None, "days_late": None, "notes": [],
    }
    if not starts:
        result["notes"].append("Add your most recent period start date to get an estimate.")
        return result

    all_iv = cycle_intervals(starts)
    iv = usable_intervals(all_iv)
    result["n_usable"] = len(iv)
    if len(all_iv) > len(iv):
        result["notes"].append(
            f"{len(all_iv) - len(iv)} interval(s) were left out of the estimate because they look "
            f"unusually short (<{MIN_VALID} days) or long (>{MAX_VALID} days). "
            "Please double-check those dates.")

    # ---- choose method --------------------------------------------------
    pred, halfwidth = None, None
    bundle3 = _load_bundle(3)
    if len(iv) >= 3 and bundle3 is not None:
        if bundle3["ml_beats_baseline"]:
            row = pd.DataFrame([build_feature_row(iv, 3)], columns=feature_names(3))
            pred = float(bundle3["model"].predict(row)[0])
            result["method"] = "ml_model"
            result["method_label"] = ("Machine-learning model (ridge regression trained on the "
                                      "Kaggle/FedCycle dataset) using your last 3+ cycles")
        else:
            pred = float(np.mean(iv[-6:]))
            result["method"] = "recent_average"
        halfwidth = max(bundle3["interval_halfwidth_days"], float(np.std(iv[-6:])))
        result["confidence"] = "moderate"
    elif len(iv) == 2:
        pred = float(np.mean(iv))
        result["method"] = "recent_average"
        halfwidth = max(4.0, float(np.std(iv)) + 2)
        result["confidence"] = "low"
        result["notes"].append("Only 2 usable cycles are logged, so the model is not used. "
                               "Add more past period dates for a better estimate.")
    elif len(iv) == 1:
        pred = float(iv[0]) if not typical_length else (iv[0] + typical_length) / 2
        result["method"] = "recent_average"
        halfwidth = 5.0
        result["confidence"] = "low"
        result["notes"].append("Only 1 usable cycle is logged - this is a rough guess.")
    elif typical_length and MIN_VALID <= typical_length <= MAX_VALID:
        pred = float(typical_length)
        result["method"] = "self_reported"
        result["method_label"] = "Typical cycle length you told us"
        halfwidth = 7.0
        result["confidence"] = "low"
        result["notes"].append("No full cycle is logged yet, so this uses your own typical cycle length.")
    else:
        result["notes"].append("Not enough history yet. Add at least 2 earlier period start dates "
                               "(3+ is better) to see a personal estimate.")
        return result

    if result["method"] == "recent_average":
        result["method_label"] = "Average of your recent cycle lengths"

    pred_days = int(round(pred))
    halfwidth_days = int(np.ceil(halfwidth))
    last = starts[-1]
    nxt = last + timedelta(days=pred_days)
    result.update({
        "available": True,
        "predicted_length": round(pred, 1),
        "halfwidth": halfwidth_days,
        "next_start": nxt,
        "range_start": nxt - timedelta(days=halfwidth_days),
        "range_end": nxt + timedelta(days=halfwidth_days),
    })
    delta = (nxt - today).days
    if delta >= 0:
        result["days_until"] = delta
    if today > result["range_end"]:
        result["days_late"] = (today - nxt).days
    result["notes"].append("This is an estimate, not a guaranteed date, and not for contraception "
                           "or fertility planning.")
    return result


# ---------------------------------------------------------------------------
# Cycle day + phase (educational approximation)
# ---------------------------------------------------------------------------
PHASES = {
    "menstrual": "Menstrual",
    "follicular": "Follicular",
    "ovulatory": "Mid-cycle",
    "luteal": "Luteal",
}


def cycle_day_and_phase(last_start, expected_length=29, period_length=5, today=None):
    """
    Rough phase of the cycle based on day number.  Real hormone levels vary
    from person to person, so this is for education only.
    """
    today = today or date.today()
    if last_start is None:
        return None, None
    day = (today - last_start).days + 1
    period_length = period_length or 5
    expected_length = expected_length or 29
    mid = max(period_length + 2, expected_length - 14)        # approx. mid-cycle day
    if day <= period_length:
        phase = "menstrual"
    elif day < mid - 1:
        phase = "follicular"
    elif day <= mid + 1:
        phase = "ovulatory"
    else:
        phase = "luteal"
    return day, phase
