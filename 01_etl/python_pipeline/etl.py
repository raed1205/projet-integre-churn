"""ETL pipeline in Python (bonus) — same logic as the Talend jobs.

    python 01_etl/python_pipeline/etl.py

Steps:
    E  read the CSV and the 5 Excel files (data/ folder, never versioned)
    T  typing, de-duplication, account and customer grains, derived variables
    L  load PostgreSQL: staging, dimensions, then the fact table

The connection is configured through environment variables (no password in the code):
    PGHOST (localhost)  PGPORT (5432)  PGDATABASE (vigie_dwh)  PGUSER (postgres)  PGPASSWORD

This script is the **reference**: the Talend jobs must produce exactly the same volumes,
which is what the queries in 02_data_warehouse/checks/checks.sql verify.
"""

from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from vigie import data  # noqa: E402

SCHEMA_SQL = ROOT / "02_data_warehouse" / "schema" / "create_tables.sql"
NOT_PROVIDED = data.NOT_PROVIDED

MARITAL_STATUS = {"C": "Single", "M": "Married", "D": "Divorced", "V": "Widowed"}
# Account families, keyed by the label found in ACCOUNT_CATEGORY.xlsx.
ACCOUNT_FAMILY = {
    "Epargne": "Deposits", "Comptes courants": "Deposits", "Comptes en devises": "Deposits",
    "Exigibles": "Deposits", "Placements a terme": "Deposits", "Comptes indisponibles": "Deposits",
    "Credit immobilier": "Loans", "Credit consommation": "Loans", "Credit automobile": "Loans",
    "Credit investissement": "Loans", "Financement court terme": "Loans",
    "Autres comptes": "Other", "Coffres": "Other", "Contentieux": "Other",
}


def connect():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "vigie_dwh"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
    )


