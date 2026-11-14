"""From a customer profile to the model's feature vector.

This module is **the only place** where a profile is turned into features. It is used
for training (04_machine_learning) *and* by the application, so there can be no gap
between what the model learnt and what it is shown in production.

It depends only on pandas / numpy and reads no data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Numeric features: passed through as they are (a missing value stays NaN).
NUMERIC = [
    "AGE",                    # age in years (middle of the birth period)
    "CUSTOMER_TENURE",        # years since the relationship started
    "N_ACCOUNTS",             # number of accounts held
    "SALARY",                 # declared income (rounded), NaN when not declared
    "FILE_COMPLETE",          # 1 when the customer file is complete
    "MONTHS_SINCE_REVIEW",    # months elapsed since the last file review
    "MONTHS_TO_NEXT_REVIEW",  # months until the next review (negative = review overdue)
]

# Categorical features and their allowed categories (fixed order = fixed columns).
# Any value that is not in the list falls into the last category of that list.
CATEGORICAL = {
    "MARITAL_STATUS": ["C", "M", "D", "V", "NR"],
    "CUSTOMER_TYPE": ["PPH", "PM", "PRO", "OTHER"],
    "SEGMENT": ["Retail", "Premium", "Corporate Small", "Corporate"],
    "KYC_SCORE": ["LR", "MR", "H1", "H2", "H3", "NR"],
    "RESIDENCE_ZONE": ["LOCAL", "EUROPE", "AFRIQUE_MO", "AMERIQUES", "OTHER"],
}

LABELS = {
    "AGE": "Age",
    "CUSTOMER_TENURE": "Customer tenure (years)",
    "N_ACCOUNTS": "Number of accounts",
    "SALARY": "Declared income",
    "FILE_COMPLETE": "Complete file",
    "MONTHS_SINCE_REVIEW": "Months since last review",
    "MONTHS_TO_NEXT_REVIEW": "Months to next review",
    "MARITAL_STATUS": "Marital status",
    "CUSTOMER_TYPE": "Customer type",
    "SEGMENT": "Commercial segment",
    "KYC_SCORE": "KYC score",
    "RESIDENCE_ZONE": "Residence zone",
}

CATEGORY_LABELS = {
    "MARITAL_STATUS": {"C": "Single", "M": "Married", "D": "Divorced", "V": "Widowed", "NR": "Not provided"},
    "CUSTOMER_TYPE": {"PPH": "Individual", "PM": "Legal entity", "PRO": "Professional", "OTHER": "Other category"},
    "KYC_SCORE": {"LR": "LR — low risk", "MR": "MR — medium risk", "H1": "H1 — high risk (1)",
                  "H2": "H2 — high risk (2)", "H3": "H3 — high risk (3)", "NR": "Not provided"},
    "RESIDENCE_ZONE": {"LOCAL": "Local", "EUROPE": "Europe", "AFRIQUE_MO": "Africa / Middle East",
                       "AMERIQUES": "Americas", "OTHER": "Other zone"},
}

# Business rule found in the data: the length of the review cycle depends on the KYC score
# (97 to 99% of the customers of each score). The next review therefore follows from the last one.
REVIEW_CYCLE_MONTHS = {"LR": 48, "MR": 36, "H1": 24, "H2": 24, "H3": 24, "NR": 48}


def months_to_next_review(kyc_score: str, months_since_review: float) -> float:
    """Months left before the next review (negative = review overdue)."""
    return REVIEW_CYCLE_MONTHS.get(kyc_score, 48) - months_since_review


def model_columns() -> list[str]:
    """Ordered list of the columns the model expects."""
    cols = list(NUMERIC)
    for feature, categories in CATEGORICAL.items():
        cols += [f"{feature}={c}" for c in categories]
    return cols


def source_feature(column: str) -> str:
    """Business feature behind an encoded column (``SEGMENT=Retail`` -> ``SEGMENT``)."""
    return column.split("=", 1)[0]


def normalise_categories(profiles: pd.DataFrame) -> pd.DataFrame:
    """Put every categorical value into a known category."""
    out = profiles.copy()
    for feature, categories in CATEGORICAL.items():
        fallback = categories[-1]
        values = out[feature].astype("object").where(out[feature].notna(), None)
        out[feature] = [v if v in categories else fallback for v in values]
    return out


def encode(profiles: pd.DataFrame) -> pd.DataFrame:
    """Turn profiles (one row = one customer) into the model matrix.

    * numeric features: cast to ``float`` (NaN is kept; the model handles it);
    * categorical features: one-hot encoding over a fixed list of categories.
    """
    missing = [c for c in list(NUMERIC) + list(CATEGORICAL) if c not in profiles.columns]
    if missing:
        raise ValueError(f"Features missing from the profile: {missing}")
    p = normalise_categories(profiles)
    blocks = {c: pd.to_numeric(p[c], errors="coerce").astype("float32") for c in NUMERIC}
    for feature, categories in CATEGORICAL.items():
        for c in categories:
            blocks[f"{feature}={c}"] = (p[feature] == c).astype("float32")
    X = pd.DataFrame(blocks, index=profiles.index)
    return X[model_columns()]


def default_profile() -> dict:
    """Neutral fictitious profile used to pre-fill the form."""
    return {
        "AGE": 40, "CUSTOMER_TENURE": 8.0, "N_ACCOUNTS": 1, "SALARY": np.nan,
        "FILE_COMPLETE": 1, "MONTHS_SINCE_REVIEW": 12, "MONTHS_TO_NEXT_REVIEW": 36,
        "MARITAL_STATUS": "M", "CUSTOMER_TYPE": "PPH", "SEGMENT": "Retail", "KYC_SCORE": "LR",
        "RESIDENCE_ZONE": "LOCAL",
    }
