"""Explanatory features of churn, at customer grain.

Only features **known before the closure** are built here. The columns that give the
target away (closing date and reason, balance, account family, currency, product,
amount...) are never read by this module: see the leakage check in
``04_machine_learning/notebooks/03_churn_ml.ipynb``.
"""

from __future__ import annotations

import sys

import pandas as pd

from . import config

# The encoding code lives in the application: training and inference share
# exactly the same function.
sys.path.insert(0, str(config.ROOT / "05_web_app"))
from utils import preprocessing  # noqa: E402

DAYS_PER_YEAR = 365.25
DAYS_PER_MONTH = 30.4375


def customer_features(customers: pd.DataFrame, ref_date: pd.Timestamp) -> pd.DataFrame:
    """Build each customer's profile (same fields as the application form)."""
    p = pd.DataFrame(index=customers.index)
    p["AGE"] = ref_date.year - (customers["BIRTH_PERIOD"] + 2)
    p["CUSTOMER_TENURE"] = (ref_date - customers["CUST_OPENING_DATE"]).dt.days / DAYS_PER_YEAR
    p["N_ACCOUNTS"] = customers["N_ACCOUNTS"]
    p["SALARY"] = customers["SALARY"]
    p["FILE_COMPLETE"] = (customers["COMPLETED_FILE"] == "YES").astype(int)
    p["MONTHS_SINCE_REVIEW"] = (ref_date - customers["LAST_REVIEW_DATE"]).dt.days / DAYS_PER_MONTH
    p["MONTHS_TO_NEXT_REVIEW"] = (customers["NEXT__REVIEW_DATE"] - ref_date).dt.days / DAYS_PER_MONTH
    p["MARITAL_STATUS"] = customers["MARITAL_STATUS"].fillna("NR")
    p["CUSTOMER_TYPE"] = customers["NATURE_CLIENT"]
    p["SEGMENT"] = customers["PARTYCLASS"]
    p["KYC_SCORE"] = customers["SCORE_KYC"].fillna("NR")
    p["RESIDENCE_ZONE"] = customers["RESIDENCE_REGION"]
    for c in ["AGE", "CUSTOMER_TENURE", "MONTHS_SINCE_REVIEW", "MONTHS_TO_NEXT_REVIEW", "SALARY"]:
        p[c] = p[c].astype(float).round(2)
    return preprocessing.normalise_categories(p)


def modelling_set(customers: pd.DataFrame, ref_date: pd.Timestamp):
    """Return (profiles, X, y, groups) for the customers holding at least one account."""
    scope = customers[customers["CHURN"].notna()].reset_index(drop=True)
    profiles = customer_features(scope, ref_date)
    X = preprocessing.encode(profiles)
    y = scope["CHURN"].astype(int).to_numpy()
    groups = scope["CUSTOMER_NO"].to_numpy()
    return profiles, X, y, groups


def feature_families() -> dict[str, list[str]]:
    """Business grouping of the features (used by the sensitivity analysis)."""
    return {
        "Demographics": ["AGE", "MARITAL_STATUS", "RESIDENCE_ZONE"],
        "Relationship": ["CUSTOMER_TENURE", "N_ACCOUNTS", "CUSTOMER_TYPE", "SEGMENT", "SALARY"],
        "Compliance": ["KYC_SCORE", "FILE_COMPLETE", "MONTHS_SINCE_REVIEW", "MONTHS_TO_NEXT_REVIEW"],
    }


def discarded_candidates(customers: pd.DataFrame) -> pd.DataFrame:
    """Candidate features that were not kept (industry, branch group), one-hot encoded.

    They are only used by the ablation study that justifies leaving them out.
    """
    scope = customers[customers["CHURN"].notna()].reset_index(drop=True)
    industry = scope["INDUSTRY"].where(
        scope["INDUSTRY"].isin(["Z", "G", "C", "M", "A", "F", "Q", "I", "S", "J", "H", "N"]), "OTHER")
    blocks = pd.concat([
        pd.get_dummies(industry, prefix="INDUSTRY", prefix_sep="="),
        pd.get_dummies(scope["BRANCH_GROUP"], prefix="BRANCH_GROUP", prefix_sep="="),
    ], axis=1)
    return blocks.astype("float32")


def columns_of(features: list[str]) -> list[str]:
    """Encoded columns that belong to a list of business features."""
    return [c for c in preprocessing.model_columns() if preprocessing.source_feature(c) in features]


__all__ = ["customer_features", "modelling_set", "feature_families", "discarded_candidates", "columns_of"]
