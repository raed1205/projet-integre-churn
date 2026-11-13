"""Prévision d'un KPI hebdomadaire : LSTM / RNN et modèles de référence.

Toutes les prévisions de ce module sont « à un pas » : pour prévoir la semaine *t*,
le modèle ne voit que les semaines strictement antérieures à *t*. Les références
simples sont évaluées exactement dans les mêmes conditions, sur les mêmes semaines.

Protocole (identique pour tous les modèles) :

    |<------------- entraînement ------------->|<- validation ->|<---- test ---->|
                                                  (arrêt précoce)   (jamais vu)

* le découpage respecte l'ordre du temps (aucun mélange) ;
* la transformation ``log(1 + x)`` écrase les pics ;
* la normalisation (moyenne, écart-type) est calculée **sur l'entraînement seul**.
"""

from __future__ import annotations

import os
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE))
from vigie import config, series  # noqa: E402

TAILLE_TEST = 40        # ≈ 20 % de la série : les 40 dernières semaines
TAILLE_VALIDATION = 20  # semaines réservées à l'arrêt précoce
FENETRE = 8             # le modèle regarde les 8 dernières semaines (≈ 2 mois)
UNITES = 32
GRAINES = (42, 7, 123)  # trois initialisations : on rapporte la moyenne et la dispersion
HORIZON = 8             # semaines prévues au-delà de la fin de la série


@dataclass
class Decoupage:
    """Indices du découpage chronologique et paramètres de normalisation."""
    n: int
    fin_train: int
    fin_validation: int
    moyenne: float
    ecart_type: float

    @classmethod
    def construire(cls, valeurs: np.ndarray) -> "Decoupage":
        n = len(valeurs)
        fin_validation = n - TAILLE_TEST
        fin_train = fin_validation - TAILLE_VALIDATION
        z = np.log1p(valeurs[:fin_train])
        return cls(n, fin_train, fin_validation, float(z.mean()), float(z.std()))

    def normaliser(self, valeurs) -> np.ndarray:
        return (np.log1p(np.asarray(valeurs, dtype=float)) - self.moyenne) / self.ecart_type

    def denormaliser(self, z) -> np.ndarray:
        return np.clip(np.expm1(np.asarray(z, dtype=float) * self.ecart_type + self.moyenne), 0, None)


# --------------------------------------------------------------------------
# Modèles de référence (une ligne chacun : c'est tout leur intérêt)
# --------------------------------------------------------------------------
def references(valeurs: np.ndarray, debut: int) -> dict[str, np.ndarray]:
    """Prévisions à un pas des modèles simples, pour les semaines ``debut`` … fin."""
    v = np.asarray(valeurs, dtype=float)
    t = range(debut, len(v))
    return {
        "Naïve (dernière valeur)": np.array([v[i - 1] for i in t]),
        "Moyenne mobile 4 semaines": np.array([v[i - 4:i].mean() for i in t]),
        "Médiane mobile 8 semaines": np.array([np.median(v[i - 8:i]) for i in t]),
    }


