"""
Let It Flow - Irregular Cycle Intelligence (Stage 6)

Looks at a person's logged period start dates and explains, in plain language:
  * how consistent the cycles are
  * whether cycles are often shorter or longer than the usual range
  * repeated delays, long gaps / missed periods
  * changes over time
  * symptoms that deserve a doctor's attention (severe pain, heavy bleeding)

This is RULE-BASED (not machine learning) on purpose: rules can be explained
to a user and a viva examiner line by line.

REFERENCE RANGES (simplified, for education only)
  Adults (19+):  usual cycle 24-38 days   (FIGO 2018 menstrual-frequency categories)
  Age 18 or less: usual cycle 21-45 days  (ACOG: adolescents' cycles often vary)
  Variation between shortest and longest recent cycle: up to ~7-9 days is
  commonly described as normal variation.
  No period for 90+ days (3 months) is something to discuss with a clinician.

IMPORTANT: Nothing here is a diagnosis.  We never name PCOS, thyroid
disorders, endometriosis, etc.  A "worth discussing" message means exactly
that - not that something is wrong.
"""

from datetime import date

import numpy as np

from prediction.cycle_prediction import cycle_intervals

ENTRY_CHECK_BELOW = 15       # gaps this short are probably typing mistakes
MISSED_GAP = 60              # a gap this long is likely a missed period
LONG_GAP = 90                # 3+ months without a period


def reference_range(age):
    """Usual cycle-length range for the person's age."""
    if age is not None and age <= 18:
        return 21, 45, "ACOG guidance for adolescents (21-45 days)"
    return 24, 38, "FIGO 2018 normal frequency for adults (24-38 days)"


def _finding(severity, title, text):
    return {"severity": severity, "title": title, "text": text}


