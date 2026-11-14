"""Build the defence slides (PowerPoint) with speaker notes.

    python tools/build_slides.py

Writes 07_presentation/slides.pptx; convert to PDF with
`soffice --headless --convert-to pdf --outdir 07_presentation 07_presentation/slides.pptx`.
Every figure comes from 06_rapport/figures or from the application screenshots.
"""

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "06_rapport" / "figures"
SHOTS = ROOT / "05_web_app" / "assets" / "screenshots"
INK, CHURN, RETENTION, GREY, MIST, PAPER = (RGBColor(0x14, 0x21, 0x3D), RGBColor(0xD6, 0x28, 0x39),
                                            RGBColor(0x2A, 0x9D, 0x8F), RGBColor(0x6B, 0x72, 0x80),
                                            RGBColor(0xE9, 0xEC, 0xEF), RGBColor(0xFA, 0xFA, 0xF7))
W, H = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width, prs.slide_height = W, H
BLANK = prs.slide_layouts[6]
count = {"n": 0}


def text(slide, x, y, w, h, content, size=18, bold=False, colour=INK, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    lines = content if isinstance(content, list) else [content]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(size), bold, colour, "Calibri"
        p.space_after = Pt(6)
    return box


def bullets(slide, x, y, w, h, items, size=17):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        bold_part, _, rest = item.partition("|")
        r = p.add_run()
        r.text = "▪  " + bold_part
        r.font.size, r.font.color.rgb, r.font.name, r.font.bold = Pt(size), INK, "Calibri", bool(rest)
        if rest:
            r2 = p.add_run()
            r2.text = rest
            r2.font.size, r2.font.color.rgb, r2.font.name = Pt(size), RGBColor(0x1F, 0x29, 0x37), "Calibri"
        p.space_after = Pt(10)


def picture(slide, path, x, y, max_w, max_h):
    iw, ih = Image.open(path).size
    scale = min(max_w / iw, max_h / ih)
    w, h = int(iw * scale), int(ih * scale)
    slide.shapes.add_picture(str(path), x + (max_w - w) // 2, y + (max_h - h) // 2, w, h)


def slide(title, speaker, notes, section=""):
    s = prs.slides.add_slide(BLANK)
    count["n"] += 1
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, Inches(0.12))
    bar.fill.solid(); bar.fill.fore_color.rgb = INK; bar.line.fill.background()
    accent = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.18), Inches(1.2), Inches(0.06))
    accent.fill.solid(); accent.fill.fore_color.rgb = CHURN; accent.line.fill.background()
    if section:
        text(s, Inches(0.6), Inches(0.28), Inches(9), Inches(0.35), section.upper(), 11, True, CHURN)
    text(s, Inches(0.6), Inches(0.5), Inches(12), Inches(0.7), title, 28, True, INK)
    text(s, Inches(0.6), Inches(7.05), Inches(8), Inches(0.3), f"VIGIE · Group BI 5 · {speaker}", 10, colour=GREY)
    text(s, Inches(11.7), Inches(7.05), Inches(1.1), Inches(0.3), str(count["n"]), 10, colour=GREY, align=PP_ALIGN.RIGHT)
    s.notes_slide.notes_text_frame.text = f"[{speaker}] " + notes
    return s


def kpi(s, x, y, value, label, colour=INK, w=Inches(2.9)):
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, Inches(1.35))
    box.fill.solid(); box.fill.fore_color.rgb = PAPER; box.line.color.rgb = MIST
    box.adjustments[0] = 0.12
    text(s, x + Inches(0.15), y + Inches(0.1), w - Inches(0.3), Inches(0.7), value, 30, True, colour)
    text(s, x + Inches(0.15), y + Inches(0.8), w - Inches(0.3), Inches(0.5), label, 12, colour=GREY)


L, T, FW, FH = Inches(0.6), Inches(1.45), Inches(12.1), Inches(5.45)

