"""Chargement, typage et construction des grains d'analyse.

Trois grains coexistent dans le fichier source :

* **ligne**  : un rapprochement client / compte / produit (483 536 lignes) ;
* **compte** : une ligne par ``ACCOUNT_NO`` (410 309 comptes) ;
* **client** : une ligne par ``CUSTOMER_NO`` (363 024 clients).

Toutes les fonctions sont déterministes : même fichier => mêmes chiffres.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from . import config

FICHIER_PRINCIPAL = "data_churn.csv"
REFERENTIELS = {
    "ACCOUNT_CATEGORY": "CATEGORY_ID",
    "CLOSURE_REASON": "REASON_ID",
    "CURRENCY": "CURRENCY_CODE",
    "INDUSTRY": "INDUSTRY_CODE",
    "TARGET": "TARGET_CODE",
}

COLONNES_DATES = [
    "CUST_OPENING_DATE", "LAST_REVIEW_DATE", "NEXT__REVIEW_DATE",
    "ACCT_OPENING_DATE", "ACCT_CLOSE_DATE", "STARTDATE", "MATURITYDATE",
]
COLONNES_NUMERIQUES = ["BIRTH_PERIOD", "SALARY", "ACCT_BALANCE", "AMOUNT", "FIXEDRATE"]

COLONNES_CLIENT = [
    "CUSTOMER_NO", "NATIONALITY_REGION", "RESIDENCE_REGION", "MARITAL_STATUS",
    "BIRTH_PERIOD", "CUST_OPENING_DATE", "NATURE_CLIENT", "PARTYCLASS", "LOB",
    "SCORE_KYC", "COMPLETED_FILE", "LAST_REVIEW_DATE", "NEXT__REVIEW_DATE",
    "INDUSTRY", "SALARY", "BRANCH_GROUP",
]
COLONNES_COMPTE = [
    "ACCOUNT_NO", "CUSTOMER_NO", "ACCOUNT_STATUS", "ACCT_OPENING_DATE",
    "ACCT_CLOSE_DATE", "ACCOUNT_CATEGORY", "ACCOUNT_TYPE_DESC", "CURRENCY",
    "CLOSURE_REASON", "ACCT_BALANCE", "PRODUCT_GROUP", "PRODUCT_LINE",
    "STARTDATE", "MATURITYDATE", "AMOUNT", "FIXEDRATE", "PRODUCT_STATUS",
]


def _dossier(dossier: str | Path | None) -> Path:
    d = Path(dossier) if dossier else config.DOSSIER_DONNEES
    if not (d / FICHIER_PRINCIPAL).exists():
        raise FileNotFoundError(
            f"{FICHIER_PRINCIPAL} introuvable dans {d}. Copiez les fichiers fournis par les "
            "tuteurs dans data/ (ignoré par git) ou définissez VIGIE_DATA_DIR."
        )
    return d


def empreinte(dossier: str | Path | None = None) -> dict:
    """Empreinte SHA-256 du fichier source : prouve sur quel fichier on a calculé."""
    chemin = _dossier(dossier) / FICHIER_PRINCIPAL
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return {"fichier": FICHIER_PRINCIPAL, "sha256": h.hexdigest(), "octets": chemin.stat().st_size}


def charger_brut(dossier: str | Path | None = None) -> pd.DataFrame:
    """Lit le CSV tel quel : tout en texte, les vides restent des valeurs manquantes."""
    return pd.read_csv(
        _dossier(dossier) / FICHIER_PRINCIPAL,
        dtype=str, keep_default_na=False, na_values=[""],
    )


def typer(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit les dates YYYYMMDD et les colonnes numériques."""
    out = df.copy()
    for c in COLONNES_DATES:
        out[c] = pd.to_datetime(out[c], format="%Y%m%d", errors="coerce")
    for c in COLONNES_NUMERIQUES:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def charger(dossier: str | Path | None = None) -> pd.DataFrame:
    """Données au grain ligne, typées."""
    return typer(charger_brut(dossier))


