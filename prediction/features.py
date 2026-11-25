"""
Shared feature builder for Let It Flow.

The SAME function is used when training the model and when predicting for a
real user.  That guarantees the app feeds the model exactly the kind of
numbers it learned from (a very common source of silent bugs otherwise).
"""

import numpy as np

RECENT_WINDOW = 6          # how many of the latest cycles feed mean/std
MIN_VALID, MAX_VALID = 15, 60   # inputs outside this range are clipped (not deleted)


def feature_names(n_lags):
    """Column names, in order: lag1 (most recent) ... lagK, mean_recent, std_recent."""
    return [f"lag{i}" for i in range(1, n_lags + 1)] + ["mean_recent", "std_recent"]


def build_feature_row(history, n_lags):
    """
    history : list of previous cycle lengths in days, OLDEST first, NEWEST last.
    n_lags  : how many of the latest cycles to use as separate features.
    Returns a list of numbers matching feature_names(n_lags).
    """
    h = np.clip(np.asarray(history, dtype=float), MIN_VALID, MAX_VALID)
    latest_first = h[::-1]                       # lag1 = most recent
    lags = list(latest_first[:n_lags])
    recent = h[-RECENT_WINDOW:]
    return lags + [float(np.mean(recent)), float(np.std(recent))]
