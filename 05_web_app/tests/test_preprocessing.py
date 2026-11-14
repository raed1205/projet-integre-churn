"""Encoding a profile must be stable: it is the contract between training and the application."""

import numpy as np
import pandas as pd
import pytest

from utils import preprocessing


def test_model_columns_are_fixed():
    columns = preprocessing.model_columns()
    assert len(columns) == 31
    assert columns[:7] == preprocessing.NUMERIC
    assert len(set(columns)) == len(columns)


def test_encoding_a_profile():
    X = preprocessing.encode(pd.DataFrame([preprocessing.default_profile()]))
    assert list(X.columns) == preprocessing.model_columns()
    assert X.loc[0, "AGE"] == 40
    assert X.loc[0, "MARITAL_STATUS=M"] == 1 and X.loc[0, "MARITAL_STATUS=C"] == 0
    for feature in preprocessing.CATEGORICAL:          # exactly one active indicator per categorical feature
        assert X.filter(like=f"{feature}=").sum(axis=1).iloc[0] == 1


def test_missing_value_is_kept():
    X = preprocessing.encode(pd.DataFrame([preprocessing.default_profile()]))
    assert np.isnan(X.loc[0, "SALARY"])               # income not declared: stays missing


def test_unknown_category_goes_to_the_last_one():
    profile = preprocessing.default_profile() | {"CUSTOMER_TYPE": "TRPP", "MARITAL_STATUS": None}
    X = preprocessing.encode(pd.DataFrame([profile]))
    assert X.loc[0, "CUSTOMER_TYPE=OTHER"] == 1
    assert X.loc[0, "MARITAL_STATUS=NR"] == 1


def test_missing_feature_is_rejected():
    profile = preprocessing.default_profile()
    del profile["AGE"]
    with pytest.raises(ValueError, match="AGE"):
        preprocessing.encode(pd.DataFrame([profile]))


def test_every_feature_has_a_label():
    for feature in list(preprocessing.NUMERIC) + list(preprocessing.CATEGORICAL):
        assert feature in preprocessing.LABELS


def test_review_cycle_depends_on_the_kyc_score():
    assert preprocessing.months_to_next_review("LR", 12) == 36      # 48-month cycle
    assert preprocessing.months_to_next_review("MR", 12) == 24      # 36-month cycle
    assert preprocessing.months_to_next_review("H2", 30) == -6      # 24-month cycle: review overdue
    default = preprocessing.default_profile()
    assert default["MONTHS_TO_NEXT_REVIEW"] == preprocessing.months_to_next_review(
        default["KYC_SCORE"], default["MONTHS_SINCE_REVIEW"])