def analyze_cycles(period_starts, age=None, today=None, period_length=None,
                   self_regularity=None, self_missed=None, recent_symptoms=None):
    """
    period_starts   : list of date objects
    age             : int or None
    period_length   : typical bleeding days from the user's profile (or None)
    self_regularity : 'regular' / 'slightly_irregular' / 'highly_irregular' / None
    self_missed     : True / False / None (user said they have missed periods)
    recent_symptoms : list of dicts with pain_severity, bleeding_intensity (recent logs)
    """
    today = today or date.today()
    starts = sorted(set(period_starts))
    low, high, ref_source = reference_range(age)
    findings = []
    all_iv = cycle_intervals(starts)

    out = {
        "status": "not_enough_data", "status_label": "Not enough data yet",
        "headline": "", "stats": {}, "findings": findings,
        "reference": {"low": low, "high": high, "source": ref_source},
        "intervals": [], "n_intervals": len(all_iv),
    }

    # interval table for charts / tables
    for i, d in enumerate(all_iv):
        flag = "ok"
        if d < ENTRY_CHECK_BELOW:
            flag = "check_entry"
        elif d > MISSED_GAP:
            flag = "long_gap"
        elif d < low:
            flag = "short"
        elif d > high:
            flag = "long"
        out["intervals"].append({"start": starts[i], "end": starts[i + 1], "days": d, "flag": flag})

    usable = [d for d in all_iv if ENTRY_CHECK_BELOW <= d <= MISSED_GAP]

    # ---------- 0. data-entry warnings ----------
    short_entries = [d for d in all_iv if d < ENTRY_CHECK_BELOW]
    if short_entries:
        findings.append(_finding(
            "notice", "Some dates may need checking",
            f"{len(short_entries)} gap(s) between period dates are under {ENTRY_CHECK_BELOW} days "
            f"(for example {short_entries[0]} days). Cycles are rarely this short, so one of the dates "
            "may have been entered by mistake (for example a period end date). "
            "These gaps are ignored in the analysis below - please check them on the Cycle Tracker."))

    # ---------- 1. not enough data ----------
    if len(usable) < 3:
        out["headline"] = ("Add a few more past period start dates to see a pattern. "
                           "At least 3 recorded cycles are needed for a meaningful analysis.")
        findings.append(_finding(
            "info", "Why we need more data",
            "One or two cycles can differ a lot just by chance. With 3 or more recorded cycles, "
            "Let It Flow can show how consistent your cycle is."))
        _add_self_report_and_symptom_findings(findings, period_length, self_regularity, self_missed,
                                              recent_symptoms)
        _add_current_gap(findings, starts, today, usable)
        _finalize_status(out, keep_label_if_no_data=True)
        return out

    # ---------- 2. basic statistics ----------
    recent = usable[-6:]
    mean_all = float(np.mean(usable))
    std_recent = float(np.std(recent))
    rng = max(recent) - min(recent)
    out["stats"] = {
        "n_cycles": len(usable), "mean": round(mean_all, 1),
        "median": float(np.median(usable)), "std": round(std_recent, 1),
        "shortest": min(usable), "longest": max(usable), "range_recent": rng,
        "inside_range_pct": round(100 * sum(low <= d <= high for d in usable) / len(usable)),
    }

    # ---------- 3. consistency ----------
    if rng <= 7:
        findings.append(_finding(
            "good", "Your cycle length is fairly consistent",
            f"Your last {len(recent)} cycles ranged from {min(recent)} to {max(recent)} days, "
            f"a difference of {rng} days. Variation of up to about 7 days is commonly seen."))
    elif rng <= 9:
        findings.append(_finding(
            "info", "Some natural variation",
            f"Your recent cycles ranged from {min(recent)} to {max(recent)} days "
            f"({rng} days apart). This is at the upper end of what is often described as normal variation."))
    elif rng < 20:
        findings.append(_finding(
            "notice", "Your cycle length varies quite a bit",
            f"Your recent cycles ranged from {min(recent)} to {max(recent)} days ({rng} days apart). "
            "Stress, illness, travel, sleep changes and exam periods can all be associated with "
            "variation. If this keeps happening, it is worth mentioning to a doctor."))
    else:
        findings.append(_finding(
            "talk", "Your cycle length varies a lot",
            f"Your recent cycles ranged from {min(recent)} to {max(recent)} days ({rng} days apart). "
            "A gap this wide is worth discussing with a doctor, who can look at the full picture."))

    # ---------- 4. often shorter / longer than the usual range ----------
    short_ct = sum(1 for d in recent if d < low)
    long_ct = sum(1 for d in recent if d > high)
    n = len(recent)
    if short_ct >= 2 and short_ct / n >= 0.4:
        findings.append(_finding(
            "talk", "Cycles are often shorter than usual",
            f"{short_ct} of your last {n} cycles were shorter than {low} days. Frequent short cycles "
            "are worth discussing with a healthcare professional."))
    elif short_ct == 1:
        findings.append(_finding(
            "info", "One shorter cycle",
            f"One recent cycle was shorter than {low} days. A single short cycle is common and "
            "usually not a concern by itself."))
    if long_ct >= 2 and long_ct / n >= 0.4:
        findings.append(_finding(
            "talk", "Cycles are often longer than usual",
            f"{long_ct} of your last {n} cycles were longer than {high} days. Frequently long cycles "
            "are worth discussing with a healthcare professional."))
    elif long_ct == 1:
        findings.append(_finding(
            "info", "One longer cycle",
            f"One recent cycle was longer than {high} days. Stress, illness or travel are common "
            "reasons for an occasional longer cycle."))

    # ---------- 5. repeated delays (each cycle longer than the one before) ----------
    if len(usable) >= 4:
        last3 = usable[-4:]
        if last3[0] < last3[1] < last3[2] < last3[3] and last3[3] - last3[0] >= 5:
            findings.append(_finding(
                "notice", "Cycles are getting longer",
                f"Your last 4 cycles got longer each time ({' -> '.join(map(str, last3))} days). "
                "Keep logging - if the trend continues, mention it to a doctor."))

    # ---------- 6. change over time ----------
    if len(usable) >= 6:
        half = len(usable) // 2
        first, second = np.mean(usable[:half]), np.mean(usable[half:])
        diff = second - first
        if abs(diff) >= 5:
            direction = "longer" if diff > 0 else "shorter"
            findings.append(_finding(
                "notice", f"Your cycles have become {direction} over time",
                f"Your earlier cycles averaged {first:.0f} days and your later ones {second:.0f} days "
                f"({abs(diff):.0f} days {direction}). Changes in routine, stress and sleep are "
                "sometimes linked with shifts like this."))

    # ---------- 7. long gaps / missed periods ----------
    gaps = [d for d in all_iv if d > MISSED_GAP]
    if gaps:
        sev = "talk" if max(gaps) >= LONG_GAP else "notice"
        findings.append(_finding(
            sev, "A long gap between periods",
            f"There is a gap of {max(gaps)} days between two logged periods. This can mean a "
            "period was missed or not recorded. If it was not just a missing entry, gaps of 60+ days "
            "are worth discussing with a doctor" +
            (" - and 90+ days (3 months) should be checked." if max(gaps) >= LONG_GAP else ".")))

    _add_current_gap(findings, starts, today, usable)
    _add_self_report_and_symptom_findings(findings, period_length, self_regularity, self_missed,
                                          recent_symptoms)
    _finalize_status(out)
    return out


