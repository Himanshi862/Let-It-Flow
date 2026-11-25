"""
Let It Flow - ML training script (Stage 5)
==========================================

WHAT THIS SCRIPT DOES
---------------------
Trains a model that predicts the NEXT cycle length (in days) from a person's
PREVIOUS cycle lengths.

DATA USED (and why)
-------------------
* Kaggle / FedCycle dataset (2data.csv)  -> TRAINING data.
    One row = one cycle of one participant (ClientID).  Many cycles per person,
    so rows of the same person are NOT independent.  We therefore split the data
    BY PARTICIPANT (GroupKFold / GroupShuffleSplit) - never by row.
* Primary college survey (xlsx)          -> NOT used for training (only ~63
    intervals from 33 people).  Used only for (a) a tiny sanity check and
    (b) describing the student population (models/primary_summary.json).

FEATURES (only things the app can also collect from a user)
------------------------------------------------------------
    lag1..lagK   previous K cycle lengths (lag1 = most recent)
    mean_recent  mean of the last <=6 previous cycles
    std_recent   standard deviation of the last <=6 previous cycles

Columns such as MeanCycleLength / EstimatedDayofOvulation / LengthofLutealPhase
are deliberately NOT used: they describe the same cycle being predicted (data
leakage).  Fertility / intercourse columns are outside the app's purpose.

HOW TO RUN
----------
    python prediction/train_model.py
Outputs go to the models/ folder.
"""

import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from prediction.features import build_feature_row, feature_names  # noqa: E402

KAGGLE_CSV = os.path.join(BASE_DIR, "datasets", "kaggle_dataset", "2data.csv")
PRIMARY_XLSX = os.path.join(BASE_DIR, "datasets", "primary_dataset",
                            "Primary_Data_Revised_Cycle_Cleaning.xlsx")
MODELS_DIR = os.path.join(BASE_DIR, "models")
RANDOM_STATE = 42
LAG_OPTIONS = (2, 3)          # we train one model that needs 2 past cycles, one that needs 3


# ---------------------------------------------------------------------------
# 1. Load + clean the Kaggle data (nothing is invented; only removed if invalid)
# ---------------------------------------------------------------------------
def load_kaggle():
    df = pd.read_csv(KAGGLE_CSV)
    report = {"rows_raw": int(len(df)), "participants_raw": int(df["ClientID"].nunique())}

    df["LengthofCycle"] = pd.to_numeric(df["LengthofCycle"], errors="coerce")
    df["CycleNumber"] = pd.to_numeric(df["CycleNumber"], errors="coerce")
    df = df.dropna(subset=["ClientID", "CycleNumber", "LengthofCycle"])

    # (a) exact duplicate rows -> keep one copy
    before = len(df)
    df = df.drop_duplicates()
    report["exact_duplicate_rows_removed"] = int(before - len(df))

    # (b) same ClientID + CycleNumber but DIFFERENT values = conflicting records.
    #     We cannot know which is right, so those cycles are removed (not "fixed").
    dup_mask = df.duplicated(["ClientID", "CycleNumber"], keep=False)
    report["conflicting_cycle_rows_removed"] = int(dup_mask.sum())
    df = df[~dup_mask]

    df = df.sort_values(["ClientID", "CycleNumber"]).reset_index(drop=True)
    report["rows_clean"] = int(len(df))
    report["participants_clean"] = int(df["ClientID"].nunique())
    return df[["ClientID", "CycleNumber", "LengthofCycle"]], report


# ---------------------------------------------------------------------------
# 2. Turn each participant's sequence of cycles into (features -> next cycle) rows
# ---------------------------------------------------------------------------
def make_supervised(df, n_lags):
    rows, targets, groups = [], [], []
    for client, g in df.groupby("ClientID"):
        lengths = g["LengthofCycle"].tolist()
        # need n_lags previous cycles before we can predict cycle i
        for i in range(n_lags, len(lengths)):
            history = lengths[:i]                       # only the PAST (no leakage)
            rows.append(build_feature_row(history, n_lags))
            targets.append(lengths[i])
            groups.append(client)
    X = pd.DataFrame(rows, columns=feature_names(n_lags))
    return X, np.array(targets, dtype=float), np.array(groups)


# ---------------------------------------------------------------------------
# 3. Baselines (a model must beat these to be worth using)
# ---------------------------------------------------------------------------
def baseline_predictions(X, train_median):
    return {
        "baseline_last_cycle": X["lag1"].values,
        "baseline_recent_mean": X["mean_recent"].values,
        "baseline_global_median": np.full(len(X), train_median),
    }