def arima(valeurs: np.ndarray, debut: int) -> tuple[np.ndarray, tuple]:
    """ARIMA sur log(1 + x) : ordre choisi par AIC avant ``debut``, puis prévisions à un pas."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    z = np.log1p(np.asarray(valeurs, dtype=float))
    meilleur, meilleur_aic = None, np.inf
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p in range(3):
            for d in range(2):
                for q in range(3):
                    try:
                        res = SARIMAX(z[:debut], order=(p, d, q), trend="c" if d == 0 else "n").fit(disp=False)
                    except Exception:
                        continue
                    if res.aic < meilleur_aic:
                        meilleur, meilleur_aic = (p, d, q), res.aic
        res = SARIMAX(z[:debut], order=meilleur, trend="c" if meilleur[1] == 0 else "n").fit(disp=False)
        complet = res.apply(z)                       # mêmes paramètres, série complète
        prevision = complet.predict(start=debut, end=len(z) - 1)   # à un pas, sans ré-estimation
    return np.clip(np.expm1(prevision), 0, None), meilleur


# --------------------------------------------------------------------------
# Réseaux récurrents
# --------------------------------------------------------------------------
def construire_reseau(type_couche: str = "lstm", fenetre: int = FENETRE, unites: int = UNITES):
    """Une couche récurrente + une sortie : volontairement petit (≈ 200 points d'entraînement)."""
    import tensorflow as tf
    from tensorflow import keras

    tf.get_logger().setLevel("ERROR")
    couche = {"lstm": keras.layers.LSTM, "rnn": keras.layers.SimpleRNN}[type_couche]
    modele = keras.Sequential([
        keras.layers.Input((fenetre, 1)),
        couche(unites),
        keras.layers.Dense(1),
    ])
    # Erreur absolue : moins sensible aux pics que l'erreur quadratique.
    modele.compile(optimizer=keras.optimizers.Adam(learning_rate=0.005), loss="mae")
    return modele


@dataclass
class ResultatReseau:
    type_couche: str
    graine: int
    prevision_test: np.ndarray
    epoques: int
    historique: dict = field(default_factory=dict)
    modele: object = None


def entrainer_reseau(valeurs: np.ndarray, dec: Decoupage, type_couche: str = "lstm",
                     graine: int = config.GRAINE) -> ResultatReseau:
    """Entraîne un réseau et renvoie ses prévisions à un pas sur la période de test."""
    from tensorflow import keras

    keras.utils.set_random_seed(graine)
    z = dec.normaliser(valeurs)
    X, y = series.fenetres(z, FENETRE)
    cible = np.arange(FENETRE, dec.n)                     # indice de la semaine prévue par chaque fenêtre
    train = cible < dec.fin_train
    validation = (cible >= dec.fin_train) & (cible < dec.fin_validation)
    test = cible >= dec.fin_validation

    modele = construire_reseau(type_couche)
    arret = keras.callbacks.EarlyStopping(monitor="val_loss", patience=30, restore_best_weights=True)
    hist = modele.fit(X[train][..., None], y[train], validation_data=(X[validation][..., None], y[validation]),
                      epochs=300, batch_size=16, shuffle=True, verbose=0, callbacks=[arret])
    prevision = dec.denormaliser(modele.predict(X[test][..., None], verbose=0).ravel())
    return ResultatReseau(type_couche, graine, prevision, len(hist.history["loss"]),
                          {k: [float(v) for v in vals] for k, vals in hist.history.items()}, modele)


def prevoir_futur(modele, valeurs: np.ndarray, dec: Decoupage, horizon: int = HORIZON) -> np.ndarray:
    """Prévision récursive : chaque semaine prévue sert d'entrée pour la suivante."""
    fenetre = list(dec.normaliser(valeurs[-FENETRE:]))
    sorties = []
    for _ in range(horizon):
        x = np.asarray(fenetre[-FENETRE:], dtype="float32")[None, :, None]
        z = float(modele.predict(x, verbose=0).ravel()[0])
        sorties.append(z)
        fenetre.append(z)
    return dec.denormaliser(sorties)


# --------------------------------------------------------------------------
# Évaluation complète d'un KPI
# --------------------------------------------------------------------------
def evaluer_kpi(serie: pd.Series, graines=GRAINES, avec_arima: bool = True) -> dict:
    """Compare LSTM, RNN et références sur les ``TAILLE_TEST`` dernières semaines d'une série.

    Renvoie un dictionnaire sérialisable (tableau comparatif, prévisions, prévision future).
    """
    valeurs = serie.to_numpy(dtype=float)
    dec = Decoupage.construire(valeurs)
    reel = valeurs[dec.fin_validation:]
    semaines_test = serie.index[dec.fin_validation:]

    previsions = references(valeurs, dec.fin_validation)
    lignes = [{"Modèle": nom, "Type": "Référence", "MAE": series.mae(reel, p), "RMSE": series.rmse(reel, p)}
              for nom, p in previsions.items()]
    ordre_arima = None
    if avec_arima:
        previsions["ARIMA"], ordre_arima = arima(valeurs, dec.fin_validation)
        lignes.append({"Modèle": f"ARIMA{ordre_arima}", "Type": "Référence",
                       "MAE": series.mae(reel, previsions["ARIMA"]), "RMSE": series.rmse(reel, previsions["ARIMA"])})

    reseaux = {}
    for type_couche, nom in (("lstm", "LSTM"), ("rnn", "RNN simple")):
        essais = [entrainer_reseau(valeurs, dec, type_couche, g) for g in graines]
        maes = [series.mae(reel, e.prevision_test) for e in essais]
        rmses = [series.rmse(reel, e.prevision_test) for e in essais]
        reseaux[type_couche] = essais
        previsions[nom] = essais[0].prevision_test          # graine principale (42) pour les graphiques
        lignes.append({"Modèle": nom, "Type": "Deep Learning", "MAE": float(np.mean(maes)),
                       "RMSE": float(np.mean(rmses)), "MAE écart-type": float(np.std(maes)),
                       "RMSE écart-type": float(np.std(rmses)), "Époques": [e.epoques for e in essais]})

    lstm = reseaux["lstm"][0]
    futur = prevoir_futur(lstm.modele, valeurs, dec)
    # Intervalle empirique : quantiles 10 % / 90 % du rapport réel / prévu observé sur le test.
    rapport = np.log1p(reel) - np.log1p(lstm.prevision_test)
    bas, haut = np.quantile(rapport, [0.10, 0.90])
    semaines_futures = pd.date_range(serie.index[-1] + pd.Timedelta(weeks=1), periods=HORIZON, freq="W-MON")

    return {
        "decoupage": {"semaines": dec.n, "train": dec.fin_train, "validation": TAILLE_VALIDATION,
                      "test": TAILLE_TEST, "fenetre": FENETRE, "debut_test": str(semaines_test[0].date()),
                      "fin_test": str(semaines_test[-1].date())},
        "comparaison": lignes,
        "ordre_arima": list(ordre_arima) if ordre_arima else None,
        "test": {"semaines": [str(s.date()) for s in semaines_test], "reel": [int(v) for v in reel],
                 "previsions": {nom: [round(float(v), 1) for v in p] for nom, p in previsions.items()}},
        "futur": {"semaines": [str(s.date()) for s in semaines_futures],
                  "prevision": [round(float(v), 1) for v in futur],
                  "bas": [round(float(np.expm1(np.log1p(v) + bas)), 1) for v in futur],
                  "haut": [round(float(np.expm1(np.log1p(v) + haut)), 1) for v in futur]},
        "historique_lstm": lstm.historique,
        "_modele_lstm": lstm.modele,       # retiré avant sérialisation
    }
