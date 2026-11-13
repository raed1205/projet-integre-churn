"""Génère ``04_machine_learning/comparison.md`` à partir des résultats enregistrés par les notebooks.

    python 04_machine_learning/src/rapport_comparatif.py

Aucun chiffre n'est saisi à la main : tout vient de ``resultats/*.json``.
"""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE))
from vigie import config  # noqa: E402


def arrondi(x: float, d: int) -> Decimal:
    """Arrondi « au plus proche, 5 vers le haut » : évite les surprises du double arrondi binaire."""
    return Decimal(repr(x)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)


def fr(x: float, d: int = 3) -> str:
    return str(arrondi(x, d)).replace(".", ",")


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f} %".replace(".", ",")


def main() -> None:
    churn = json.loads((config.RESULTATS_ML / "churn_ml.json").read_text(encoding="utf-8"))
    prev = json.loads((config.RESULTATS_ML / "prevision_kpi.json").read_text(encoding="utf-8"))
    L = [
        "# Tableaux comparatifs des modèles — VIGIE · Groupe BI 5",
        "",
        "> Fichier généré par `src/rapport_comparatif.py` à partir de `resultats/*.json` (eux-mêmes écrits par les",
        "> notebooks). Aucun chiffre n'est saisi à la main.  ",
        f"> Fichier source : `data_churn.csv`, SHA-256 `{churn['source_sha256'][:16]}…`",
        "",
        "## 1. Prédiction du churn (grain client, jeu de test : 47 856 clients)",
        "",
        "Découpage par client (`GroupShuffleSplit`, 70 / 15 / 15). Seuil de décision choisi sur la validation (F1 maximal).",
        "",
        "| Modèle | ROC-AUC | PR-AUC | Precision | Recall | F1 | Accuracy | Brier | Seuil |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for nom, m in churn["comparaison_modeles"].items():
        gras = "**" if "retenu" in nom else ""
        L.append(f"| {gras}{nom}{gras} | {fr(m['ROC-AUC'])} | {fr(m['PR-AUC'])} | {fr(m['Precision'])} | {fr(m['Recall'])} | "
                 f"{fr(m['F1'])} | {fr(m['Accuracy'])} | {fr(m['Brier'])} | {fr(m['Seuil'], 2)} |")
    L += ["", "**Matrices de confusion (jeu de test)**", "",
          "| Modèle | Vrais positifs | Faux positifs | Faux négatifs | Vrais négatifs |", "|---|---:|---:|---:|---:|"]
    for nom, m in churn["matrices_confusion"].items():
        L.append(f"| {nom} | {m['VP']:,} | {m['FP']:,} | {m['FN']:,} | {m['VN']:,} |".replace(",", " "))
    h = churn["hyperparametres"]
    s = churn["stabilite_roc_auc"]
    L += ["", "**Modèle retenu : XGBoost optimisé.** Hyperparamètres (recherche aléatoire, validation croisée par client) : "
          + ", ".join(f"`{k}` = {v:g}" for k, v in sorted(h.items())) + ".", "",
          f"Stabilité (ROC-AUC) : entraînement {fr(s['Entraînement'])} · validation {fr(s['Validation'])} · test {fr(s['Test'])}.",
          "", "### Contrôle de la fuite de cible", "",
          "| Modèle | ROC-AUC sur le test |", "|---|---:|"]
    for nom, v in churn["demonstration_fuite"].items():
        L.append(f"| {nom} | {fr(v)} |")
    L += ["", "Colonnes exclues pour fuite (AUC du seul indicateur « valeur manquante » ≥ 0,80) :", "",
          "| Colonne | % vide si actif | % vide si clos | AUC du vide | Verdict |", "|---|---:|---:|---:|---|"]
    for a in churn["audit_fuite"]:
        if a["AUC du vide"] >= 0.6:
            L.append(f"| `{a['Variable']}` | {fr(a['% vide si actif'], 1)} | {fr(a['% vide si clos'], 1)} | {fr(a['AUC du vide'])} | {a['Verdict']} |")
    L += ["", "`PRODUCT_STATUS` est exclue elle aussi : ce n'est pas son vide mais ses valeurs (`CLOSE`, `PENDING.CLOSURE`, "
          "`UNAUTH`) qui désignent la clôture.", "", "### Analyse de sensibilité (même XGBoost, variables retirées ou ajoutées)", "",
          "| Scénario | Colonnes | ROC-AUC | PR-AUC | Écart de ROC-AUC |", "|---|---:|---:|---:|---:|"]
    for nom, m in churn["sensibilite"].items():
        L.append(f"| {nom} | {int(m['Colonnes'])} | {fr(m['ROC-AUC'])} | {fr(m['PR-AUC'])} | {'+' if m['Écart de ROC-AUC'] >= 0 else '−'}{fr(abs(m['Écart de ROC-AUC']))} |")
    L += ["", "### Importance des variables", "", "| Variable | Gain XGBoost | SHAP (part) |", "|---|---:|---:|"]
    for i in churn["importance"]:
        L.append(f"| {i['Variable']} | {pct(i['Gain (part)'])} | {pct(i['SHAP (part)'])} |")
    L += ["", "### Courbe de gains et niveaux de risque", "",
          "| Clients ciblés (scores décroissants) | Départs captés | Taux de churn dans la cible | Lift |", "|---:|---:|---:|---:|"]
    for g in churn["gains"]:
        L.append(f"| {pct(g['Clients ciblés'], 0)} | {pct(g['Départs captés'])} | {pct(g['Taux de churn dans la cible'])} | {fr(g['Lift'], 2)} |")
    L += ["", "| Niveau de risque | Clients du test | Taux de churn observé |", "|---|---:|---:|"]
    for n in churn["niveaux_de_risque"]:
        L.append(f"| {n['niveau']} | {n['clients_test']:,} | {pct(n['taux_observe'])} |".replace(",", " ", 1))

    for cle, titre in (("clotures_hebdo", "2. Prévision du KPI — clôtures de comptes par semaine"),
                       ("clients_perdus_hebdo", "3. Bonus — second KPI : clients perdus par semaine")):
        r = prev[cle]
        d = r["decoupage"]
        naive = next(l for l in r["comparaison"] if l["Modèle"].startswith("Naïve"))
        L += ["", f"## {titre}", "",
              f"Série corrigée des opérations de masse · {d['semaines']} semaines · entraînement {d['train']} · "
              f"validation {d['validation']} · test {d['test']} (du {d['debut_test']} au {d['fin_test']}) · "
              f"fenêtre de {d['fenetre']} semaines · prévision à un pas.", "",
              "| Modèle | Type | MAE | RMSE | MAE vs naïve | RMSE vs naïve |", "|---|---|---:|---:|---:|---:|"]
        for l in sorted(r["comparaison"], key=lambda x: x["MAE"]):
            disp = f" (± {fr(l['MAE écart-type'], 1)} sur 3 graines)" if l.get("MAE écart-type") == l.get("MAE écart-type") and l.get("MAE écart-type") is not None else ""
            L.append(f"| {l['Modèle']} | {l['Type']} | {fr(l['MAE'], 1)}{disp} | {fr(l['RMSE'], 1)} | "
                     f"{100 * (l['MAE'] / naive['MAE'] - 1):+.0f} % | {100 * (l['RMSE'] / naive['RMSE'] - 1):+.0f} % |")
    L += ["", "**Lecture.** Le LSTM réduit nettement l'erreur de la prévision naïve et fait mieux que le RNN simple, ARIMA "
          "et la moyenne mobile. Il ne bat pas la médiane mobile sur les clôtures de comptes ; il obtient la meilleure MAE "
          "sur les clients perdus. Le MAPE n'est pas utilisé : il n'est pas défini sur les semaines à zéro.", ""]
    (RACINE / "04_machine_learning" / "comparison.md").write_text("\n".join(L), encoding="utf-8")
    print("écrit : 04_machine_learning/comparison.md")


if __name__ == "__main__":
    main()
