"""
Let It Flow - Doctor-ready PDF report (Stage 9) using ReportLab.

generate_pdf(snapshot) -> bytes of a PDF.
Everything automated is clearly labelled as an ESTIMATE / OBSERVATION, not a diagnosis.
"""
from datetime import date
from io import BytesIO

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

PLUM = colors.HexColor("#3B2A55")
LAVENDER = colors.HexColor("#8B78B8")
SOFT = colors.HexColor("#F4F1FA")
ROSE = colors.HexColor("#C9737A")
AMBER = colors.HexColor("#B9791F")
SAGE = colors.HexColor("#4E7E6E")
GREY = colors.HexColor("#6E6780")

SEV_STYLE = {"talk": ("Worth discussing", ROSE), "notice": ("Notice", AMBER),
             "good": ("Reassuring", SAGE), "info": ("Note", GREY)}


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontName="Helvetica-Bold", fontSize=22,
                                textColor=PLUM, alignment=0, spaceAfter=2),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=10, textColor=GREY, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13,
                             textColor=PLUM, spaceBefore=12, spaceAfter=5),
        "body": ParagraphStyle("b", parent=base["Normal"], fontSize=9.5, leading=13.5),
        "small": ParagraphStyle("sm", parent=base["Normal"], fontSize=8, leading=11, textColor=GREY),
        "cell": ParagraphStyle("c", parent=base["Normal"], fontSize=8.5, leading=11),
    }


def _table(data, col_widths, header=True):
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDD6EA")),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), LAVENDER), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                  ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT])]
    t.setStyle(TableStyle(style))
    return t