def mae(y, p):
    return float(mean_absolute_error(y, p))


def rmse(y, p):
    return float(np.sqrt(mean_squared_error(y, p)))


def candidate_models():
    return {
        "ridge": Pipeline([("scale", StandardScaler()), ("m", Ridge(alpha=10.0))]),
        "random_forest": RandomForestRegressor(
            n_estimators=300, min_samples_leaf=10, random_state=RANDOM_STATE, n_jobs=-1),
        "gradient_boosting": GradientBoostingRegressor(
            n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.8,
            random_state=RANDOM_STATE),
    }


# ---------------------------------------------------------------------------
# 4. Train + evaluate for one value of n_lags
# ---------------------------------------------------------------------------
def train_for_lags(df, n_lags):
    X, y, groups = make_supervised(df, n_lags)
    info = {"n_lags": n_lags, "n_rows": int(len(X)), "n_participants": int(len(set(groups)))}

    # Held-out TEST participants (20%) - never touched while choosing a model
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RANDOM_STATE)
    train_idx, test_idx = next(splitter.split(X, y, groups))
    Xtr, ytr, gtr = X.iloc[train_idx], y[train_idx], groups[train_idx]
    Xte, yte = X.iloc[test_idx], y[test_idx]
    info["train_participants"] = int(len(set(gtr)))
    info["test_participants"] = int(len(set(groups[test_idx])))
    info["test_rows"] = int(len(test_idx))

    train_median = float(np.median(ytr))

    # 5-fold CV grouped by participant, on the TRAIN part only -> choose the model
    cv = GroupKFold(n_splits=5)
    cv_scores, oof = {}, {}
    for name, model in candidate_models().items():
        preds = np.zeros(len(ytr))
        for a, b in cv.split(Xtr, ytr, gtr):
            model.fit(Xtr.iloc[a], ytr[a])
            preds[b] = model.predict(Xtr.iloc[b])
        cv_scores[name] = {"cv_mae": mae(ytr, preds), "cv_rmse": rmse(ytr, preds)}
        oof[name] = preds
    for bname, bp in baseline_predictions(Xtr, train_median).items():
        cv_scores[bname] = {"cv_mae": mae(ytr, bp), "cv_rmse": rmse(ytr, bp)}

    ml_names = list(candidate_models().keys())
    best_name = min(ml_names, key=lambda n: cv_scores[n]["cv_mae"])
    best_baseline = min([n for n in cv_scores if n.startswith("baseline")],
                        key=lambda n: cv_scores[n]["cv_mae"])
    info["cv_scores"] = cv_scores
    info["best_ml_model"] = best_name
    info["best_baseline"] = best_baseline

    # Refit the chosen model on all training participants, test on held-out people
    final_model = candidate_models()[best_name]
    final_model.fit(Xtr, ytr)
    test_scores = {best_name: {"mae": mae(yte, final_model.predict(Xte)),
                               "rmse": rmse(yte, final_model.predict(Xte))}}
    for bname, bp in baseline_predictions(Xte, train_median).items():
        test_scores[bname] = {"mae": mae(yte, bp), "rmse": rmse(yte, bp)}
    info["test_scores"] = test_scores

    # Is the ML model actually better than the best simple baseline? (be honest)
    ml_mae = test_scores[best_name]["mae"]
    base_mae = test_scores[best_baseline]["mae"]
    info["ml_beats_best_baseline_on_test"] = bool(ml_mae < base_mae)
    info["ml_improvement_over_best_baseline_pct"] = float(100 * (base_mae - ml_mae) / base_mae)

    # Uncertainty band: the 80th percentile of absolute out-of-fold errors.
    # "Most predictions land within +/- q80 days" (an empirical estimate, not a guarantee)
    abs_err = np.abs(ytr - oof[best_name])
    q80 = float(np.quantile(abs_err, 0.80))
    test_abs = np.abs(yte - final_model.predict(Xte))
    info["interval_halfwidth_days_q80"] = q80
    info["interval_coverage_on_test"] = float(np.mean(test_abs <= q80))

    # Final model for the app: refit on ALL participants (train + test)
    app_model = candidate_models()[best_name]
    app_model.fit(X, y)

    bundle = {
        "model": app_model,
        "model_name": best_name,
        "n_lags": n_lags,
        "feature_names": feature_names(n_lags),
        "interval_halfwidth_days": q80,
        "ml_beats_baseline": info["ml_beats_best_baseline_on_test"],
        "train_median": float(np.median(y)),
    }
    joblib.dump(bundle, os.path.join(MODELS_DIR, f"cycle_model_lags{n_lags}.joblib"))
    return info, bundle


