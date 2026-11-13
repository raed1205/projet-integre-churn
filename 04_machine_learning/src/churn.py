"""Churn prediction at customer grain: split, models, evaluation, target leakage.

Principles:

* **one customer = one row**; the split is made per customer (``GroupShuffleSplit``), so a
  customer can never be in both the training and the test set;
* three sets: training (70%), validation (15% — choice of the threshold), test (15% — never
  used before the final evaluation);
* a model is not judged on accuracy alone: precision, recall, F1, ROC-AUC, PR-AUC.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
                             confusion_matrix, f1_score, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, RandomizedSearchCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from vigie import config  # noqa: E402

SEED = config.SEED


# --------------------------------------------------------------------------
# Split
# --------------------------------------------------------------------------
def split(y: np.ndarray, groups: np.ndarray) -> dict[str, np.ndarray]:
    """70% training / 15% validation / 15% test, **per customer**."""
    indices = np.arange(len(y))
    rest, test = next(GroupShuffleSplit(1, test_size=0.15, random_state=SEED).split(indices, y, groups))
    train, validation = next(GroupShuffleSplit(1, test_size=0.15 / 0.85, random_state=SEED)
                             .split(rest, y[rest], groups[rest]))
    parts = {"train": rest[train], "validation": rest[validation], "test": test}
    # Safety net: no customer shared between two sets.
    sets = {k: set(groups[v]) for k, v in parts.items()}
    assert not (sets["train"] & sets["test"])
    assert not (sets["train"] & sets["validation"])
    assert not (sets["validation"] & sets["test"])
    return parts


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
DEFAULT_XGB_PARAMS = dict(n_estimators=300, max_depth=6, learning_rate=0.08, subsample=0.8,
                          colsample_bytree=0.8, min_child_weight=5)


def xgboost(**params) -> XGBClassifier:
    settings = {**DEFAULT_XGB_PARAMS, **params}
    return XGBClassifier(**settings, tree_method="hist", eval_metric="logloss", n_jobs=4, random_state=SEED)


def models() -> dict:
    """The models compared, from the simplest to the most flexible."""
    imputer = lambda: SimpleImputer(strategy="median", add_indicator=True)  # noqa: E731
    return {
        "Baseline (average rate)": DummyClassifier(strategy="prior"),
        "Logistic regression": make_pipeline(imputer(), StandardScaler(),
                                             LogisticRegression(max_iter=1000, random_state=SEED)),
        "Random Forest": make_pipeline(imputer(), RandomForestClassifier(
            n_estimators=300, min_samples_leaf=20, n_jobs=4, random_state=SEED)),
        "XGBoost": xgboost(),
    }


def tune_xgboost(X, y, groups, n_iter: int = 12):
    """Random search of hyperparameters, cross-validation **per customer** (3 folds)."""
    grid = {
        "n_estimators": [200, 300, 400, 600],
        "max_depth": [4, 5, 6, 7, 8],
        "learning_rate": [0.03, 0.05, 0.08, 0.12],
        "subsample": [0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.6, 0.8, 1.0],
        "min_child_weight": [1, 5, 10, 20],
        "reg_lambda": [1, 5, 10],
    }
    search = RandomizedSearchCV(
        XGBClassifier(tree_method="hist", eval_metric="logloss", n_jobs=4, random_state=SEED),
        grid, n_iter=n_iter, scoring="average_precision", cv=GroupKFold(n_splits=3),
        random_state=SEED, n_jobs=1, refit=False,
    )
    search.fit(X, y, groups=groups)
    results = (pd.DataFrame(search.cv_results_)
               .sort_values("rank_test_score")[["rank_test_score", "mean_test_score", "std_test_score", "params"]])
    return search.best_params_, results


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------
def f1_threshold(y, proba) -> float:
    """Decision threshold that maximises F1 (to be computed on VALIDATION, never on the test set)."""
    precision, recall, thresholds = precision_recall_curve(y, proba)
    f1 = 2 * precision[:-1] * recall[:-1] / np.clip(precision[:-1] + recall[:-1], 1e-12, None)
    return float(thresholds[int(np.argmax(f1))])


def evaluate(y, proba, threshold: float = 0.5) -> dict:
    """All the requested metrics, for a given decision threshold."""
    prediction = (np.asarray(proba) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, prediction).ravel()
    return {
        "ROC-AUC": roc_auc_score(y, proba) if len(np.unique(proba)) > 1 else 0.5,
        "PR-AUC": average_precision_score(y, proba),
        "Precision": precision_score(y, prediction, zero_division=0),
        "Recall": recall_score(y, prediction),
        "F1": f1_score(y, prediction),
        "Accuracy": accuracy_score(y, prediction),
        "Brier": brier_score_loss(y, proba),
        "Threshold": threshold,
        "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn),
    }


def gains(y, proba, shares=(0.05, 0.10, 0.20, 0.30, 0.50)) -> pd.DataFrame:
    """Gains curve: by targeting the x% best-scored customers, what share of the departures is captured?"""
    order = np.argsort(-np.asarray(proba))
    y_sorted = np.asarray(y)[order]
    total = y_sorted.sum()
    rows = []
    for share in shares:
        k = int(round(share * len(y_sorted)))
        captured = y_sorted[:k].sum()
        rows.append({"Customers targeted": share, "Departures captured": captured / total,
                     "Churn rate in the target": captured / k, "Lift": (captured / k) / (total / len(y_sorted))})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Target leakage check
# --------------------------------------------------------------------------
def leakage_audit(table: pd.DataFrame, target: str, columns: list[str]) -> pd.DataFrame:
    """For each column: is the mere fact that it is blank enough to guess the target?

    ``Blank AUC`` = AUC obtained by predicting the target with the single "value is missing" flag.
    0.5: the blank teaches nothing. Close to 1: the blank gives the target away.
    """
    y = table[target].to_numpy()
    rows = []
    for col in columns:
        blank = table[col].isna().to_numpy().astype(int)
        auc = roc_auc_score(y, blank) if 0 < blank.sum() < len(blank) else 0.5
        rows.append({
            "Variable": col,
            "% blank if active": round(100 * blank[y == 0].mean(), 1),
            "% blank if closed": round(100 * blank[y == 1].mean(), 1),
            "Blank AUC": round(max(auc, 1 - auc), 3),
        })
    audit = pd.DataFrame(rows).set_index("Variable")
    audit["Verdict"] = np.select(
        [audit["Blank AUC"] >= 0.80, audit["Blank AUC"] >= 0.60],
        ["LEAK — excluded", "To watch"], default="Sound")
    return audit.sort_values("Blank AUC", ascending=False)
