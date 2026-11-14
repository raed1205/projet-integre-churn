"""Generate the project diagrams in the VIGIE colours (no data is read).

    python tools/diagrams.py

Produces:
    02_data_warehouse/schema/star_schema.png   star schema
    01_etl/etl_flow.png                        end-to-end ETL flow
    06_rapport/figures/architecture.png        solution architecture
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vigie import config, style  # noqa: E402

C = config.COLORS
ROW_HEIGHT = 0.27
TITLE_HEIGHT = 0.42


def table(ax, x, y, width, title, columns, color, caption=None):
    """Draw a table (title + columns). (x, y) = top-left corner. Returns its box."""
    h = TITLE_HEIGHT + ROW_HEIGHT * len(columns) + 0.12
    ax.add_patch(FancyBboxPatch((x, y - h), width, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc="white", ec=color, lw=1.6, zorder=2))
    ax.add_patch(FancyBboxPatch((x, y - TITLE_HEIGHT), width, TITLE_HEIGHT,
                                boxstyle="round,pad=0.02,rounding_size=0.08", fc=color, ec=color, lw=1.6, zorder=3))
    ax.text(x + width / 2, y - TITLE_HEIGHT / 2, title, ha="center", va="center", color="white",
            fontweight="bold", fontsize=9.5, zorder=4)
    for i, col in enumerate(columns):
        is_key = col.startswith(("PK ", "FK "))
        ax.text(x + 0.12, y - TITLE_HEIGHT - 0.06 - ROW_HEIGHT * (i + 0.5), col, ha="left", va="center",
                fontsize=7.6, color=C["ink"] if is_key else C["text"], fontweight="bold" if is_key else "normal",
                family="DejaVu Sans Mono", zorder=4)
    if caption:
        ax.text(x + width / 2, y - h - 0.14, caption, ha="center", va="top", fontsize=7.4, color=C["grey"],
                style="italic")
    return (x, y - h, width, h)


def star_schema():
    style.apply()
    fig, ax = plt.subplots(figsize=(15, 10.2))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 10.2)
    ax.axis("off")

    fact = table(ax, 5.55, 7.75, 3.9, "fact_account", [
        "PK account_id", "   account_code", "FK customer_id", "FK branch_id", "FK industry_id", "FK category_id",
        "FK currency_id", "FK reason_id", "FK product_id", "FK opening_date_id", "FK closing_date_id",
        "   is_closed           (target)", "   balance · is_overdrawn", "   product_amount · fixed_rate",
        "   account_age_days", "   opened_after_closing", "   product_status", "   n_source_rows",
    ], C["churn"], "Grain: 1 row = 1 account · 410,309 rows")

    dims = [
        table(ax, 0.35, 9.75, 3.7, "dim_customer", [
            "PK customer_id", "   customer_code", "   nationality_zone · residence_zone", "   marital_status",
            "   age · age_band", "   customer_type · segment", "   line_of_business",
            "   tenure_years · tenure_band", "   declared_income · n_accounts", "   kyc_score · file_complete",
            "   review dates · review_overdue", "   is_churned"], C["ink"], "363,024 customers"),
        table(ax, 0.35, 4.55, 3.7, "dim_date", [
            "PK date_id (YYYYMMDD)", "   full_date", "   year · quarter · month", "   month_name · year_month",
            "   iso_week · week_start", "   day_of_week · day_name"], C["ink"],
            "Calendar built here (1978–2031)\nplays 2 roles: opening and closing"),
        table(ax, 0.35, 1.45, 3.7, "dim_branch", [
            "PK branch_id", "   group_code · label", "   is_masked"], C["ink"], None),
        table(ax, 10.95, 9.75, 3.7, "dim_account_category", [
            "PK category_id", "   category_code · label", "   family"], C["ink"], "ACCOUNT_CATEGORY.xlsx"),
        table(ax, 10.95, 7.6, 3.7, "dim_product", [
            "PK product_id", "   product_group", "   product_line"], C["ink"], None),
        table(ax, 10.95, 5.6, 3.7, "dim_currency", [
            "PK currency_id", "   currency_code · label"], C["ink"], "CURRENCY.xlsx"),
        table(ax, 10.95, 3.75, 3.7, "dim_closure_reason", [
            "PK reason_id", "   reason_code · label"], C["ink"], "CLOSURE_REASON.xlsx"),
        table(ax, 10.95, 1.9, 3.7, "dim_industry", [
            "PK industry_id", "   industry_code · label"], C["ink"], "INDUSTRY.xlsx"),
    ]
    for d in dims:
        left = d[0] < 5
        start = (fact[0] if left else fact[0] + fact[2], fact[1] + fact[3] / 2 + (d[1] + d[3] / 2 - 5) * 0.55)
        end = (d[0] + d[2] if left else d[0], d[1] + d[3] / 2)
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-", lw=1.3, color=C["grey"], zorder=1))
        ax.text(end[0] + (0.12 if left else -0.12), end[1] + 0.13, "1", fontsize=8, color=C["grey"],
                ha="left" if left else "right")
        ax.text(start[0] + (-0.12 if left else 0.12), start[1] + 0.13, "n", fontsize=8, color=C["grey"],
                ha="right" if left else "left")

    ax.text(0.35, 10.05, "Star schema of the warehouse — dwh schema", fontsize=15, fontweight="bold",
            color=C["ink"], va="bottom")
    ax.text(14.65, 0.12, f"{config.PROJECT_NAME} · {config.GROUP} · key 0 of every dimension = \"Not provided\"",
            fontsize=8, color=C["grey"], ha="right")
    path = ROOT / "02_data_warehouse" / "schema" / "star_schema.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def box(ax, x, y, w, h, title, lines, color, fill="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1", fc=fill, ec=color,
                                lw=1.6, zorder=2))
    ax.text(x + w / 2, y + h - 0.26, title, ha="center", va="center", fontweight="bold", fontsize=9.5,
            color=color if fill == "white" else "white", zorder=3)
    for i, line in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.6 - 0.27 * i, line, ha="center", va="center", fontsize=7.8,
                color=C["text"] if fill == "white" else "white", zorder=3)
    return (x, y, w, h)


def arrow(ax, a, b, text=None):
    p1, p2 = (a[0] + a[2], a[1] + a[3] / 2), (b[0], b[1] + b[3] / 2)
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=14, lw=1.6, color=C["ink"], zorder=1))
    if text:
        ax.text((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + 0.16, text, ha="center", fontsize=7.5, color=C["grey"])


def etl_flow():
    style.apply()
    fig, ax = plt.subplots(figsize=(15, 6.6))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 6.6)
    ax.axis("off")
    ax.text(0.3, 6.25, "ETL flow — from the source files to the warehouse", fontsize=15, fontweight="bold", color=C["ink"])

    src = box(ax, 0.3, 2.2, 2.4, 3.3, "Sources", [
        "data_churn.csv", "483,536 rows · 32 cols", "", "5 Excel reference files", "category · reason · currency",
        "industry · line of business"], C["grey"])
    stg = box(ax, 3.5, 2.2, 2.4, 3.3, "STAGING", [
        "staging schema", "stg_churn", "stg_* (reference files)", "", "raw copy, all text",
        "no transformation"], C["sky"])
    trf = box(ax, 6.7, 2.2, 3.1, 3.3, "TRANSFORM", [
        "1. YYYYMMDD dates → date", "2. exact duplicates absorbed", "3. account grain: 1st closing",
        "4. customer grain: accounts, churn", "5. join the 5 reference files", "6. blanks → member \"0\"",
        "7. derived variables", "   (age, tenure, review)", "8. date anomalies flagged"], C["amber"])
    dwh = box(ax, 10.6, 2.2, 2.0, 3.3, "WAREHOUSE", [
        "dwh schema", "8 dimensions", "then fact_account", "", "410,309 accounts", "363,024 customers"], C["churn"])
    use = box(ax, 13.2, 2.2, 1.55, 3.3, "Uses", ["Power BI", "(DAX)", "", "Models", "ML / LSTM", "Web app"],
              C["retention"])
    arrow(ax, src, stg, "Extract")
    arrow(ax, stg, trf, "Transform")
    arrow(ax, trf, dwh, "Load")
    arrow(ax, dwh, use)

    jobs = [
        ("J01_Staging", "tFileInputDelimited\ntFileInputExcel → tDBOutput", 0.3),
        ("J02_Dim_References", "tDBInput → tMap\n→ tDBOutput (6 dims)", 3.25),
        ("J03_Dim_Customer", "tDBInput → tMap\n(2 lookups) → tDBOutput", 6.2),
        ("J04_Fact_Account", "tDBInput (GROUP BY) → tMap\n(7 lookups) → tDBOutput", 9.15),
        ("J05_Checks", "tDBRow (checks.sql)\n→ tLogRow / tDie", 12.1),
    ]
    for name, detail, x in jobs:
        ax.add_patch(FancyBboxPatch((x, 0.45), 2.65, 1.15, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    fc=C["ink"], ec=C["ink"], zorder=2))
        ax.text(x + 1.325, 1.3, name, ha="center", va="center", color="white", fontweight="bold", fontsize=9, zorder=3)
        ax.text(x + 1.325, 0.82, detail, ha="center", va="center", color="white", fontsize=7.3, zorder=3)
    for x in [2.95, 5.9, 8.85, 11.8]:
        ax.add_patch(FancyArrowPatch((x, 1.02), (x + 0.3, 1.02), arrowstyle="-|>", mutation_scale=12, lw=1.4,
                                     color=C["ink"]))
    ax.text(0.3, 1.85, "Talend jobs, chained by J00_Orchestration (tRunJob) — Python equivalent: 01_etl/python_pipeline/etl.py",
            fontsize=8.6, color=C["ink"], fontweight="bold")
    ax.text(14.75, 0.08, f"{config.PROJECT_NAME} · {config.GROUP}", fontsize=8, color=C["grey"], ha="right")
    path = ROOT / "01_etl" / "etl_flow.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def architecture():
    style.apply()
    fig, ax = plt.subplots(figsize=(15, 6.2))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 6.2)
    ax.axis("off")
    ax.text(0.3, 5.85, "Architecture of the VIGIE solution", fontsize=15, fontweight="bold", color=C["ink"])
    stages = [
        ("1 · Data", ["CSV + 5 Excel files", "anonymised", "", "Python · pandas", "univariate analysis", "missing · outliers"], C["grey"]),
        ("2 · ETL", ["Talend", "extraction", "cleaning", "joins", "", "(+ Python pipeline)"], C["sky"]),
        ("3 · Warehouse", ["PostgreSQL", "pgAdmin", "", "star schema", "1 fact · 8 dimensions", "19 checks"], C["ink"]),
        ("4 · Reporting", ["Power BI", "DAX measures", "", "overview", "churn analysis", "segmentation"], C["amber"]),
        ("5 · Prediction", ["LSTM (Keras)", "weekly closures", "", "XGBoost", "churn score", "SHAP"], C["churn"]),
        ("6 · Application", ["Streamlit", "", "summary KPIs", "individual prediction", "KPI forecast", "tests · CI"], C["retention"]),
    ]
    boxes = [box(ax, 0.3 + i * 2.45, 2.2, 2.1, 2.9, title, lines, color) for i, (title, lines, color) in enumerate(stages)]
    for a, b in zip(boxes, boxes[1:]):
        arrow(ax, a, b)
    ax.add_patch(FancyBboxPatch((0.3, 0.55), 14.35, 1.05, boxstyle="round,pad=0.02,rounding_size=0.1",
                                fc=C["paper"], ec=C["mist"], lw=1.2))
    ax.text(7.5, 1.28, "Cross-cutting foundation", ha="center", fontweight="bold", fontsize=9.5, color=C["ink"])
    ax.text(7.5, 0.86, "Git / GitHub · shared vigie/ library (one code base for every figure) · "
                       "no data in the repository · aggregates and fictitious profiles only in the application",
            ha="center", fontsize=8.4, color=C["text"])
    ax.text(14.75, 0.12, f"{config.PROJECT_NAME} · {config.GROUP}", fontsize=8, color=C["grey"], ha="right")
    path = config.FIGURES / "architecture.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


if __name__ == "__main__":
    for f in (star_schema, etl_flow, architecture):
        print("written:", f().relative_to(ROOT))
