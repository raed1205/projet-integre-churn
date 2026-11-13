"""Séries hebdomadaires de KPI et traitement des opérations de masse."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def serie_hebdo(dates: pd.Series, debut=None, fin=None) -> pd.Series:
    """Nombre d'événements par semaine (lundi), **semaines à zéro incluses**.

    ``dates`` doit déjà être au grain voulu (un événement = une ligne).
    """
    d = dates.dropna()
    comptage = d.groupby(d).size()
    debut = debut if debut is not None else comptage.index.min()
    fin = fin if fin is not None else comptage.index.max()
    index = pd.date_range(debut, fin, freq="W-MON")
    serie = comptage.reindex(index, fill_value=0).astype(int)
    serie.index.name = "semaine"
    return serie


def semaines_de_masse(serie: pd.Series, part: float = config.PART_MASSE) -> pd.DatetimeIndex:
    """Opérations de masse = le plus petit ensemble de semaines cumulant ``part`` du volume.

    Règle simple, sans seuil arbitraire : on trie les semaines par volume décroissant
    et on s'arrête dès que la part cumulée atteint ``part`` (50 % par défaut).
    """
    tri = serie.sort_values(ascending=False)
    cumul = tri.cumsum() / tri.sum()
    n = int(np.argmax(cumul.values >= part)) + 1
    return tri.index[:n].sort_values()


def corriger_masse(serie: pd.Series, masse: pd.DatetimeIndex, demi_fenetre: int = 4) -> pd.Series:
    """Série corrigée : chaque semaine de masse est remplacée par la médiane locale.

    La médiane est prise sur les ``demi_fenetre`` semaines avant et après,
    en excluant les autres semaines de masse. Le volume « ordinaire » est conservé,
    l'opération exceptionnelle est retirée.
    """
    corrigee = serie.astype(float).copy()
    ordinaire = serie.astype(float).copy()
    ordinaire[masse] = np.nan
    for semaine in masse:
        pos = serie.index.get_loc(semaine)
        voisinage = ordinaire.iloc[max(0, pos - demi_fenetre): pos + demi_fenetre + 1]
        corrigee[semaine] = float(np.nanmedian(voisinage.values))
    return corrigee.round().astype(int)


def fenetres(valeurs: np.ndarray, taille: int) -> tuple[np.ndarray, np.ndarray]:
    """Fenêtres glissantes : X[i] = ``taille`` semaines, y[i] = la semaine suivante."""
    X, y = [], []
    for i in range(len(valeurs) - taille):
        X.append(valeurs[i: i + taille])
        y.append(valeurs[i + taille])
    return np.asarray(X, dtype="float32"), np.asarray(y, dtype="float32")


def mae(y, p) -> float:
    return float(np.mean(np.abs(np.asarray(y, float) - np.asarray(p, float))))


def rmse(y, p) -> float:
    return float(np.sqrt(np.mean((np.asarray(y, float) - np.asarray(p, float)) ** 2)))
