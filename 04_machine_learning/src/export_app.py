"""Export des artefacts de l'application : **agrégats et paramètres, jamais de ligne client**.

Trois fichiers JSON lisibles sont écrits dans ``05_web_app/artifacts/`` :

* ``kpi_synthese.json``     indicateurs agrégés (aucun effectif publié sous le seuil de confidentialité) ;
* ``modele_churn.json``     les arbres du modèle XGBoost (seuils de coupure et valeurs des feuilles) ;
* ``modele_churn_meta.json`` seuil, métriques, importance des variables, distributions marginales.

Un fichier JSON d'arbres ne contient aucune observation : uniquement des règles du type
« ancienneté < 6,5 ans ». Il est donc publiable, contrairement à un fichier ``.pkl`` qui peut
embarquer des données d'entraînement — ceux-ci restent dans ``04_machine_learning/models/``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE))
from vigie import config, donnees  # noqa: E402

SEUIL = config.SEUIL_PETIT_EFFECTIF


def _axe(table: pd.DataFrame, colonne, cible: str, ordre: list | None = None) -> list[dict]:
    """Effectif et taux de churn par modalité, en masquant les petits effectifs."""
    g = table.groupby(colonne, observed=True)[cible].agg(["size", "mean"])
    g = g[g["size"] >= SEUIL]
    if ordre:
        g = g.loc[[m for m in ordre if m in g.index]]
    else:
        g = g.sort_values("size", ascending=False)
    return [{"modalite": str(m), "effectif": int(r["size"]), "taux_churn": round(float(r["mean"]), 4)}
            for m, r in g.iterrows()]


def agregats_synthese(df: pd.DataFrame, comptes: pd.DataFrame, clients: pd.DataFrame,
                      refs: dict[str, pd.DataFrame]) -> dict:
    """Tous les indicateurs affichés par l'application et par l'interface JavaScript."""
    date_ref = donnees.date_reference(df)
    c = clients[clients["CHURN"].notna()].copy()
    c["CHURN"] = c["CHURN"].astype(int)
    anciennete = (date_ref - c["CUST_OPENING_DATE"]).dt.days / 365.25
    c["Tranche d'âge"] = donnees.tranche_age(c["BIRTH_PERIOD"], date_ref.year)
    c["Ancienneté"] = donnees.tranche_anciennete(anciennete)
    c["Dossier client"] = np.where(c["COMPLETED_FILE"] == "YES", "Complet", "Incomplet")
    c["Revue du dossier"] = np.where(c["NEXT__REVIEW_DATE"] < date_ref, "En retard", "À jour")
    c["Nombre de comptes"] = c["NB_COMPTES"].clip(upper=5).map(lambda n: str(n) if n < 5 else "5 et +")
    c["Statut marital"] = c["MARITAL_STATUS"].map(
        {"C": "Célibataire", "M": "Marié(e)", "D": "Divorcé(e)", "V": "Veuf / veuve"}).fillna("Non renseigné")
    c["Score KYC"] = c["SCORE_KYC"].fillna("Non renseigné")
    lib_secteur = dict(zip(refs["INDUSTRY"]["INDUSTRY_CODE"], refs["INDUSTRY"]["DESCRIPTION"]))
    c["Secteur d'activité"] = c["INDUSTRY"].map(lib_secteur)

    k = comptes.copy()
    k["Famille de compte"] = k["ACCOUNT_TYPE_DESC"].fillna("Non renseigné")
    lib_dev = dict(zip(refs["CURRENCY"]["CURRENCY_CODE"], refs["CURRENCY"]["DESCRIPTION"]))
    k["Devise"] = k["CURRENCY"].map(lib_dev).fillna("Non renseigné")
    k["Groupe de produits"] = k["PRODUCT_GROUP"].fillna("Non renseigné")
    actifs = k[k["CHURN"] == 0]
    clos = k[k["CHURN"] == 1]
    lib_motif = dict(zip(refs["CLOSURE_REASON"]["REASON_ID"], refs["CLOSURE_REASON"]["DESCRIPTION"]))
    motifs = clos["CLOSURE_REASON"].map(lib_motif).fillna("Non saisi").value_counts()

    ordre_age = ["< 18 ans", "18–24 ans", "25–34 ans", "35–44 ans", "45–54 ans", "55–64 ans", "65 ans et +",
                 "Non renseigné"]
    ordre_anc = ["< 2 ans", "2–5 ans", "5–10 ans", "10–15 ans", "15 ans et +", "Non renseigné"]

    # Valeur client : profil médian par segment (comptes actifs uniquement, où le solde est renseigné).
    solde_client = actifs.groupby("CUSTOMER_NO")["ACCT_BALANCE"].sum().rename("SOLDE_TOTAL")
    seg = c.set_index("CUSTOMER_NO").join(solde_client)
    segments = []
    for nom, bloc in seg.groupby("PARTYCLASS"):
        if len(bloc) < SEUIL:
            continue
        segments.append({
            "segment": nom, "clients": int(len(bloc)), "taux_churn": round(float(bloc["CHURN"].mean()), 4),
            "anciennete_moyenne": round(float(((date_ref - bloc["CUST_OPENING_DATE"]).dt.days / 365.25).mean()), 1),
            "comptes_par_client": round(float(bloc["NB_COMPTES"].mean()), 2),
            "part_multi_equipes": round(float((bloc["NB_COMPTES"] > 1).mean()), 4),
            "part_dossier_complet": round(float((bloc["COMPLETED_FILE"] == "YES").mean()), 4),
            "solde_median_clients_actifs": round(float(bloc["SOLDE_TOTAL"].median()), 0),
        })
    segments.sort(key=lambda s: -s["clients"])

    return {
        "source": {"fichier": "data_churn.csv", "sha256": donnees.empreinte()["sha256"],
                   "date_reference": str(date_ref.date()), "seuil_petit_effectif": SEUIL,
                   "note": "Agrégats uniquement. Dates décalées et montants arrondis par l'anonymisation."},
        "global": {
            "lignes_source": int(len(df)),
            "comptes": int(len(k)), "comptes_actifs": int(len(actifs)), "comptes_clos": int(len(clos)),
            "taux_churn_comptes": round(float(k["CHURN"].mean()), 4),
            "clients": int(len(clients)), "clients_avec_compte": int(len(c)),
            "clients_partis": int(c["CHURN"].sum()),
            "taux_churn_clients": round(float(c["CHURN"].mean()), 4),
            "taux_churn_tous_clients": round(float(c["CHURN"].sum() / len(clients)), 4),
            "taux_churn_lignes": round(float((df["ACCOUNT_STATUS"] == "Closed").sum()
                                             / df["ACCOUNT_STATUS"].notna().sum()), 4),
            "anciennete_moyenne_clients": round(float(anciennete.mean()), 2),
            "solde_median_comptes_actifs": float(actifs["ACCT_BALANCE"].median()),
            "part_comptes_debiteurs_actifs": round(float((actifs["ACCT_BALANCE"] < 0).mean()), 4),
            "part_multi_equipes": round(float((c["NB_COMPTES"] > 1).mean()), 4),
            "part_dossier_complet": round(float((c["COMPLETED_FILE"] == "YES").mean()), 4),
            "part_revue_en_retard": round(float((c["NEXT__REVIEW_DATE"] < date_ref).mean()), 4),
        },
        "axes_client": {
            "Tranche d'âge": _axe(c, "Tranche d'âge", "CHURN", ordre_age),
            "Ancienneté": _axe(c, "Ancienneté", "CHURN", ordre_anc),
            "Dossier client": _axe(c, "Dossier client", "CHURN", ["Complet", "Incomplet"]),
            "Revue du dossier": _axe(c, "Revue du dossier", "CHURN", ["À jour", "En retard"]),
            "Nombre de comptes": _axe(c, "Nombre de comptes", "CHURN", ["1", "2", "3", "4", "5 et +"]),
            "Segment commercial": _axe(c, "PARTYCLASS", "CHURN"),
            "Score KYC": _axe(c, "Score KYC", "CHURN", ["LR", "MR", "H1", "H2", "H3"]),
            "Nature du client": _axe(c, "NATURE_CLIENT", "CHURN"),
            "Statut marital": _axe(c, "Statut marital", "CHURN"),
            "Zone de résidence": _axe(c, "RESIDENCE_REGION", "CHURN"),
            "Groupe d'agences": _axe(c, "BRANCH_GROUP", "CHURN", sorted(c["BRANCH_GROUP"].unique())),
            "Secteur d'activité": _axe(c, "Secteur d'activité", "CHURN"),
        },
        "axes_compte": {
            "Famille de compte": _axe(k, "Famille de compte", "CHURN"),
            "Devise": _axe(k, "Devise", "CHURN"),
            "Groupe de produits": _axe(k, "Groupe de produits", "CHURN"),
        },
        "segments": segments,
        "motifs_cloture": [{"motif": m, "comptes": int(n)} for m, n in motifs.items() if n >= SEUIL],
        "clotures_par_annee": [{"annee": int(a), "comptes": int(n)} for a, n in
                               clos["ACCT_CLOSE_DATE"].dt.year.value_counts().sort_index().items()],
    }


def marginales(profils: pd.DataFrame, numeriques: list[str], categorielles: dict) -> dict:
    """Distributions marginales des variables du modèle (pour générer des profils FICTIFS).

    Chaque variable est décrite seule (déciles ou fréquences). Tirer chaque variable
    indépendamment produit des profils plausibles qui ne correspondent à aucun client réel.
    """
    out = {"numeriques": {}, "categorielles": {}}
    for col in numeriques:
        s = profils[col].dropna()
        entiere = bool((s == s.round()).all())
        if entiere and s.nunique() > 15 and s.quantile(0.99) <= 15:
            s = s.clip(upper=s.quantile(0.99))      # variable de comptage : on regroupe la queue (≥ 99e centile)
        valeurs = s.value_counts(normalize=True)
        if len(valeurs) <= 15:      # variable discrète : fréquences
            out["numeriques"][col] = {
                "type": "discrete", "part_manquante": round(float(profils[col].isna().mean()), 4),
                "valeurs": [float(v) for v in valeurs.index], "frequences": [round(float(f), 5) for f in valeurs.values]}
        else:                       # variable continue : déciles
            out["numeriques"][col] = {
                "type": "continue", "part_manquante": round(float(profils[col].isna().mean()), 4),
                "deciles": [round(float(q), 2) for q in s.quantile(np.linspace(0, 1, 11))]}
    for col in categorielles:
        f = profils[col].value_counts(normalize=True)
        out["categorielles"][col] = {str(m): round(float(v), 5) for m, v in f.items()}
    return out


def ecrire(nom: str, contenu: dict) -> Path:
    config.ARTEFACTS_APP.mkdir(parents=True, exist_ok=True)
    chemin = config.ARTEFACTS_APP / nom
    chemin.write_text(json.dumps(contenu, ensure_ascii=False, indent=1), encoding="utf-8")
    return chemin