# 1 — Cover --------------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
count["n"] += 1
bg = s.background.fill
bg.solid(); bg.fore_color.rgb = INK
logo = ROOT / "06_rapport" / "figures" / "_logo.png"
text(s, Inches(0.9), Inches(1.4), Inches(11), Inches(0.5), "ESPRIT SCHOOL OF BUSINESS · INTEGRATED PROJECT 2026", 14, True, RGBColor(0xCB, 0xD5, 0xE1))
text(s, Inches(0.9), Inches(2.0), Inches(11), Inches(1.3), "VIGIE", 80, True, RGBColor(0xFF, 0xFF, 0xFF))
text(s, Inches(0.9), Inches(3.35), Inches(11), Inches(0.6), "Customer churn analysis and prediction", 28, colour=RGBColor(0xFF, 0xFF, 0xFF))
text(s, Inches(0.9), Inches(4.0), Inches(11), Inches(0.5), "See churn coming. Act before the account closes.", 18, colour=RGBColor(0xF4, 0xA2, 0x61))
text(s, Inches(0.9), Inches(5.2), Inches(11.5), Inches(1.2),
     ["Group BI 5 — Raed Meddeb · Ibrahim Grira · Salsabil Ben Elhadj · Salah Chebbi · Ines Ayed",
      "Supervisors: Aymen Ben Brik and Hela Hammami"], 16, colour=RGBColor(0xE5, 0xE7, 0xEB))
s.notes_slide.notes_text_frame.text = ("[Raed] Good morning. We are Group BI 5 and our project is called VIGIE — French for "
                                       "'lookout'. In 20 minutes we will show how we went from a raw banking file to a deployed "
                                       "tool that measures and anticipates churn. Each of us will present the part they led.")

# 2 — Problem and approach -----------------------------------------------------------------------------
s = slide("The question: understand, measure and anticipate churn", "Raed Meddeb", (
    "The bank gave us an anonymised snapshot of 363 thousand customers. Our goal was to answer three questions: how much "
    "churn, where and why, and what comes next. We followed the five phases of the project, with one rule: verify every "
    "number before using it."), "Introduction")
bullets(s, L, T + Inches(0.1), Inches(6.2), Inches(5), [
    "Anonymised banking snapshot|: 483,536 rows · 363,024 customers · 410,309 accounts",
    "Churn = account closed|; a customer churns when all accounts are closed",
    "Five phases|: data → warehouse → reporting → prediction → application",
    "One rule|: every figure is verified — checks, reference values, reproducible models",
    "Privacy by design|: no data in the repository, aggregates only in the app"])
kpi(s, Inches(7.4), T + Inches(0.1), "36.1%", "churn rate per account", CHURN)
kpi(s, Inches(10.4), T + Inches(0.1), "36.8%", "churn rate per customer", CHURN)
kpi(s, Inches(7.4), T + Inches(1.7), "51%", "of closures in 5 mass weeks")
kpi(s, Inches(10.4), T + Inches(1.7), "0.751", "ROC-AUC of the churn model", RETENTION)
kpi(s, Inches(7.4), T + Inches(3.3), "19 / 19", "warehouse checks passed", RETENTION)
kpi(s, Inches(10.4), T + Inches(3.3), "26", "automated tests")

# 3 — Architecture -------------------------------------------------------------------------------------
s = slide("Architecture: one chain, one code base", "Raed Meddeb", (
    "Six stages. The key design choice is the shared library: the warehouse, the notebooks and the application compute "
    "every number with the same code, so a figure cannot differ from one deliverable to another."), "Introduction")
picture(s, FIG / "architecture.png", L, T, FW, FH)

# 4 — Data: grain ------------------------------------------------------------------------------------------
s = slide("Phase 1 · A rate is meaningless without its grain", "Ines Ayed", (
    "First finding: the file mixes three grains. The same data gives 40, 36 or 32 percent of churn depending on what you "
    "count. We fixed two grains: the account for the warehouse, the customer for the model. And no customer is both active "
    "and closed — which makes customer churn unambiguous."), "Understanding the data")