def bulk_load(cur, table: str, df: pd.DataFrame) -> None:
    """Bulk load (COPY): fast, and equivalent to a tDBOutput in bulk mode."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep="\\N", sep="\t")
    buffer.seek(0)
    columns = ", ".join(df.columns)
    cur.copy_expert(f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buffer)
    print(f"   {table:<32} {len(df):>9,} rows")


def date_key(series: pd.Series) -> pd.Series:
    """Date -> YYYYMMDD key; missing date -> 0 (the "unknown" member)."""
    return series.dt.strftime("%Y%m%d").fillna("0").astype(int)


def dimension(codes: pd.Series, code_name: str, id_name: str, labels: dict | None = None,
              unknown_label: str = NOT_PROVIDED, unknown_code: str = "ND") -> pd.DataFrame:
    """Simple dimension: key 0 = not provided, then one key per sorted code."""
    values = sorted(codes.dropna().unique())
    dim = pd.DataFrame({id_name: range(1, len(values) + 1), code_name: values})
    dim["label"] = [labels.get(v, v) if labels else v for v in values]
    unknown = pd.DataFrame({id_name: [0], code_name: [unknown_code], "label": [unknown_label]})
    return pd.concat([unknown, dim], ignore_index=True)


def transform(df: pd.DataFrame, refs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Build every table of the star schema."""
    accounts = data.account_grain(df)
    customers = data.customer_grain(df, accounts)
    ref_date = data.reference_date(df)
    lab = {name: dict(zip(ref.iloc[:, 0], ref.iloc[:, 1])) for name, ref in refs.items()}

    # ---------------- reference dimensions ----------------
    dim_branch = dimension(customers["BRANCH_GROUP"], "group_code", "branch_id",
                           {c: f"Branch group {c[2:]}" for c in customers["BRANCH_GROUP"].unique()})
    dim_branch.loc[dim_branch["group_code"] == "AG00", "label"] = "Masked branches"
    dim_branch["is_masked"] = dim_branch["group_code"].isin(["AG00", "ND"])

    dim_industry = dimension(refs["INDUSTRY"]["INDUSTRY_CODE"], "industry_code", "industry_id", lab["INDUSTRY"])
    dim_currency = dimension(refs["CURRENCY"]["CURRENCY_CODE"], "currency_code", "currency_id", lab["CURRENCY"])
    dim_reason = dimension(refs["CLOSURE_REASON"]["REASON_ID"], "reason_code", "reason_id", lab["CLOSURE_REASON"],
                           unknown_label="No reason (active account or not entered)")
    dim_category = dimension(refs["ACCOUNT_CATEGORY"]["CATEGORY_ID"], "category_code", "category_id",
                             lab["ACCOUNT_CATEGORY"])
    dim_category["family"] = dim_category["label"].map(ACCOUNT_FAMILY).fillna(NOT_PROVIDED)

    products = (accounts[["PRODUCT_GROUP", "PRODUCT_LINE"]].dropna().drop_duplicates()
                .sort_values(["PRODUCT_LINE", "PRODUCT_GROUP"]).reset_index(drop=True))
    dim_product = pd.concat([
        pd.DataFrame({"product_id": [0], "product_group": [NOT_PROVIDED], "product_line": [NOT_PROVIDED]}),
        pd.DataFrame({"product_id": range(1, len(products) + 1),
                      "product_group": products["PRODUCT_GROUP"], "product_line": products["PRODUCT_LINE"]}),
    ], ignore_index=True)

    # ---------------- customer dimension ----------------
    c = customers.sort_values("CUSTOMER_NO").reset_index(drop=True)
    tenure = (ref_date - c["CUST_OPENING_DATE"]).dt.days / 365.25
    months_review = (ref_date - c["LAST_REVIEW_DATE"]).dt.days / 30.4375
    dim_customer = pd.DataFrame({
        "customer_id": range(1, len(c) + 1),
        "customer_code": c["CUSTOMER_NO"],
        "nationality_zone": c["NATIONALITY_REGION"],
        "residence_zone": c["RESIDENCE_REGION"],
        "marital_status": c["MARITAL_STATUS"].map(MARITAL_STATUS).fillna(NOT_PROVIDED),
        "birth_period": c["BIRTH_PERIOD"].astype("Int64"),
        "age": (ref_date.year - (c["BIRTH_PERIOD"] + 2)).astype("Int64"),
        "age_band": data.age_band(c["BIRTH_PERIOD"], ref_date.year),
        "customer_type": c["NATURE_CLIENT"],
        "segment": c["PARTYCLASS"],
        "line_of_business": c["LOB"].map(lab["TARGET"]).fillna(NOT_PROVIDED),
        "relationship_start_date": c["CUST_OPENING_DATE"].dt.date,
        "tenure_years": tenure.round(2),
        "tenure_band": data.tenure_band(tenure),
        "declared_income": c["SALARY"],
        "n_accounts": c["N_ACCOUNTS"],
        "kyc_score": c["SCORE_KYC"].fillna(NOT_PROVIDED),
        "file_complete": c["COMPLETED_FILE"] == "YES",
        "last_review_date": c["LAST_REVIEW_DATE"].dt.date,
        "next_review_date": c["NEXT__REVIEW_DATE"].dt.date,
        "months_since_review": months_review.round(1),
        "review_overdue": (c["NEXT__REVIEW_DATE"] < ref_date).where(c["NEXT__REVIEW_DATE"].notna()),
        "is_churned": c["CHURN"],
    })

    # ---------------- fact table ----------------
    k = accounts.sort_values("ACCOUNT_NO").reset_index(drop=True)
    k = k.merge(c[["CUSTOMER_NO", "BRANCH_GROUP", "INDUSTRY"]].assign(customer_id=dim_customer["customer_id"]),
                on="CUSTOMER_NO", how="left", suffixes=("", "_CUSTOMER"))

    def key(values: pd.Series, dim: pd.DataFrame, code: str, ident: str) -> pd.Series:
        return values.map(dict(zip(dim[code], dim[ident]))).fillna(0).astype(int)

    product_key = k[["PRODUCT_GROUP", "PRODUCT_LINE"]].merge(
        dim_product, left_on=["PRODUCT_GROUP", "PRODUCT_LINE"],
        right_on=["product_group", "product_line"], how="left")["product_id"].fillna(0).astype(int)
    end = k["ACCT_CLOSE_DATE"].fillna(ref_date)
    account_age = (end - k["ACCT_OPENING_DATE"]).dt.days
    # Source anomaly: for some closed accounts the opening is later than the closing.
    # The date is not corrected; the account is flagged and its age is not computed.
    inconsistent = account_age < 0
    fact = pd.DataFrame({
        "account_id": range(1, len(k) + 1),
        "account_code": k["ACCOUNT_NO"],
        "customer_id": k["customer_id"],
        "branch_id": key(k["BRANCH_GROUP"], dim_branch, "group_code", "branch_id"),
        "industry_id": key(k["INDUSTRY"], dim_industry, "industry_code", "industry_id"),
        "category_id": key(k["ACCOUNT_CATEGORY"], dim_category, "category_code", "category_id"),
        "currency_id": key(k["CURRENCY"], dim_currency, "currency_code", "currency_id"),
        "reason_id": key(k["CLOSURE_REASON"], dim_reason, "reason_code", "reason_id"),
        "product_id": product_key.to_numpy(),
        "opening_date_id": date_key(k["ACCT_OPENING_DATE"]),
        "closing_date_id": date_key(k["ACCT_CLOSE_DATE"]),
        "is_closed": k["CHURN"],
        "balance": k["ACCT_BALANCE"],
        "is_overdrawn": (k["ACCT_BALANCE"] < 0).where(k["ACCT_BALANCE"].notna()),
        "product_amount": k["AMOUNT"],
        "fixed_rate": k["FIXEDRATE"],
        "account_age_days": account_age.where(~inconsistent).astype("Int64"),
        "opened_after_closing": inconsistent.to_numpy(),
        "product_status": k["PRODUCT_STATUS"],
        "n_source_rows": k["N_SOURCE_ROWS"],
    })
    return {
        "dwh.dim_branch": dim_branch, "dwh.dim_industry": dim_industry, "dwh.dim_currency": dim_currency,
        "dwh.dim_closure_reason": dim_reason, "dwh.dim_account_category": dim_category,
        "dwh.dim_product": dim_product, "dwh.dim_customer": dim_customer, "dwh.fact_account": fact,
    }


def main() -> None:
    t0 = time.time()
    print("E — Extract")
    raw = data.load_raw()
    refs = data.load_references()
    print(f"   data_churn.csv: {len(raw):,} rows, {raw.shape[1]} columns")

    print("T — Transform")
    tables = transform(data.cast_types(raw), refs)

    print("L — Load PostgreSQL")
    with connect() as cnx, cnx.cursor() as cur:
        cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        staging = raw.rename(columns=str.lower)
        # Tabs and backslashes do not occur in the source; make sure before COPY.
        assert not staging.apply(lambda s: s.str.contains(r"[\t\\]", na=False)).any().any()
        bulk_load(cur, "staging.stg_churn", staging)
        for name, ref in refs.items():
            bulk_load(cur, f"staging.stg_{name.lower()}", ref.rename(columns=str.lower))
        for table, frame in tables.items():          # dimensions first, facts last
            bulk_load(cur, table, frame)
        cur.execute("ANALYZE")
    print(f"Done in {time.time() - t0:.0f} s.")


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
