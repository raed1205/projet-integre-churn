"""Chargement et inférence du modèle de churn.

Le modèle est un XGBoost stocké en JSON (arbres uniquement). L'inférence produit :

* un **score** : probabilité que le client parte ;
* un **niveau de risque** : faible, modéré ou élevé ;
* une **explication** : la contribution de chaque variable au score (valeurs SHAP exactes,
  calculées par XGBoost lui-même).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import xgboost as xgb

from . import preprocessing
from .artefacts import DepotArtefacts

NIVEAUX = [  # (borne haute exclue, libellé, couleur)
    (0.25, "Faible", "#2A9D8F"),
    (0.50, "Modéré", "#F4A261"),
    (1.01, "Élevé", "#D62839"),
]


def niveau_de_risque(score: float) -> tuple[str, str]:
    """Traduit un score en niveau de risque et en couleur."""
    for borne, libelle, couleur in NIVEAUX:
        if score < borne:
            return libelle, couleur
    return NIVEAUX[-1][1], NIVEAUX[-1][2]


@dataclass
class Prediction:
    """Résultat d'une demande de score pour un profil."""
    score: float                         # probabilité de départ, entre 0 et 1
    niveau: str                          # Faible / Modéré / Élevé
    couleur: str
    au_dessus_du_seuil: bool             # score ≥ seuil d'alerte du modèle
    taux_observe: float | None           # taux de départ réel des clients de test au score comparable
    contributions: pd.Series = field(repr=False, default=None)   # effet de chaque variable (log-odds)

    def facteurs(self, n: int = 6) -> pd.DataFrame:
        """Les ``n`` variables qui pèsent le plus, avec le sens de leur effet."""
        c = self.contributions.reindex(self.contributions.abs().sort_values(ascending=False).index).head(n)
        return pd.DataFrame({
            "variable": c.index,
            "libelle": [preprocessing.LIBELLES[v] for v in c.index],
            "effet": c.values,
            "sens": np.where(c.values > 0, "augmente le risque", "réduit le risque"),
        })


class ModeleChurn:
    """Modèle de churn prêt à l'emploi : encode un profil, calcule son score et l'explique."""

    def __init__(self, depot: DepotArtefacts | None = None):
        self.depot = depot or DepotArtefacts()
        self.meta = self.depot.meta_modele()
        self.colonnes = self.meta["colonnes"]
        self.seuil_alerte = float(self.meta["seuil_alerte"])
        self._booster = xgb.Booster()
        self._booster.load_model(str(self.depot.chemin_modele))
        if self.colonnes != preprocessing.colonnes_modele():
            raise ValueError("Les colonnes du modèle ne correspondent pas à celles de l'encodeur.")

    # ------------------------------------------------------------------ inférence
    def _matrice(self, profils: pd.DataFrame) -> xgb.DMatrix:
        X = preprocessing.encoder(profils)
        return xgb.DMatrix(X.to_numpy(dtype="float32"), feature_names=self.colonnes, missing=np.nan)

    def scores(self, profils: pd.DataFrame) -> np.ndarray:
        """Probabilité de départ pour chaque profil (une ligne = un profil)."""
        return self._booster.predict(self._matrice(profils))

    def contributions(self, profils: pd.DataFrame) -> pd.DataFrame:
        """Contribution de chaque variable métier (les indicatrices d'une même variable sont additionnées)."""
        brut = self._booster.predict(self._matrice(profils), pred_contribs=True)[:, :-1]
        par_colonne = pd.DataFrame(brut, columns=self.colonnes, index=profils.index)
        variables = [preprocessing.variable_d_origine(c) for c in self.colonnes]
        return par_colonne.T.groupby(variables, sort=False).sum().T

    def taux_observe(self, score: float) -> float | None:
        """Taux de départ réellement observé, sur le jeu de test, pour les scores de la même tranche."""
        for tranche in self.meta["score_vers_taux_observe"]:
            if tranche["de"] <= score <= tranche["a"]:
                return float(tranche["taux_observe"])
        return None

    def predire(self, profil: dict) -> Prediction:
        """Score, niveau de risque et explication pour **un** profil."""
        table = pd.DataFrame([profil])
        score = float(self.scores(table)[0])
        niveau, couleur = niveau_de_risque(score)
        return Prediction(
            score=score, niveau=niveau, couleur=couleur,
            au_dessus_du_seuil=score >= self.seuil_alerte,
            taux_observe=self.taux_observe(score),
            contributions=self.contributions(table).iloc[0],
        )


class GenerateurFictif:
    """Fabrique des profils **fictifs** à partir des distributions marginales publiées.

    Chaque variable est tirée indépendamment des autres : les profils obtenus sont plausibles
    variable par variable, mais ne correspondent à aucun client réel. Seule la prochaine revue
    est déduite des autres variables (règle du cycle de revue), pour que le profil reste cohérent.
    """

    def __init__(self, marginales: dict, graine: int = 42):
        self.marginales = marginales
        self.rng = np.random.default_rng(graine)

    def _numerique(self, spec: dict, n: int) -> np.ndarray:
        if spec["type"] == "discrete":
            f = np.asarray(spec["frequences"], dtype=float)
            valeurs = self.rng.choice(spec["valeurs"], size=n, p=f / f.sum())
        else:   # tirage uniforme à l'intérieur d'un décile tiré au hasard
            d = np.asarray(spec["deciles"], dtype=float)
            k = self.rng.integers(0, len(d) - 1, size=n)
            valeurs = d[k] + self.rng.random(n) * (d[k + 1] - d[k])
        valeurs = np.asarray(valeurs, dtype=float)
        valeurs[self.rng.random(n) < spec["part_manquante"]] = np.nan
        return valeurs

    def generer(self, n: int = 200) -> pd.DataFrame:
        profils = {}
        for nom, spec in self.marginales["numeriques"].items():
            profils[nom] = self._numerique(spec, n)
        for nom, frequences in self.marginales["categorielles"].items():
            f = np.asarray(list(frequences.values()), dtype=float)
            profils[nom] = self.rng.choice(list(frequences.keys()), size=n, p=f / f.sum())
        table = pd.DataFrame(profils)
        # Cohérence métier : la prochaine revue se déduit de la dernière et du cycle du score KYC.
        table["MOIS_AVANT_PROCHAINE_REVUE"] = [
            preprocessing.mois_avant_prochaine_revue(k, m)
            for k, m in zip(table["SCORE_KYC"], table["MOIS_DEPUIS_REVUE"])]
        for col in ("AGE", "NB_COMPTES", "DOSSIER_COMPLET"):
            table[col] = table[col].round()
        table.index = [f"Profil fictif {i + 1:03d}" for i in range(n)]
        return table
