"""Variables explicatives du churn, au grain client.

Seules des variables **connues avant la clôture** sont construites ici.
Les colonnes qui trahissent la cible (date et motif de clôture, solde, famille
de compte, devise, produit, montant...) ne sont jamais lues par ce module :
voir le contrôle de fuite dans ``04_machine_learning/notebooks/03_churn_ml.ipynb``.
"""

from __future__ import annotations

import sys

import pandas as pd

from . import config

# Le code d'encodage vit dans l'application : entraînement et inférence partagent
# exactement la même fonction.
sys.path.insert(0, str(config.RACINE / "05_web_app"))
from utils import preprocessing  # noqa: E402

JOURS_PAR_AN = 365.25
JOURS_PAR_MOIS = 30.4375


def variables_client(clients: pd.DataFrame, date_ref: pd.Timestamp) -> pd.DataFrame:
    """Construit le profil de chaque client (mêmes champs que le formulaire de l'application)."""
    p = pd.DataFrame(index=clients.index)
    p["AGE"] = date_ref.year - (clients["BIRTH_PERIOD"] + 2)
    p["ANCIENNETE_CLIENT"] = (date_ref - clients["CUST_OPENING_DATE"]).dt.days / JOURS_PAR_AN
    p["NB_COMPTES"] = clients["NB_COMPTES"]
    p["SALAIRE"] = clients["SALARY"]
    p["DOSSIER_COMPLET"] = (clients["COMPLETED_FILE"] == "YES").astype(int)
    p["MOIS_DEPUIS_REVUE"] = (date_ref - clients["LAST_REVIEW_DATE"]).dt.days / JOURS_PAR_MOIS
    p["MOIS_AVANT_PROCHAINE_REVUE"] = (clients["NEXT__REVIEW_DATE"] - date_ref).dt.days / JOURS_PAR_MOIS
    p["STATUT_MARITAL"] = clients["MARITAL_STATUS"].fillna("NR")
    p["NATURE_CLIENT"] = clients["NATURE_CLIENT"]
    p["SEGMENT"] = clients["PARTYCLASS"]
    p["SCORE_KYC"] = clients["SCORE_KYC"].fillna("NR")
    p["ZONE_RESIDENCE"] = clients["RESIDENCE_REGION"].replace({"ASIE_OCEANIE": "AUTRE"})
    for c in ["AGE", "ANCIENNETE_CLIENT", "MOIS_DEPUIS_REVUE", "MOIS_AVANT_PROCHAINE_REVUE", "SALAIRE"]:
        p[c] = p[c].astype(float).round(2)
    return preprocessing.normaliser_modalites(p)


def jeu_modelisation(clients: pd.DataFrame, date_ref: pd.Timestamp):
    """Renvoie (profils, X, y, groupes) pour les clients ayant au moins un compte."""
    perimetre = clients[clients["CHURN"].notna()].reset_index(drop=True)
    profils = variables_client(perimetre, date_ref)
    X = preprocessing.encoder(profils)
    y = perimetre["CHURN"].astype(int).to_numpy()
    groupes = perimetre["CUSTOMER_NO"].to_numpy()
    return profils, X, y, groupes


def famille_variables() -> dict[str, list[str]]:
    """Regroupement métier des variables (pour l'analyse de sensibilité)."""
    return {
        "Démographie": ["AGE", "STATUT_MARITAL", "ZONE_RESIDENCE"],
        "Relation": ["ANCIENNETE_CLIENT", "NB_COMPTES", "NATURE_CLIENT", "SEGMENT", "SALAIRE"],
        "Conformité": ["SCORE_KYC", "DOSSIER_COMPLET", "MOIS_DEPUIS_REVUE",
                       "MOIS_AVANT_PROCHAINE_REVUE"],
    }


def candidats_ecartes(clients: pd.DataFrame) -> pd.DataFrame:
    """Variables candidates non retenues (secteur, groupe d'agences), encodées en one-hot.

    Elles ne servent qu'à l'étude d'ablation qui justifie de ne pas les garder.
    """
    perimetre = clients[clients["CHURN"].notna()].reset_index(drop=True)
    secteur = perimetre["INDUSTRY"].where(
        perimetre["INDUSTRY"].isin(["Z", "G", "C", "M", "A", "F", "Q", "I", "S", "J", "H", "N"]), "AUTRE")
    blocs = pd.concat([
        pd.get_dummies(secteur, prefix="SECTEUR", prefix_sep="="),
        pd.get_dummies(perimetre["BRANCH_GROUP"], prefix="GROUPE_AGENCES", prefix_sep="="),
    ], axis=1)
    return blocs.astype("float32")


def colonnes_de(variables: list[str]) -> list[str]:
    """Colonnes encodées correspondant à une liste de variables métier."""
    return [c for c in preprocessing.colonnes_modele()
            if preprocessing.variable_d_origine(c) in variables]


__all__ = ["variables_client", "jeu_modelisation", "famille_variables", "candidats_ecartes", "colonnes_de"]