picture(s, FIG / "01_churn_rate_by_grain.png", L, T + Inches(0.3), Inches(6.3), Inches(3.4))
bullets(s, Inches(7.2), T + Inches(0.2), Inches(5.6), Inches(5), [
    "Volumes match the supervisors' document|: to the unit",
    "One row = customer × account × product|: 9% of rows have no account",
    "No customer is both active and closed|: customer churn is unambiguous",
    "Moderate imbalance (36.8%)|: no rebalancing needed",
    "Anomaly|: 20,166 accounts closed before they were opened — flagged"])

# 5 — Missing values / leak ------------------------------------------------------------------------------
s = slide("Phase 1 · Some blanks give the answer away", "Ines Ayed", (
    "Missing values are not all the same. The important ones: balance, account family, currency and opening date are "
    "blank for 68 percent of closed accounts and never for active ones. They record the departure — so they cannot be "
    "used to predict it. Outliers: a third of balances are 'outliers', but they are loans in debit, not errors."),
    "Understanding the data")
picture(s, FIG / "01_missing_values.png", L, T, Inches(5.6), FH)
bullets(s, Inches(6.6), T + Inches(0.2), Inches(6.2), Inches(5), [
    "Structural, business, declarative blanks|: typed one by one",
    "Tied to the closure|: blank for 67.8% of closed accounts, 0% of active ones → target leak",
    "Outliers (IQR)|: 32% of balances — loan accounts in debit, not errors",
    "No row deleted|: flags and medians instead",
    "Bivariate (bonus)|: incomplete file → 49.6% churn vs 22.5%"])

# 6 — Star schema ---------------------------------------------------------------------------------------
s = slide("Phase 2 · Star schema at account grain", "Salsabil Ben Elhadj", (
    "One fact table, one row per account, eight dimensions. Two choices matter: a 'Not provided' member with key zero, so "
    "no join ever loses rows, and a calendar built in SQL that plays two roles — opening and closing."), "Data warehouse and ETL")
picture(s, ROOT / "02_data_warehouse" / "schema" / "star_schema.png", L, T, Inches(7.6), FH)
bullets(s, Inches(8.4), T + Inches(0.2), Inches(4.5), Inches(5), [
    "fact_account|: 410,309 accounts",
    "8 dimensions|: customer keeps the 43,984 customers with no account",
    "Key 0 = Not provided|: no null foreign key",
    "Calendar in SQL|: two roles",
    "Bonus|: SCD type 2 on the customer"])

# 7 — ETL + checks --------------------------------------------------------------------------------------
s = slide("Phase 2 · ETL and 19 checks, 19 OK", "Salsabil Ben Elhadj", (
    "The flow: staging, transformation, load. The Talend jobs are specified component by component, and a Python pipeline "
    "gives the reference load. Then 19 checks compare source and warehouse: volumes, KPIs, integrity. All pass."),
    "Data warehouse and ETL")
picture(s, ROOT / "01_etl" / "etl_flow.png", L, T, FW, Inches(3.6))
bullets(s, L, T + Inches(3.75), FW, Inches(1.8), [
    "Volumes|: 483,536 rows · 410,309 accounts · 363,024 customers — identical on both sides",
    "Indicators|: 148,215 closures · churn 36.12% · first closing date kept · balances reconciled",
    "Integrity|: no duplicate, no orphan, every date in the calendar, anomalies flagged"], 15)

# 8 — Power BI ------------------------------------------------------------------------------------------
s = slide("Phase 3 · Reporting: 3 pages, 30 documented DAX measures", "Ines Ayed", (
    "Thirty DAX measures, each with the value it must show — so the report can be checked number by number. Two rules: a "
    "rate at its grain, and inactive date relationships so that a date filter never distorts the global KPIs. The JavaScript "
    "dashboard is our bonus and our mockup."), "Reporting")
