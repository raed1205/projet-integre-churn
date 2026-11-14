"""Export of the application artefacts: **aggregates and parameters, never a customer row**.

Three readable JSON files are written to ``05_web_app/artifacts/``:

* ``kpi_summary.json``       aggregated indicators (no count published below the confidentiality threshold);
* ``churn_model.json``       the trees of the XGBoost model (split thresholds and leaf values);
* ``churn_model_meta.json``  threshold, metrics, feature importance, marginal distributions.

A JSON file of trees holds no observation: only rules such as "tenure < 6.5 years". It can
therefore be published, unlike a ``.pkl`` file, which may embed training data — those stay in
``04_machine_learning/models/``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from vigie import config, data  # noqa: E402

MIN_CELL = config.MIN_CELL_SIZE


def _axis(table: pd.DataFrame, column, target: str, order: list | None = None) -> list[dict]:
    """Count and churn rate per category, hiding the small cells."""
    g = table.groupby(column, observed=True)[target].agg(["size", "mean"])
    g = g[g["size"] >= MIN_CELL]
    g = g.loc[[c for c in order if c in g.index]] if order else g.sort_values("size", ascending=False)
    return [{"category": str(c), "count": int(r["size"]), "churn_rate": round(float(r["mean"]), 4)}
            for c, r in g.iterrows()]


def summary_aggregates(df: pd.DataFrame, accounts: pd.DataFrame, customers: pd.DataFrame,
                       refs: dict[str, pd.DataFrame]) -> dict:
    """Every indicator displayed by the application and by the JavaScript interface."""
    ref_date = data.reference_date(df)
    c = customers[customers["CHURN"].notna()].copy()
    c["CHURN"] = c["CHURN"].astype(int)
    tenure = (ref_date - c["CUST_OPENING_DATE"]).dt.days / 365.25
    c["Age band"] = data.age_band(c["BIRTH_PERIOD"], ref_date.year)
    c["Tenure"] = data.tenure_band(tenure)
    c["Customer file"] = np.where(c["COMPLETED_FILE"] == "YES", "Complete", "Incomplete")
    c["File review"] = np.where(c["NEXT__REVIEW_DATE"] < ref_date, "Overdue", "Up to date")
    c["Number of accounts"] = c["N_ACCOUNTS"].clip(upper=5).map(lambda k: str(k) if k < 5 else "5 and more")
    c["Marital status"] = c["MARITAL_STATUS"].map(data.MARITAL_STATUS_LABELS).fillna(data.NOT_PROVIDED)
    c["KYC score"] = c["SCORE_KYC"].fillna(data.NOT_PROVIDED)
    c["Customer type"] = c["NATURE_CLIENT"].map(data.CUSTOMER_TYPE_LABELS)
    c["Residence zone"] = c["RESIDENCE_REGION"].map(data.english)
    industry = dict(zip(refs["INDUSTRY"]["INDUSTRY_CODE"], refs["INDUSTRY"]["DESCRIPTION"]))
    c["Industry"] = c["INDUSTRY"].map(industry).map(data.english)

    k = accounts.copy()
    k["Account family"] = k["ACCOUNT_TYPE_DESC"].map(data.english).fillna(data.NOT_PROVIDED)
    currency = dict(zip(refs["CURRENCY"]["CURRENCY_CODE"], refs["CURRENCY"]["DESCRIPTION"]))
    k["Currency"] = k["CURRENCY"].map(currency).map(data.english).fillna(data.NOT_PROVIDED)
    k["Product group"] = k["PRODUCT_GROUP"].map(data.english).fillna(data.NOT_PROVIDED)
    active = k[k["CHURN"] == 0]
    closed = k[k["CHURN"] == 1]
    reason = dict(zip(refs["CLOSURE_REASON"]["REASON_ID"], refs["CLOSURE_REASON"]["DESCRIPTION"]))
    reasons = closed["CLOSURE_REASON"].map(reason).map(data.english).fillna("Not entered").value_counts()

    # Customer value: median profile per segment (active accounts only, where the balance is filled in).
    customer_balance = active.groupby("CUSTOMER_NO")["ACCT_BALANCE"].sum().rename("TOTAL_BALANCE")
    seg = c.set_index("CUSTOMER_NO").join(customer_balance)
    segments = []
    for name, block in seg.groupby("PARTYCLASS"):
        if len(block) < MIN_CELL:
            continue
        segments.append({
            "segment": name, "customers": int(len(block)), "churn_rate": round(float(block["CHURN"].mean()), 4),
            "average_tenure": round(float(((ref_date - block["CUST_OPENING_DATE"]).dt.days / 365.25).mean()), 1),
            "accounts_per_customer": round(float(block["N_ACCOUNTS"].mean()), 2),
            "multi_account_share": round(float((block["N_ACCOUNTS"] > 1).mean()), 4),
            "complete_file_share": round(float((block["COMPLETED_FILE"] == "YES").mean()), 4),
            "median_balance_active_customers": round(float(block["TOTAL_BALANCE"].median()), 0),
        })
    segments.sort(key=lambda s: -s["customers"])

    return {
        "source": {"file": "data_churn.csv", "sha256": data.fingerprint()["sha256"],
                   "reference_date": str(ref_date.date()), "min_cell_size": MIN_CELL,
                   "note": "Aggregates only. Dates shifted and amounts rounded by the anonymisation."},
        "overall": {
            "source_rows": int(len(df)),
            "accounts": int(len(k)), "active_accounts": int(len(active)), "closed_accounts": int(len(closed)),
            "account_churn_rate": round(float(k["CHURN"].mean()), 4),
            "customers": int(len(customers)), "customers_with_account": int(len(c)),
            "churned_customers": int(c["CHURN"].sum()),
            "customer_churn_rate": round(float(c["CHURN"].mean()), 4),
            "all_customers_churn_rate": round(float(c["CHURN"].sum() / len(customers)), 4),
            "row_churn_rate": round(float((df["ACCOUNT_STATUS"] == "Closed").sum()
                                          / df["ACCOUNT_STATUS"].notna().sum()), 4),
            "average_customer_tenure": round(float(tenure.mean()), 2),
            "median_balance_active_accounts": float(active["ACCT_BALANCE"].median()),
            "overdrawn_share_active": round(float((active["ACCT_BALANCE"] < 0).mean()), 4),
            "multi_account_share": round(float((c["N_ACCOUNTS"] > 1).mean()), 4),
            "complete_file_share": round(float((c["COMPLETED_FILE"] == "YES").mean()), 4),
            "overdue_review_share": round(float((c["NEXT__REVIEW_DATE"] < ref_date).mean()), 4),
        },
        "customer_axes": {
            "Age band": _axis(c, "Age band", "CHURN", data.AGE_BANDS + [data.NOT_PROVIDED]),
            "Tenure": _axis(c, "Tenure", "CHURN", data.TENURE_BANDS + [data.NOT_PROVIDED]),
            "Customer file": _axis(c, "Customer file", "CHURN", ["Complete", "Incomplete"]),
            "File review": _axis(c, "File review", "CHURN", ["Up to date", "Overdue"]),
            "Number of accounts": _axis(c, "Number of accounts", "CHURN", ["1", "2", "3", "4", "5 and more"]),
            "Commercial segment": _axis(c, "PARTYCLASS", "CHURN"),
            "KYC score": _axis(c, "KYC score", "CHURN", ["LR", "MR", "H1", "H2", "H3"]),
            "Customer type": _axis(c, "Customer type", "CHURN"),
            "Marital status": _axis(c, "Marital status", "CHURN"),
            "Residence zone": _axis(c, "Residence zone", "CHURN"),
            "Branch group": _axis(c, "BRANCH_GROUP", "CHURN", sorted(c["BRANCH_GROUP"].unique())),
            "Industry": _axis(c, "Industry", "CHURN"),
        },
        "account_axes": {
            "Account family": _axis(k, "Account family", "CHURN"),
            "Currency": _axis(k, "Currency", "CHURN"),
            "Product group": _axis(k, "Product group", "CHURN"),
        },
        "segments": segments,
        "closure_reasons": [{"reason": r, "accounts": int(v)} for r, v in reasons.items() if v >= MIN_CELL],
        "closures_per_year": [{"year": int(y), "accounts": int(v)} for y, v in
                              closed["ACCT_CLOSE_DATE"].dt.year.value_counts().sort_index().items()],
    }


def marginals(profiles: pd.DataFrame, numeric: list[str], categorical: dict) -> dict:
    """Marginal distributions of the model features (used to generate FICTITIOUS profiles).

    Each feature is described on its own (deciles or frequencies). Drawing each feature
    independently yields plausible profiles that match no real customer.
    """
    out = {"numeric": {}, "categorical": {}}
    for col in numeric:
        s = profiles[col].dropna()
        is_integer = bool((s == s.round()).all())
        if is_integer and s.nunique() > 15 and s.quantile(0.99) <= 15:
            s = s.clip(upper=s.quantile(0.99))      # count variable: the tail (≥ 99th percentile) is grouped
        values = s.value_counts(normalize=True)
        if len(values) <= 15:      # discrete variable: frequencies
            out["numeric"][col] = {
                "type": "discrete", "missing_share": round(float(profiles[col].isna().mean()), 4),
                "values": [float(v) for v in values.index], "frequencies": [round(float(f), 5) for f in values.values]}
        else:                      # continuous variable: deciles
            out["numeric"][col] = {
                "type": "continuous", "missing_share": round(float(profiles[col].isna().mean()), 4),
                "deciles": [round(float(q), 2) for q in s.quantile(np.linspace(0, 1, 11))]}
    for col in categorical:
        f = profiles[col].value_counts(normalize=True)
        out["categorical"][col] = {str(c): round(float(v), 5) for c, v in f.items()}
    return out


def write(name: str, content: dict) -> Path:
    config.APP_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = config.APP_ARTIFACTS / name
    path.write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    return path
