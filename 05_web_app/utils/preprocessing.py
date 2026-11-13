"""Du profil client au vecteur de variables du modèle.

Ce module est **le seul endroit** où un profil est transformé en variables.
Il est utilisé à l'entraînement (04_machine_learning) *et* par l'application :
il ne peut donc pas y avoir d'écart entre ce que le modèle a appris et ce
qu'on lui présente en production.

Il ne dépend que de pandas / numpy et ne lit aucune donnée.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Variables numériques : laissées telles quelles (une valeur manquante reste NaN).
NUMERIQUES = [
    "AGE",                         # âge en années (milieu de la tranche de naissance)
    "ANCIENNETE_CLIENT",           # années depuis l'entrée en relation
    "NB_COMPTES",                  # nombre de comptes détenus
    "SALAIRE",                     # revenu déclaré (arrondi), NaN si non déclaré
    "DOSSIER_COMPLET",             # 1 si le dossier client est complet
    "MOIS_DEPUIS_REVUE",           # mois écoulés depuis la dernière revue du dossier
    "MOIS_AVANT_PROCHAINE_REVUE",  # mois avant la prochaine revue (négatif = revue en retard)
]

# Variables catégorielles et leurs modalités autorisées (ordre figé = colonnes figées).
# Toute modalité absente de la liste est rangée dans la dernière de sa liste.
# SEGMENT et les codes KYC n'ont pas de modalité "autre" : une valeur inconnue y est
# donc rangée, par convention, dans la dernière modalité listée.
CATEGORIELLES = {
    "STATUT_MARITAL": ["C", "M", "D", "V", "NR"],
    "NATURE_CLIENT": ["PPH", "PM", "PRO", "AUTRE"],
    "SEGMENT": ["Retail", "Premium", "Corporate Small", "Corporate"],
    "SCORE_KYC": ["LR", "MR", "H1", "H2", "H3", "NR"],
    "ZONE_RESIDENCE": ["LOCAL", "EUROPE", "AFRIQUE_MO", "AMERIQUES", "AUTRE"],
}

LIBELLES = {
    "AGE": "Âge",
    "ANCIENNETE_CLIENT": "Ancienneté client (années)",
    "NB_COMPTES": "Nombre de comptes",
    "SALAIRE": "Revenu déclaré",
    "DOSSIER_COMPLET": "Dossier complet",
    "MOIS_DEPUIS_REVUE": "Mois depuis la dernière revue",
    "MOIS_AVANT_PROCHAINE_REVUE": "Mois avant la prochaine revue",
    "STATUT_MARITAL": "Statut marital",
    "NATURE_CLIENT": "Nature du client",
    "SEGMENT": "Segment commercial",
    "SCORE_KYC": "Score KYC",
    "ZONE_RESIDENCE": "Zone de résidence",
}

LIBELLES_MODALITES = {
    "STATUT_MARITAL": {"C": "Célibataire", "M": "Marié(e)", "D": "Divorcé(e)", "V": "Veuf / veuve",
                       "NR": "Non renseigné"},
    "NATURE_CLIENT": {"PPH": "Personne physique", "PM": "Personne morale", "PRO": "Professionnel",
                      "AUTRE": "Autre catégorie"},
    "SCORE_KYC": {"LR": "LR — risque faible", "MR": "MR — risque moyen", "H1": "H1 — risque élevé (1)",
                  "H2": "H2 — risque élevé (2)", "H3": "H3 — risque élevé (3)", "NR": "Non renseigné"},
    "ZONE_RESIDENCE": {"LOCAL": "Locale", "EUROPE": "Europe", "AFRIQUE_MO": "Afrique / Moyen-Orient",
                       "AMERIQUES": "Amériques", "AUTRE": "Autre zone"},
}


# Règle métier constatée dans les données : la durée du cycle de revue dépend du score KYC
# (98 à 99 % des clients de chaque score). La prochaine revue se déduit donc de la dernière.
CYCLE_REVUE_MOIS = {"LR": 48, "MR": 36, "H1": 24, "H2": 24, "H3": 24, "NR": 48}


def mois_avant_prochaine_revue(score_kyc: str, mois_depuis_revue: float) -> float:
    """Mois restants avant la prochaine revue (négatif = revue en retard)."""
    return CYCLE_REVUE_MOIS.get(score_kyc, 48) - mois_depuis_revue


def colonnes_modele() -> list[str]:
    """Liste ordonnée des colonnes attendues par le modèle."""
    cols = list(NUMERIQUES)
    for variable, modalites in CATEGORIELLES.items():
        cols += [f"{variable}={m}" for m in modalites]
    return cols


def variable_d_origine(colonne: str) -> str:
    """Retrouve la variable métier derrière une colonne encodée (``SEGMENT=Retail`` -> ``SEGMENT``)."""
    return colonne.split("=", 1)[0]


def normaliser_modalites(profils: pd.DataFrame) -> pd.DataFrame:
    """Range chaque valeur catégorielle dans une modalité connue."""
    out = profils.copy()
    for variable, modalites in CATEGORIELLES.items():
        defaut = modalites[-1]
        valeurs = out[variable].astype("object").where(out[variable].notna(), None)
        out[variable] = [v if v in modalites else defaut for v in valeurs]
    return out


def encoder(profils: pd.DataFrame) -> pd.DataFrame:
    """Transforme des profils (une ligne = un client) en matrice du modèle.

    * numériques : converties en ``float`` (NaN conservé, géré par le modèle) ;
    * catégorielles : encodage « one-hot » sur une liste figée de modalités.
    """
    manquantes = [c for c in list(NUMERIQUES) + list(CATEGORIELLES) if c not in profils.columns]
    if manquantes:
        raise ValueError(f"Variables absentes du profil : {manquantes}")
    p = normaliser_modalites(profils)
    blocs = {c: pd.to_numeric(p[c], errors="coerce").astype("float32") for c in NUMERIQUES}
    for variable, modalites in CATEGORIELLES.items():
        for m in modalites:
            blocs[f"{variable}={m}"] = (p[variable] == m).astype("float32")
    X = pd.DataFrame(blocs, index=profils.index)
    return X[colonnes_modele()]


def profil_par_defaut() -> dict:
    """Profil fictif neutre, utilisé pour pré-remplir le formulaire."""
    return {
        "AGE": 40, "ANCIENNETE_CLIENT": 8.0, "NB_COMPTES": 1, "SALAIRE": np.nan,
        "DOSSIER_COMPLET": 1, "MOIS_DEPUIS_REVUE": 12, "MOIS_AVANT_PROCHAINE_REVUE": 36,
        "STATUT_MARITAL": "M", "NATURE_CLIENT": "PPH", "SEGMENT": "Retail", "SCORE_KYC": "LR",
        "ZONE_RESIDENCE": "LOCAL",
    }
