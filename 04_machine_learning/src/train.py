"""Ré-entraîne les deux modèles finaux en une commande et vérifie les résultats publiés.

    python 04_machine_learning/src/train.py              # churn + série temporelle
    python 04_machine_learning/src/train.py --churn      # churn seulement
    python 04_machine_learning/src/train.py --serie      # série temporelle seulement

Ce script utilise exactement les mêmes fonctions que les notebooks (``churn.py``,
``prevision.py``). Il :

1. reconstruit les jeux de données à partir de ``data/`` ;
2. ré-entraîne le XGBoost final et le LSTM ;
3. enregistre les modèles dans ``04_machine_learning/models/`` (dossier **hors dépôt**) ;
4. compare les métriques obtenues à celles publiées dans ``resultats/*.json`` :
   si tout est reproductible, l'écart affiché est nul.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import joblib
import pandas as pd

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import churn  # noqa: E402
import prevision  # noqa: E402
from vigie import config, donnees, series, variables  # noqa: E402

warnings.filterwarnings("ignore")


def verifier(nom: str, obtenu: float, publie: float, tolerance: float = 1e-3) -> bool:
    ecart = abs(obtenu - publie)
    verdict = "OK" if ecart <= tolerance else "ÉCART"
    print(f"   {nom:<34} obtenu {obtenu:>9.4f}   publié {publie:>9.4f}   {verdict}")
    return ecart <= tolerance


def entrainer_churn(df: pd.DataFrame) -> bool:
    print("\n=== Modèle de churn (XGBoost, grain client) ===")
    comptes = donnees.grain_compte(df)
    clients = donnees.grain_client(df, comptes)
    _, X, y, groupes = variables.jeu_modelisation(clients, donnees.date_reference(df))
    d = churn.decouper(y, groupes)
    print(f"   {len(y):,} clients · entraînement {len(d['train']):,} · validation {len(d['validation']):,} · "
          f"test {len(d['test']):,}".replace(",", " "))

    publie = json.loads((config.RESULTATS_ML / "churn_ml.json").read_text(encoding="utf-8"))
    modele = churn.xgboost(**publie["hyperparametres"]).fit(X.iloc[d["train"]], y[d["train"]])
    seuil = churn.seuil_f1(y[d["validation"]], modele.predict_proba(X.iloc[d["validation"]])[:, 1])
    metriques = churn.evaluer(y[d["test"]], modele.predict_proba(X.iloc[d["test"]])[:, 1], seuil)

    config.MODELES.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modele": modele, "colonnes": list(X.columns), "seuil": seuil}, config.MODELES / "model_final.pkl")
    print("   modèle enregistré : 04_machine_learning/models/model_final.pkl (hors dépôt)")

    reference = publie["comparaison_modeles"]["XGBoost optimisé (retenu)"]
    return all([verifier(k, metriques[k], reference[k]) for k in ("ROC-AUC", "PR-AUC", "Precision", "Recall", "F1")])


def entrainer_serie(df: pd.DataFrame) -> bool:
    print("\n=== Prévision du KPI (LSTM, clôtures hebdomadaires) ===")
    comptes = donnees.grain_compte(df)
    brute = series.serie_hebdo(comptes.loc[comptes["CHURN"] == 1, "ACCT_CLOSE_DATE"])
    serie = series.corriger_masse(brute, series.semaines_de_masse(brute))
    print(f"   {len(serie)} semaines · {int(brute.sum()):,} clôtures".replace(",", " "))

    resultat = prevision.evaluer_kpi(serie)
    modele = resultat.pop("_modele_lstm")
    config.MODELES.mkdir(parents=True, exist_ok=True)
    modele.save(config.MODELES / "lstm_clotures_hebdo.keras")
    print("   modèle enregistré : 04_machine_learning/models/lstm_clotures_hebdo.keras (hors dépôt)")

    publie = json.loads((config.RESULTATS_ML / "prevision_kpi.json").read_text(encoding="utf-8"))
    reference = {l["Modèle"]: l for l in publie["clotures_hebdo"]["comparaison"]}
    ok = []
    for ligne in resultat["comparaison"]:
        ok.append(verifier(f"MAE  {ligne['Modèle']}"[:34], ligne["MAE"], reference[ligne["Modèle"]]["MAE"], 0.5))
        ok.append(verifier(f"RMSE {ligne['Modèle']}"[:34], ligne["RMSE"], reference[ligne["Modèle"]]["RMSE"], 0.5))
    return all(ok)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--churn", action="store_true", help="ré-entraîner uniquement le modèle de churn")
    parser.add_argument("--serie", action="store_true", help="ré-entraîner uniquement le LSTM")
    args = parser.parse_args()
    tout = not (args.churn or args.serie)

    print(f"{config.NOM_PROJET} · {config.GROUPE} — ré-entraînement des modèles")
    print("Fichier source :", donnees.empreinte()["sha256"][:16], "…")
    df = donnees.charger()
    resultats = []
    if tout or args.churn:
        resultats.append(entrainer_churn(df))
    if tout or args.serie:
        resultats.append(entrainer_serie(df))
    reproductible = all(resultats)
    print("\nRésultats publiés reproduits à l'identique." if reproductible
          else "\nATTENTION : écart avec les résultats publiés (versions de bibliothèques différentes ?).")
    return 0 if reproductible else 1


if __name__ == "__main__":
    sys.exit(main())
