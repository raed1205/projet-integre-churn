"""The model loads, returns consistent probabilities and explains itself."""

import numpy as np
import pandas as pd
import pytest

from utils import preprocessing
from utils.model import ChurnModel, FictitiousGenerator, risk_level


@pytest.fixture(scope="module")
def model() -> ChurnModel:
    return ChurnModel()


def test_score_is_a_probability(model):
    p = model.predict(preprocessing.default_profile())
    assert 0.0 <= p.score <= 1.0
    assert p.level in {"Low", "Moderate", "High"}


def test_explanation_matches_the_score(model):
    """Base value + sum of contributions = score (in log-odds): the explanation is exact."""
    p = model.predict(preprocessing.default_profile())
    logit = model.meta["shap_base_value"] + p.contributions.sum()
    assert 1 / (1 + np.exp(-logit)) == pytest.approx(p.score, abs=1e-3)
    assert set(p.contributions.index) == set(preprocessing.LABELS)


def test_overdue_review_raises_the_risk(model):
    base = preprocessing.default_profile()
    up_to_date = model.predict(base | {"MONTHS_SINCE_REVIEW": 6, "MONTHS_TO_NEXT_REVIEW": 42}).score
    overdue = model.predict(base | {"MONTHS_SINCE_REVIEW": 84, "MONTHS_TO_NEXT_REVIEW": -36}).score
    assert overdue > up_to_date + 0.10


def test_holding_several_accounts_lowers_the_risk_on_average(model):
    """The effect of the number of accounts depends on the profile: checked on average over a fictitious portfolio."""
    profiles = FictitiousGenerator(model.meta["marginals"], seed=1).generate(2000)
    assert model.scores(profiles.assign(N_ACCOUNTS=3)).mean() < model.scores(profiles.assign(N_ACCOUNTS=1)).mean()


def test_risk_levels():
    assert risk_level(0.10)[0] == "Low"
    assert risk_level(0.30)[0] == "Moderate"
    assert risk_level(0.75)[0] == "High"


def test_observed_rate_grows_with_the_score(model):
    rates = [band["observed_rate"] for band in model.meta["score_to_observed_rate"]]
    assert rates == sorted(rates)        # a higher score means more actual departures


def test_fictitious_portfolio(model):
    profiles = FictitiousGenerator(model.meta["marginals"], seed=1).generate(200)
    assert len(profiles) == 200
    assert all(i.startswith("Fictitious profile") for i in profiles.index)
    scores = model.scores(profiles)
    assert ((scores >= 0) & (scores <= 1)).all()
    assert 0.20 < scores.mean() < 0.55
    cycle = profiles["KYC_SCORE"].map(preprocessing.REVIEW_CYCLE_MONTHS)
    assert ((profiles["MONTHS_SINCE_REVIEW"] + profiles["MONTHS_TO_NEXT_REVIEW"] - cycle).abs() < 1e-6).all()
    pd.testing.assert_frame_equal(profiles, FictitiousGenerator(model.meta["marginals"], seed=1).generate(200))
