"""Loading and inference of the churn model.

The model is an XGBoost stored as JSON (trees only). Inference produces:

* a **score**: probability that the customer leaves;
* a **risk level**: low, moderate or high;
* an **explanation**: the contribution of each feature to the score (exact SHAP values,
  computed by XGBoost itself).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import xgboost as xgb

from . import preprocessing
from .artifacts import ArtifactStore

LEVELS = [  # (upper bound excluded, label, colour)
    (0.25, "Low", "#2A9D8F"),
    (0.50, "Moderate", "#F4A261"),
    (1.01, "High", "#D62839"),
]


def risk_level(score: float) -> tuple[str, str]:
    """Turn a score into a risk level and a colour."""
    for bound, label, colour in LEVELS:
        if score < bound:
            return label, colour
    return LEVELS[-1][1], LEVELS[-1][2]


@dataclass
class Prediction:
    """Result of a scoring request for one profile."""
    score: float                       # probability of leaving, between 0 and 1
    level: str                         # Low / Moderate / High
    colour: str
    above_threshold: bool              # score ≥ the model's alert threshold
    observed_rate: float | None        # actual departure rate of test customers with a similar score
    contributions: pd.Series = field(repr=False, default=None)   # effect of each feature (log-odds)

    def drivers(self, k: int = 6) -> pd.DataFrame:
        """The ``k`` features that weigh the most, with the direction of their effect."""
        c = self.contributions.reindex(self.contributions.abs().sort_values(ascending=False).index).head(k)
        return pd.DataFrame({
            "feature": c.index,
            "label": [preprocessing.LABELS[v] for v in c.index],
            "effect": c.values,
            "direction": np.where(c.values > 0, "raises the risk", "lowers the risk"),
        })


class ChurnModel:
    """Ready-to-use churn model: encodes a profile, scores it and explains the score."""

    def __init__(self, store: ArtifactStore | None = None):
        self.store = store or ArtifactStore()
        self.meta = self.store.model_meta()
        self.columns = self.meta["columns"]
        self.alert_threshold = float(self.meta["alert_threshold"])
        self._booster = xgb.Booster()
        self._booster.load_model(str(self.store.model_path))
        if self.columns != preprocessing.model_columns():
            raise ValueError("The model columns do not match those of the encoder.")

    def _matrix(self, profiles: pd.DataFrame) -> xgb.DMatrix:
        X = preprocessing.encode(profiles)
        return xgb.DMatrix(X.to_numpy(dtype="float32"), feature_names=self.columns, missing=np.nan)

    def scores(self, profiles: pd.DataFrame) -> np.ndarray:
        """Probability of leaving for each profile (one row = one profile)."""
        return self._booster.predict(self._matrix(profiles))

    def contributions(self, profiles: pd.DataFrame) -> pd.DataFrame:
        """Contribution of each business feature (indicator columns of a feature are added up)."""
        raw = self._booster.predict(self._matrix(profiles), pred_contribs=True)[:, :-1]
        per_column = pd.DataFrame(raw, columns=self.columns, index=profiles.index)
        feats = [preprocessing.source_feature(c) for c in self.columns]
        return per_column.T.groupby(feats, sort=False).sum().T

    def observed_rate(self, score: float) -> float | None:
        """Departure rate actually observed on the test set for scores in the same band."""
        for band in self.meta["score_to_observed_rate"]:
            if band["from"] <= score <= band["to"]:
                return float(band["observed_rate"])
        return None

    def predict(self, profile: dict) -> Prediction:
        """Score, risk level and explanation for **one** profile."""
        table = pd.DataFrame([profile])
        score = float(self.scores(table)[0])
        level, colour = risk_level(score)
        return Prediction(
            score=score, level=level, colour=colour,
            above_threshold=score >= self.alert_threshold,
            observed_rate=self.observed_rate(score),
            contributions=self.contributions(table).iloc[0],
        )


class FictitiousGenerator:
    """Builds **fictitious** profiles from the published marginal distributions.

    Each feature is drawn independently of the others: the profiles are plausible feature by
    feature but match no real customer. Only the next review is derived from the other features
    (review-cycle rule), so that the profile stays consistent.
    """

    def __init__(self, marginals: dict, seed: int = 42):
        self.marginals = marginals
        self.rng = np.random.default_rng(seed)

    def _numeric(self, spec: dict, n: int) -> np.ndarray:
        if spec["type"] == "discrete":
            f = np.asarray(spec["frequencies"], dtype=float)
            values = self.rng.choice(spec["values"], size=n, p=f / f.sum())
        else:   # uniform draw inside a randomly chosen decile
            d = np.asarray(spec["deciles"], dtype=float)
            k = self.rng.integers(0, len(d) - 1, size=n)
            values = d[k] + self.rng.random(n) * (d[k + 1] - d[k])
        values = np.asarray(values, dtype=float)
        values[self.rng.random(n) < spec["missing_share"]] = np.nan
        return values

    def generate(self, n: int = 200) -> pd.DataFrame:
        profiles = {}
        for name, spec in self.marginals["numeric"].items():
            profiles[name] = self._numeric(spec, n)
        for name, freqs in self.marginals["categorical"].items():
            f = np.asarray(list(freqs.values()), dtype=float)
            profiles[name] = self.rng.choice(list(freqs.keys()), size=n, p=f / f.sum())
        table = pd.DataFrame(profiles)
        table["MONTHS_TO_NEXT_REVIEW"] = [
            preprocessing.months_to_next_review(k, m)
            for k, m in zip(table["KYC_SCORE"], table["MONTHS_SINCE_REVIEW"])]
        for col in ("AGE", "N_ACCOUNTS", "FILE_COMPLETE"):
            table[col] = table[col].round()
        table.index = [f"Fictitious profile {i + 1:03d}" for i in range(n)]
        return table