picture(s, ROOT / "03_power_bi" / "mockups" / "page2_churn_analysis.png", L, T, Inches(6.8), FH)
bullets(s, Inches(7.6), T + Inches(0.2), Inches(5.2), Inches(5), [
    "Pages|: overview · churn analysis · segmentation",
    "Account Churn Rate = 36.12%|: Customer Churn Rate = 36.78%",
    "Two inactive date relationships|: USERELATIONSHIP per measure",
    "\"Not provided\" stays visible|: 68% of closed accounts",
    "Bonus|: Chart.js dashboard, offline, phone-friendly"])

# 9 — KPI series --------------------------------------------------------------------------------------
s = slide("Phase 4 · The KPI: weekly closures — and 5 mass weeks", "Salah Chebbi", (
    "Our KPI is the number of accounts closed per week. Five weeks carry half of all closures: they are batch operations, "
    "with 'Other' as reason in 99.5 percent of cases. They cannot be forecast, so we corrected the series and forecast the "
    "ordinary activity."), "Predictive models")
picture(s, FIG / "04_corrected_series.png", L, T, Inches(7.6), FH)
bullets(s, Inches(8.4), T + Inches(0.2), Inches(4.5), Inches(5), [
    "202 weeks|: 11 zero weeks added",
    "5 weeks = 51% of closures|: batch operations",
    "Corrected series|: local median",
    "Three regimes|: no calendar seasonality",
    "8-week window|: MAE / RMSE (no MAPE)"])

# 10 — LSTM ---------------------------------------------------------------------------------------------
s = slide("Phase 4 · LSTM: −40% vs naive, but a median does as well", "Salah Chebbi", (
    "The LSTM cuts the error of the naive forecast by 40 percent and beats the simple RNN and ARIMA. But an 8-week moving "
    "median does slightly better. With 202 weeks, a regime change and random spikes, that is expected, and we show it "
    "instead of hiding it. On the second KPI, customers lost, the LSTM is the best."), "Predictive models")
picture(s, FIG / "04_lstm_vs_references.png", L, T, FW, Inches(3.9))
bullets(s, L, T + Inches(4.05), FW, Inches(1.5), [
    "LSTM MAE 287|  ·  moving median 272  ·  RNN 324  ·  ARIMA 335  ·  naive 478 (last 40 weeks)",
    "Second KPI (bonus)|: customers lost per week — the LSTM has the best MAE (125 vs 133)"], 15)

# 11 — Leakage ------------------------------------------------------------------------------------------
s = slide("Phase 4 · Leakage check: a 0.95 AUC would be a lie", "Raed Meddeb", (
    "Before modelling churn, we tested every column: can its blanks alone guess the target? Ten columns can. If we keep "
    "only three blank flags, the AUC jumps to 0.95. That is not a good model, it is a model reading the answer. Without "
    "them we get 0.75 — the honest level."), "Predictive models")
picture(s, FIG / "04_leakage_blank_test.png", L, T, Inches(6.2), FH)
kpi(s, Inches(7.4), T + Inches(0.4), "0.951", "ROC-AUC with 3 leaking flags", CHURN, Inches(5.3))
kpi(s, Inches(7.4), T + Inches(2.0), "0.751", "ROC-AUC without them — the model kept", RETENTION, Inches(5.3))
text(s, Inches(7.4), T + Inches(3.6), Inches(5.3), Inches(1.5),
     "10 columns excluded: closing date and reason, balance, opening date, family, currency, amount, product. "
     "PRODUCT_STATUS excluded for its values.", 14, colour=GREY)

# 12 — Churn models -------------------------------------------------------------------------------------
s = slide("Phase 4 · Churn model: XGBoost, AUC 0.751, recall 79%", "Raed Meddeb", (
    "Customer grain, twelve profile features, a split per customer so nobody is in both training and test. Three models; "
    "XGBoost wins and is well calibrated. At our threshold it catches 79 percent of the leavers. Targeting the top 30 "
    "percent of scores reaches half of the departures."), "Predictive models")