# ---------------------------------------------------------------------------
def _add_current_gap(findings, starts, today, usable):
    """How long since the latest period started?  (compared with the person's average)"""
    if not starts:
        return
    since = (today - starts[-1]).days
    if since >= LONG_GAP:
        findings.append(_finding(
            "talk", "It has been a long time since your last period",
            f"Your last logged period started {since} days ago. If you have not logged one since, "
            "please speak to a doctor - 3 months without a period should be checked."))
    elif since > MISSED_GAP:
        findings.append(_finding(
            "notice", "More than 2 months since your last logged period",
            f"Your last logged period started {since} days ago. If you have had a period since, "
            "add it on the Cycle Tracker. If not, consider speaking to a doctor."))
    elif usable and since > np.mean(usable[-6:]) + 7:
        late = int(since - np.mean(usable[-6:]))
        findings.append(_finding(
            "info", "Your period may be running late",
            f"It is day {since + 1} of this cycle, about {late} days beyond your recent average. "
            "Stress, illness, travel and routine changes are common reasons for a late period. "
            "If you think you could be pregnant, a pregnancy test is the quickest way to find out."))


def _add_self_report_and_symptom_findings(findings, period_length, self_regularity, self_missed,
                                          recent_symptoms):
    if period_length and period_length > 7:
        findings.append(_finding(
            "talk", "Long periods",
            f"You told us your period lasts about {period_length} days. Bleeding that lasts "
            "more than 7 days is worth discussing with a doctor."))
    if self_missed:
        findings.append(_finding(
            "notice", "You mentioned missed periods",
            "You told us you have missed periods or had long gaps. If this happens often, "
            "a doctor can help find out why."))
    if self_regularity == "highly_irregular":
        findings.append(_finding(
            "notice", "You describe your cycle as highly irregular",
            "Logging every period start date here will help you and your doctor see the pattern."))

    if recent_symptoms:
        severe = [s for s in recent_symptoms if (s.get("pain_severity") or 0) >= 8]
        heavy = [s for s in recent_symptoms if (s.get("bleeding_intensity") or 0) >= 5]
        if len(severe) >= 2:
            findings.append(_finding(
                "talk", "Severe period pain logged more than once",
                "You logged pain of 8 or higher (out of 10) on multiple days. Pain that is severe "
                "or stops you from studying or going about your day is worth discussing with a doctor."))
        if heavy:
            findings.append(_finding(
                "talk", "Very heavy bleeding logged",
                "You logged very heavy bleeding. Soaking through a pad or tampon every hour for "
                "several hours, or passing large clots, needs medical attention - do not wait."))


def _finalize_status(out, keep_label_if_no_data=False):
    sev = {f["severity"] for f in out["findings"]}
    if keep_label_if_no_data and out["status"] == "not_enough_data" and "talk" not in sev:
        return
    if "talk" in sev:
        out["status"], out["status_label"] = "worth_discussing", "Worth discussing with a doctor"
        out["headline"] = ("Some things in your history are worth discussing with a healthcare "
                           "professional. This is not a diagnosis.")
    elif "notice" in sev:
        out["status"], out["status_label"] = "some_variation", "Some variation"
        out["headline"] = "Your pattern shows some variation. Keep logging to see if it continues."
    else:
        out["status"], out["status_label"] = "consistent", "Consistent"
        out["headline"] = "Your logged cycles look consistent."
    if keep_label_if_no_data and out["status"] != "not_enough_data":
        pass
