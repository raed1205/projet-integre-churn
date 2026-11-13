"""Prédiction du churn au grain client : découpage, modèles, évaluation, fuite de cible.

Principes :

* **un client = une ligne** ; le découpage se fait par client (``GroupShuffleSplit``),
  un client ne peut donc pas être à la fois dans l'entraînement et dans le test ;
* trois jeux : entraînement (70 %), validation (15 % — choix du seuil), test (15 % — jamais
  utilisé avant l'évaluation finale) ;
* on ne juge pas un modèle sur l'accuracy seule : precision, recall, F1, ROC-AUC, PR-AUC.
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

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE))
from vigie import config  # noqa: E402

GRAINE = config.GRAINE


# --------------------------------------------------------------------------
# Découpage
# --------------------------------------------------------------------------
def decouper(y: np.ndarray, groupes: np.ndarray) -> dict[str, np.ndarray]:
    """70 % entraînement / 15 % validation / 15 % test, **par client**."""
    indices = np.arange(len(y))
    reste, test = next(GroupShuffleSplit(1, test_size=0.15, random_state=GRAINE).split(indices, y, groupes))
    train, validation = next(GroupShuffleSplit(1, test_size=0.15 / 0.85, random_state=GRAINE)
                             .split(reste, y[reste], groupes[reste]))
    decoupage = {"train": reste[train], "validation": reste[validation], "test": test}
    # Garde-fou : aucun client commun entre deux jeux.
    ensembles = {k: set(groupes[v]) for k, v in decoupage.items()}
    assert not (ensembles["train"] & ensembles["test"])
    assert not (ensembles["train"] & ensembles["validation"])
    assert not (ensembles["validation"] & ensembles["test"])
    return decoupage


# --------------------------------------------------------------------------
# Modèles
# --------------------------------------------------------------------------
PARAMS_XGB_DEFAUT = dict(n_estimators=300, max_depth=6, learning_rate=0.08, subsample=0.8,
                         colsample_bytree=0.8, min_child_weight=5)


def xgboost(**params) -> XGBClassifier:
    reglages = {**PARAMS_XGB_DEFAUT, **params}
    return XGBClassifier(**reglages, tree_method="hist", eval_metric="logloss", n_jobs=4, random_state=GRAINE)


def modeles() -> dict:
    """Les modèles comparés, du plus simple au plus flexible."""
    imputation = lambda: SimpleImputer(strategy="median", add_indicator=True)  # noqa: E731
    return {
        "Référence (taux moyen)": DummyClassifier(strategy="prior"),
        "Régression logistique": make_pipeline(imputation(), StandardScaler(),
                                               LogisticRegression(max_iter=1000, random_state=GRAINE)),
        "Random Forest": make_pipeline(imputation(), RandomForestClassifier(
            n_estimators=300, min_samples_leaf=20, n_jobs=4, random_state=GRAINE)),
        "XGBoost": xgboost(),
    }


def optimiser_xgboost(X, y, groupes, n_iter: int = 12):
    """Recherche aléatoire d'hyperparamètres, validation croisée **par client** (3 plis)."""
    grille = {
        "n_estimators": [200, 300, 400, 600],
        "max_depth": [4, 5, 6, 7, 8],
        "learning_rate": [0.03, 0.05, 0.08, 0.12],
        "subsample": [0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.6, 0.8, 1.0],
        "min_child_weight": [1, 5, 10, 20],
        "reg_lambda": [1, 5, 10],
    }
    recherche = RandomizedSearchCV(
        XGBClassifier(tree_method="hist", eval_metric="logloss", n_jobs=4, random_state=GRAINE),
        grille, n_iter=n_iter, scoring="average_precision", cv=GroupKFold(n_splits=3),
        random_state=GRAINE, n_jobs=1, refit=False,
    )
    recherche.fit(X, y, groups=groupes)
    resultats = (pd.DataFrame(recherche.cv_results_)
                 .sort_values("rank_test_score")[["rank_test_score", "mean_test_score", "std_test_score", "params"]])
    return recherche.best_params_, resultats


# --------------------------------------------------------------------------
# Évaluation
# --------------------------------------------------------------------------
def seuil_f1(y, proba) -> float:
    """Seuil de décision qui maximise le F1 (à calculer sur la VALIDATION, jamais sur le test)."""
    precision, recall, seuils = precision_recall_curve(y, proba)
    f1 = 2 * precision[:-1] * recall[:-1] / np.clip(precision[:-1] + recall[:-1], 1e-12, None)
    return float(seuils[int(np.argmax(f1))])


def evaluer(y, proba, seuil: float = 0.5) -> dict:
    """Toutes les métriques demandées, pour un seuil de décision donné."""
    prediction = (np.asarray(proba) >= seuil).astype(int)
    vn, fp, fn, vp = confusion_matrix(y, prediction).ravel()
    return {
        "ROC-AUC": roc_auc_score(y, proba) if len(np.unique(proba)) > 1 else 0.5,
        "PR-AUC": average_precision_score(y, proba),
        "Precision": precision_score(y, prediction, zero_division=0),
        "Recall": recall_score(y, prediction),
        "F1": f1_score(y, prediction),
        "Accuracy": accuracy_score(y, prediction),
        "Brier": brier_score_loss(y, proba),
        "Seuil": seuil,
        "VP": int(vp), "FP": int(fp), "FN": int(fn), "VN": int(vn),
    }


def gains(y, proba, parts=(0.05, 0.10, 0.20, 0.30, 0.50)) -> pd.DataFrame:
    """Courbe de gains : en ciblant les x % de clients les mieux scorés, quelle part des départs capte-t-on ?"""
    ordre = np.argsort(-np.asarray(proba))
    y_trie = np.asarray(y)[ordre]
    total = y_trie.sum()
    lignes = []
    for part in parts:
        n = int(round(part * len(y_trie)))
        captes = y_trie[:n].sum()
        lignes.append({"Clients ciblés": part, "Départs captés": captes / total,
                       "Taux de churn dans la cible": captes / n, "Lift": (captes / n) / (total / len(y_trie))})
    return pd.DataFrame(lignes)


# --------------------------------------------------------------------------
# Contrôle de la fuite de cible
# --------------------------------------------------------------------------
def audit_fuite(table: pd.DataFrame, cible: str, colonnes: list[str]) -> pd.DataFrame:
    """Pour chaque colonne : le simple fait qu'elle soit vide permet-il de deviner la cible ?

    ``AUC du vide`` = AUC obtenue en prédisant la cible avec le seul indicateur « valeur manquante ».
    0,5 : le vide n'apprend rien. Proche de 1 : le vide trahit la cible.
    """
    y = table[cible].to_numpy()
    lignes = []
    for col in colonnes:
        vide = table[col].isna().to_numpy().astype(int)
        auc = roc_auc_score(y, vide) if 0 < vide.sum() < len(vide) else 0.5
        lignes.append({
            "Variable": col,
            "% vide si actif": round(100 * vide[y == 0].mean(), 1),
            "% vide si clos": round(100 * vide[y == 1].mean(), 1),
            "AUC du vide": round(max(auc, 1 - auc), 3),
        })
    audit = pd.DataFrame(lignes).set_index("Variable")
    audit["Verdict"] = np.select(
        [audit["AUC du vide"] >= 0.80, audit["AUC du vide"] >= 0.60],
        ["FUITE — exclue", "À surveiller"], default="Saine")
    return audit.sort_values("AUC du vide", ascending=False)