picture(s, FIG / "04_churn_roc_pr.png", L, T, Inches(6.9), Inches(3.3))
picture(s, FIG / "04_churn_calibration_gains.png", L, T + Inches(3.35), Inches(6.9), Inches(2.1))
bullets(s, Inches(7.8), T + Inches(0.2), Inches(5.0), Inches(5), [
    "Logistic regression|: 0.686",
    "Random Forest|: 0.748",
    "Tuned XGBoost|: 0.751 · PR-AUC 0.611",
    "Calibrated|: within 1.5 pt per decile",
    "Gains|: top 30% of scores → 50% of departures",
    "Risk levels|: 15% · 38% · 61% observed departures"])

# 13 — SHAP ---------------------------------------------------------------------------------------------
s = slide("Phase 4 · Why customers leave", "Raed Meddeb", (
    "SHAP tells us why. The strongest signal is an overdue file review. Churn peaks at 25 to 44 years and after 5 to 10 "
    "years of relationship, and holding several accounts protects. The segment barely matters. Caveat: a neglected file can "
    "also be a consequence of leaving — so we report the model with and without these features."), "Predictive models")
picture(s, FIG / "04_churn_shap_summary.png", L, T, Inches(6.6), FH)
bullets(s, Inches(7.5), T + Inches(0.2), Inches(5.3), Inches(5), [
    "Overdue review|: +0.53 — the first warning sign",
    "Recent review|: −0.53 — protects",
    "25–44 years, 5–10 years of tenure|: the fragile zone",
    "Two accounts or more|: −0.20",
    "Compliance = 62% of importance|: segment < 2%",
    "Honest bound|: AUC 0.751 with, 0.660 without compliance"])

# 14 — App ---------------------------------------------------------------------------------------------
s = slide("Phase 5 · The VIGIE application", "Ibrahim Grira", (
    "The application has five pages around the three required features: summary KPIs, an explained prediction on a "
    "fictitious profile, and the LSTM forecast. It only reads aggregates and the model's trees in JSON — no customer data. "
    "Live demo next."), "Application")
picture(s, SHOTS / "02_prediction.png", L, T, Inches(5.8), FH)
bullets(s, Inches(6.7), T + Inches(0.2), Inches(6.1), Inches(5), [
    "Overview|: 8 KPIs, churn by axis, closures and forecast",
    "Prediction|: fictitious profile → score, risk level, SHAP drivers, action",
    "Forecast|: LSTM 8 weeks + comparison with references",
    "Segments · Method and team",
    "No data|: aggregates (≥ 20) and JSON trees only",
    "Same encoder as training|: no gap between model and app"])

# 15 — UML ----------------------------------------------------------------------------------------------
s = slide("Phase 5 · UML: use cases, sequence, classes", "Ibrahim Grira", (
    "Three diagrams: the global use cases with four actors, the sequence of a prediction request, and the classes of the "
    "application — the model, the prediction, the artefact store and the fictitious generator."), "Application")
picture(s, ROOT / "05_web_app" / "docs" / "uml" / "use_case.png", L, T, Inches(6.0), FH)
picture(s, ROOT / "05_web_app" / "docs" / "uml" / "prediction_sequence.png", Inches(6.8), T, Inches(5.9), FH)

# 16 — DevOps -------------------------------------------------------------------------------------------
s = slide("Phase 5 · Tests, CI and data protection", "Ibrahim Grira", (
    "Twenty-six automated tests run on every push with GitHub Actions. They check the encoding, the model, every page of "
    "the app — and the confidentiality rules: if anyone commits a data file or a customer identifier, the build fails."),
    "Application")