def charger_referentiels(dossier: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Les cinq fichiers Excel de libellés, indexés par leur nom."""
    d = _dossier(dossier)
    refs = {}
    for nom in REFERENTIELS:
        ref = pd.read_excel(d / f"{nom}.xlsx", dtype=str)
        ref.columns = [c.strip() for c in ref.columns]
        refs[nom] = ref
    return refs


def date_reference(df: pd.DataFrame) -> pd.Timestamp:
    """Date de la « photographie » : dernier événement de compte observé."""
    return max(df["ACCT_OPENING_DATE"].max(), df["ACCT_CLOSE_DATE"].max())


def grain_compte(df: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par compte.

    Règle de dédoublonnage (justifiée dans le rapport) :

    1. on écarte les lignes sans ``ACCOUNT_NO`` (clients sans compte) ;
    2. quand un compte porte plusieurs dates de clôture, on garde la **première**
       (c'est l'événement de churn ; les suivantes sont des régularisations) ;
    3. ``NB_LIGNES_SOURCE`` conserve le nombre de lignes fusionnées, pour le contrôle.
    """
    a = df[df["ACCOUNT_NO"].notna()]
    nb = a.groupby("ACCOUNT_NO", sort=False).size().rename("NB_LIGNES_SOURCE")
    comptes = (
        a.sort_values(["ACCOUNT_NO", "ACCT_CLOSE_DATE", "CLOSURE_REASON"], na_position="last")
        .drop_duplicates("ACCOUNT_NO", keep="first")
        .set_index("ACCOUNT_NO")
        .join(nb)
        .reset_index()
    )
    comptes["CHURN"] = (comptes["ACCOUNT_STATUS"] == "Closed").astype(int)
    return comptes


def grain_client(df: pd.DataFrame, comptes: pd.DataFrame | None = None) -> pd.DataFrame:
    """Une ligne par client, avec son nombre de comptes et son churn.

    Churn client = **tous** ses comptes sont clos. Dans ce jeu de données, aucun
    client n'a à la fois un compte actif et un compte clos : la définition
    « tous clos » et la définition « au moins un clos » coïncident.
    Les clients sans compte ont ``CHURN`` manquant (hors périmètre du churn).
    """
    if comptes is None:
        comptes = grain_compte(df)
    clients = df[COLONNES_CLIENT].drop_duplicates("CUSTOMER_NO").set_index("CUSTOMER_NO")
    agg = comptes.groupby("CUSTOMER_NO").agg(
        NB_COMPTES=("ACCOUNT_NO", "size"),
        NB_COMPTES_CLOS=("CHURN", "sum"),
        DATE_CHURN=("ACCT_CLOSE_DATE", "max"),
    )
    clients = clients.join(agg)
    clients["NB_COMPTES"] = clients["NB_COMPTES"].fillna(0).astype(int)
    avec_compte = clients["NB_COMPTES"] > 0
    clients["CHURN"] = pd.NA
    clients.loc[avec_compte, "CHURN"] = (
        clients.loc[avec_compte, "NB_COMPTES_CLOS"] == clients.loc[avec_compte, "NB_COMPTES"]
    ).astype(int)
    clients["CHURN"] = clients["CHURN"].astype("Int64")
    return clients.reset_index()


def tranche_age(birth_period: pd.Series, annee_ref: int) -> pd.Series:
    """Tranche d'âge lisible, calculée au milieu de la tranche de naissance de 5 ans."""
    age = annee_ref - (birth_period + 2)
    bornes = [-1, 17, 24, 34, 44, 54, 64, 200]
    noms = ["< 18 ans", "18–24 ans", "25–34 ans", "35–44 ans", "45–54 ans", "55–64 ans", "65 ans et +"]
    return pd.cut(age, bins=bornes, labels=noms).astype("object").fillna("Non renseigné")


def tranche_anciennete(annees: pd.Series) -> pd.Series:
    bornes = [-0.01, 2, 5, 10, 15, 100]
    noms = ["< 2 ans", "2–5 ans", "5–10 ans", "10–15 ans", "15 ans et +"]
    return pd.cut(annees, bins=bornes, labels=noms).astype("object").fillna("Non renseigné")