# ---------------------------------------------------------------------------
# 5. Tiny sanity check on the primary college survey (NOT training)
# ---------------------------------------------------------------------------
def primary_sanity_check(bundle2):
    d = pd.read_excel(PRIMARY_XLSX, sheet_name="Primary_Model_Cohort")
    cols = ["date_based_cycle_interval_3_days", "date_based_cycle_interval_2_days",
            "date_based_cycle_interval_1_days"]            # oldest -> newest
    sub = d.dropna(subset=cols).copy()
    ok = sub[cols].apply(lambda r: all(15 <= v <= 60 for v in r), axis=1)
    sub = sub[ok]
    res = {"participants_used": int(len(sub)),
           "note": "Very small descriptive check (not proof of accuracy)."}
    if len(sub) == 0:
        return res
    preds, base_last, base_mean, actual = [], [], [], []
    for _, r in sub.iterrows():
        h = [r[cols[0]], r[cols[1]]]                      # two older intervals
        row = pd.DataFrame([build_feature_row(h, 2)], columns=feature_names(2))
        preds.append(float(bundle2["model"].predict(row)[0]))
        base_last.append(h[-1])
        base_mean.append(float(np.mean(h)))
        actual.append(float(r[cols[2]]))
    res.update({
        "model_mae": mae(actual, preds),
        "baseline_last_cycle_mae": mae(actual, base_last),
        "baseline_mean_mae": mae(actual, base_mean),
    })
    return res


# ---------------------------------------------------------------------------
# 6. Describe the primary (college) population - used by the Insights page
# ---------------------------------------------------------------------------
def summarise_primary():
    d = pd.read_excel(PRIMARY_XLSX, sheet_name="Primary_Model_Cohort")

    def short(col, split_on=" – "):
        return d[col].astype(str).str.split(split_on).str[0].str.strip()

    def counts(series):
        vc = series.value_counts()
        return {str(k): int(v) for k, v in vc.items()}

    out = {
        "n_participants": int(len(d)),
        "age_median": float(d["age_years"].median()),
        "regularity": counts(short("cycle_regularity")),
        "symptom_severity": counts(short("symptom_severity")),
        "diet": counts(d["dietary_preference"]),
        "preferred_exercise": counts(d["preferred_exercise"]),
        "activity_level": counts(short("daily_activity_level")),
        "bleeding_duration": counts(d["bleeding_duration_raw"]),
    }
    # Common symptom mentions (multi-select text column)
    sym = {}
    for cell in d["period_discomforts"].dropna():
        for item in str(cell).split(","):
            item = item.strip()
            if item:
                sym[item] = sym.get(item, 0) + 1
    out["period_discomforts"] = dict(sorted(sym.items(), key=lambda kv: -kv[1])[:8])

    # Descriptive cross-tab: activity level vs symptom severity (tiny n, associations only)
    ct = pd.crosstab(short("daily_activity_level"), short("symptom_severity"))
    out["activity_vs_severity"] = {r: {c: int(ct.loc[r, c]) for c in ct.columns} for r in ct.index}
    return out


# ---------------------------------------------------------------------------
def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    df, clean_report = load_kaggle()
    print("Kaggle cleaning:", clean_report)

    results = {"data_cleaning": clean_report, "models": {}}
    bundles = {}
    for k in LAG_OPTIONS:
        info, bundle = train_for_lags(df, k)
        results["models"][f"lags{k}"] = info
        bundles[k] = bundle
        print(f"\n== Model needing {k} previous cycles ==")
        print(json.dumps({x: info[x] for x in ("n_rows", "n_participants", "best_ml_model",
                                               "best_baseline", "test_scores",
                                               "ml_beats_best_baseline_on_test",
                                               "interval_halfwidth_days_q80",
                                               "interval_coverage_on_test")}, indent=2))

    results["primary_sanity_check"] = primary_sanity_check(bundles[2])
    print("\nPrimary sanity check:", results["primary_sanity_check"])

    results["training_population_note"] = (
        "Trained on the Kaggle/FedCycle adult fertility-charting dataset "
        "(median age about 31). NOT trained on Indian college students."
    )
    with open(os.path.join(MODELS_DIR, "metrics.json"), "w") as f:
        json.dump(results, f, indent=2)
    with open(os.path.join(MODELS_DIR, "primary_summary.json"), "w") as f:
        json.dump(summarise_primary(), f, indent=2)
    print("\nSaved models/*.joblib, metrics.json and primary_summary.json")


if __name__ == "__main__":
    main()