def _interval_chart(intervals, low, high):
    """Bar chart of the last 12 cycle lengths."""
    vals = [i["days"] for i in intervals][-12:]
    if not vals:
        return None
    d = Drawing(170 * mm, 55 * mm)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 30, 20, 440, 110
    chart.data = [vals]
    chart.bars[0].fillColor = LAVENDER
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(max(vals) + 5, high + 5)
    chart.valueAxis.valueStep = 10
    chart.categoryAxis.categoryNames = [i["end"].strftime("%d %b") for i in intervals][-12:]
    chart.categoryAxis.labels.fontSize = 6.5
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.dy = -6
    chart.valueAxis.labels.fontSize = 7
    chart.barLabels.nudge = 6
    chart.barLabelFormat = "%d"
    chart.barLabels.fontSize = 7
    d.add(chart)
    d.add(String(30, 140, f"Cycle length in days (usual range for age: {low}-{high})", fontSize=8, fillColor=GREY))
    return d


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(18 * mm, 10 * mm, "Let It Flow - automated summary of self-recorded data. Estimates and observations, not a diagnosis.")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf(snap):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm,
                            title="Let It Flow - Cycle Summary", author="Let It Flow")
    st = _styles()
    story = []
    user, prof, pred, ana = snap["user"], snap["profile"], snap["prediction"], snap["analysis"]
    W = A4[0] - 36 * mm

    # ---- header
    story.append(Paragraph("Let It Flow", st["title"]))
    story.append(Paragraph(f"Menstrual health summary - generated {date.today().strftime('%d %B %Y')}", st["sub"]))
    disc = Table([[Paragraph(
        "<b>Please read:</b> This report was created from information the patient entered herself. "
        "Predictions and pattern observations are produced automatically and are <b>estimates, not diagnoses</b>. "
        "It is meant to help a conversation with a healthcare professional.", st["body"])]], colWidths=[W])
    disc.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("BOX", (0, 0), (-1, -1), 0.5, LAVENDER),
                              ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [disc, Spacer(1, 6)]

    # ---- 1. profile
    story.append(Paragraph("1. Profile (self-reported)", st["h2"]))
    reg = {"regular": "Regular", "slightly_irregular": "Slightly irregular",
           "highly_irregular": "Highly irregular"}.get(prof.get("self_regularity"), "Not provided")
    missed = {1: "Yes", 0: "No"}.get(prof.get("has_missed_periods"), "Not provided")
    rows = [["Name", user["name"], "Age", str(user["age"]) if user.get("age") else "Not provided"],
            ["Typical cycle length (self)", f"{prof['typical_cycle_length']} days" if prof.get("typical_cycle_length") else "Not provided",
             "Period duration (self)", f"{prof['period_duration']} days" if prof.get("period_duration") else "Not provided"],
            ["Self-described regularity", reg, "Missed periods / long gaps", missed]]
    t = _table(rows, [42 * mm, 42 * mm, 42 * mm, W - 126 * mm], header=False)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), SOFT), ("BACKGROUND", (2, 0), (2, -1), SOFT),
                           ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold")]))
    story.append(t)

    # ---- 2. recorded dates
    story.append(Paragraph("2. Recorded period start dates", st["h2"]))
    cycles = sorted(snap["cycles"], key=lambda c: c["period_start"])
    if not cycles:
        story.append(Paragraph("No period dates have been recorded.", st["body"]))
    else:
        rows = [["Period start", "Period end", "Bleeding days", "Days since previous start"]]
        prev = None
        for c in cycles[-18:]:
            bd = (c["period_end"] - c["period_start"]).days + 1 if c.get("period_end") else None
            gap = (c["period_start"] - prev).days if prev else None
            rows.append([c["period_start"].strftime("%d %b %Y"),
                         c["period_end"].strftime("%d %b %Y") if c.get("period_end") else "-",
                         str(bd) if bd else "-", str(gap) if gap else "-"])
            prev = c["period_start"]
        story.append(_table(rows, [W * 0.25] * 4))
        if len(cycles) > 18:
            story.append(Paragraph(f"Showing the latest 18 of {len(cycles)} recorded dates.", st["small"]))

    # ---- 3. interval history + stats
    story.append(Paragraph("3. Cycle length history", st["h2"]))
    s = ana["stats"]
    if s:
        story.append(Paragraph(
            f"Based on {s['n_cycles']} usable cycle(s): average <b>{s['mean']}</b> days, median {s['median']:.0f}, "
            f"shortest {s['shortest']}, longest {s['longest']}, variation (last 6 cycles) {s['range_recent']} days. "
            f"{s['inside_range_pct']}% of cycles fell inside the usual range for age "
            f"({ana['reference']['low']}-{ana['reference']['high']} days).", st["body"]))
        chart = _interval_chart(ana["intervals"], ana["reference"]["low"], ana["reference"]["high"])
        if chart:
            story += [Spacer(1, 4), chart]
    else:
        story.append(Paragraph("Not enough recorded cycles for statistics (at least 3 are needed).", st["body"]))

    # ---- 4. observed patterns
    story.append(Paragraph("4. Observed patterns (automated, not a diagnosis)", st["h2"]))
    story.append(Paragraph(f"<b>Overall:</b> {ana['status_label']}. {ana['headline']}", st["body"]))
    story.append(Spacer(1, 3))
    if ana["findings"]:
        rows = []
        for f in ana["findings"]:
            label, col = SEV_STYLE.get(f["severity"], SEV_STYLE["info"])
            rows.append([Paragraph(f'<font color="{col.hexval()}"><b>{label}</b></font>', st["cell"]),
                         Paragraph(f"<b>{f['title']}</b><br/>{f['text']}", st["cell"])])
        t = Table(rows, colWidths=[28 * mm, W - 28 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDD6EA")),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story.append(t)

    # ---- 5. symptoms
    story.append(Paragraph("5. Symptoms and bleeding logged (most recent)", st["h2"]))
    flow = {f["log_date"]: f["flow_intensity"] for f in snap["flows"]}
    sym = snap["symptoms"]
    if not sym and not flow:
        story.append(Paragraph("No daily symptom or flow entries have been recorded.", st["body"]))
    else:
        lv = {0: "-", 1: "mild", 2: "moderate", 3: "strong"}
        rows = [["Date", "Pain /10", "Flow /5", "Mood", "Fatigue", "Bloating", "Acne", "Headache"]]
        dates = sorted(set([x["log_date"] for x in sym]) | set(flow), reverse=True)[:12]
        by_date = {x["log_date"]: x for x in sym}
        for d in dates:
            x = by_date.get(d, {})
            rows.append([d.strftime("%d %b %Y"), str(x.get("pain_severity", "-") if x.get("pain_severity") is not None else "-"),
                         str(flow.get(d, "-")), lv.get(x.get("mood"), "-"), lv.get(x.get("fatigue"), "-"),
                         lv.get(x.get("bloating"), "-"), lv.get(x.get("acne"), "-"), lv.get(x.get("headache"), "-")])
        story.append(_table(rows, [26 * mm] + [(W - 26 * mm) / 7] * 7))
        pains = [x["pain_severity"] for x in sym if x.get("pain_severity") is not None]
        if pains:
            story.append(Spacer(1, 3))
            story.append(Paragraph(f"Average logged pain: {sum(pains)/len(pains):.1f}/10 over {len(pains)} day(s); "
                                   f"highest {max(pains)}/10.", st["body"]))

    # ---- 6. lifestyle
    life = snap["lifestyle"]
    story.append(Paragraph("6. Lifestyle summary (self-logged)", st["h2"]))
    if life:
        def avg(key):
            v = [float(x[key]) for x in life if x.get(key) is not None]
            return f"{sum(v)/len(v):.1f}" if v else "n/a"
        story.append(Paragraph(
            f"{len(life)} day(s) logged. Average sleep {avg('sleep_hours')} h, stress {avg('stress_level')}/5, "
            f"exercise {avg('exercise_minutes')} min/day, meals skipped per day {avg('meals_skipped')}. "
            f"Exam-period days: {sum(1 for x in life if x.get('exam_period'))}.", st["body"]))
    else:
        story.append(Paragraph("No lifestyle entries recorded.", st["body"]))

    # ---- 7. prediction
    story.append(Paragraph("7. Next-period estimate (machine learning, not a guarantee)", st["h2"]))
    if pred["available"]:
        story.append(Paragraph(
            f"Estimated next period start: <b>{pred['next_start'].strftime('%d %b %Y')}</b> "
            f"(likely window {pred['range_start'].strftime('%d %b')} - {pred['range_end'].strftime('%d %b %Y')}). "
            f"Method: {pred['method_label']}. Confidence: {pred['confidence']}, based on {pred['n_usable']} cycle(s).", st["body"]))
    else:
        story.append(Paragraph("Not enough history for an estimate.", st["body"]))
    story.append(Paragraph(
        "Model notes: trained on the public Kaggle/FedCycle dataset (adult fertility-charting participants, median "
        "age about 31) - not on college students. In testing, average error was roughly 2 days and the model was "
        "only slightly better than averaging recent cycles. Not for contraception or fertility planning.", st["small"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