kpi(s, L, T + Inches(0.2), "26", "automated tests (pytest)", RETENTION)
kpi(s, Inches(3.7), T + Inches(0.2), "5 / 5", "pages tested end to end")
kpi(s, Inches(6.8), T + Inches(0.2), "0", "data files in the repository", RETENTION)
kpi(s, Inches(9.9), T + Inches(0.2), "100%", "metrics reproduced by train.py")
bullets(s, L, T + Inches(2.0), FW, Inches(3.5), [
    "Encoding|: fixed columns, missing values, unknown categories, KYC review cycle",
    "Model|: probabilities, exact SHAP explanation, direction of effects, fictitious portfolio",
    "Application|: every page runs; the form reacts in the right direction",
    "Confidentiality|: no data file, no identifier, no aggregate below 20, consistent volumes",
    "Deployment|: Streamlit Community Cloud — no TensorFlow, no .pkl needed"])

# 17 — Demo --------------------------------------------------------------------------------------------
s = slide("Live demo", "Ibrahim Grira", (
    "Demo plan (5 minutes): overview and the grain note; prediction with the default profile, then move 'months since last "
    "review' to 100 and show the score and the drivers change; fictitious portfolio; forecast page. Backup: the video in "
    "07_presentation if the network fails."), "Application")
picture(s, SHOTS / "01_overview.png", L, T, Inches(6.0), FH)
bullets(s, Inches(6.9), T + Inches(0.2), Inches(5.9), Inches(5), [
    "1 · Overview|: KPIs and \"a rate at its grain\"",
    "2 · Prediction|: default profile → overdue review → score rises",
    "3 · Fictitious portfolio|: who to call first",
    "4 · Forecast|: next 8 weeks, honest comparison",
    "Backup|: recorded video"])

# 18 — Limits -------------------------------------------------------------------------------------------
s = slide("Limitations and next steps", "Salah Chebbi", (
    "Our limits: a single snapshot, no behavioural data, batch closures mixed with real departures, and a short series. "
    "Next steps: separate batch closures at the source, add monthly behavioural snapshots, re-train regularly, and measure "
    "the value of a retention campaign against a control group."), "Conclusion")
bullets(s, L, T + Inches(0.2), Inches(5.9), Inches(5), [
    "A snapshot, not a film|: some features may follow the departure",
    "No behavioural data|: AUC capped at 0.75",
    "Batch closures|: half of the \"churn\"",
    "202 weeks, 3 regimes|: hard to forecast"])
bullets(s, Inches(6.9), T + Inches(0.2), Inches(5.9), Inches(5), [
    "Separate batch closures| from real departures",
    "Monthly behavioural snapshots| (balances, complaints)",
    "Re-train regularly|: LSTM next to the median",
    "Measure value|: campaign vs control group"])

# 19 — Conclusion ----------------------------------------------------------------------------------------
s = slide("Conclusion: watch the files nobody reviews", "Raed Meddeb", (
    "To conclude: we delivered the full chain, and every stage is verified. The main lesson: question the numbers before "
    "trusting them. And the business message: an overdue file review is the strongest warning sign — the bank can act on "
    "it today. Thank you; we are happy to take your questions."), "Conclusion")
bullets(s, L, T + Inches(0.3), FW, Inches(4.6), [
    "Complete chain|: data → warehouse → Power BI → LSTM and XGBoost → web application",
    "Verified at every step|: 19 checks · reference values for every DAX measure · reproducible models · 26 tests",
    "Lessons|: a rate needs its grain; blanks can fake a perfect model; a deep network does not always beat a median",
    "Business message|: an overdue file review is the strongest warning sign — act on it"], 19)
text(s, L, Inches(6.2), FW, Inches(0.6), "Thank you — questions?", 24, True, CHURN, PP_ALIGN.CENTER)

out = ROOT / "07_presentation" / "slides.pptx"
out.parent.mkdir(exist_ok=True)
prs.save(out)
print(f"written: {out.relative_to(ROOT)} ({count['n']} slides)")
