"""Pipeline ETL en Python (bonus) — même logique que les jobs Talend.

    python 01_etl/pipeline_python/etl.py

Étapes :
    E  lecture du CSV et des 5 fichiers Excel (dossier data/, jamais versionné)
    T  typage, dédoublonnage, grains compte et client, variables dérivées
    L  chargement de PostgreSQL : staging, dimensions, puis table de faits

La connexion se configure par variables d'environnement (aucun mot de passe dans le code) :
    PGHOST (localhost)  PGPORT (5432)  PGDATABASE (vigie_dwh)  PGUSER (postgres)  PGPASSWORD

Ce script sert de **référence** : les jobs Talend doivent produire exactement les mêmes
volumes, ce que vérifient les requêtes de 02_data_warehouse/controles/controles.sql.
"""

from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE))
from vigie import donnees  # noqa: E402

SCHEMA_SQL = RACINE / "02_data_warehouse" / "schema" / "create_tables.sql"
NON_RENSEIGNE = "Non renseigné"

STATUT_MARITAL = {"C": "Célibataire", "M": "Marié(e)", "D": "Divorcé(e)", "V": "Veuf / veuve"}
FAMILLE_COMPTE = {
    "Epargne": "Dépôts", "Comptes courants": "Dépôts", "Comptes en devises": "Dépôts",
    "Exigibles": "Dépôts", "Placements a terme": "Dépôts", "Comptes indisponibles": "Dépôts",
    "Credit immobilier": "Crédits", "Credit consommation": "Crédits", "Credit automobile": "Crédits",
    "Credit investissement": "Crédits", "Financement court terme": "Crédits",
    "Autres comptes": "Autres", "Coffres": "Autres", "Contentieux": "Autres",
}


def connexion():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "vigie_dwh"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
    )


def copier(cur, table: str, df: pd.DataFrame) -> None:
    """Chargement en masse (COPY) : rapide et identique à un tDBOutput en mode « bulk »."""
    tampon = io.StringIO()
    df.to_csv(tampon, index=False, header=False, na_rep="\\N", sep="\t")
    tampon.seek(0)
    colonnes = ", ".join(df.columns)
    cur.copy_expert(f"COPY {table} ({colonnes}) FROM STDIN WITH (FORMAT text, NULL '\\N')", tampon)
    print(f"   {table:<32} {len(df):>9,} lignes".replace(",", " "))


def cle_date(serie: pd.Series) -> pd.Series:
    """Date -> clé AAAAMMJJ ; date manquante -> 0 (membre « inconnu »)."""
    return serie.dt.strftime("%Y%m%d").fillna("0").astype(int)


def dimension(codes: pd.Series, nom_code: str, nom_id: str, libelles: dict | None = None,
              libelle_inconnu: str = NON_RENSEIGNE, code_inconnu: str = "ND") -> pd.DataFrame:
    """Dimension simple : clé 0 = non renseigné, puis une clé par code trié."""
    valeurs = sorted(codes.dropna().unique())
    dim = pd.DataFrame({nom_id: range(1, len(valeurs) + 1), nom_code: valeurs})
    dim["libelle"] = [libelles.get(v, v) if libelles else v for v in valeurs]
    inconnu = pd.DataFrame({nom_id: [0], nom_code: [code_inconnu], "libelle": [libelle_inconnu]})
    return pd.concat([inconnu, dim], ignore_index=True)


def transformer(df: pd.DataFrame, refs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Construit toutes les tables du modèle en étoile."""
    comptes = donnees.grain_compte(df)
    clients = donnees.grain_client(df, comptes)
    date_ref = donnees.date_reference(df)
    lib = {nom: dict(zip(ref.iloc[:, 0], ref.iloc[:, 1])) for nom, ref in refs.items()}

    # ---------------- dimensions de référence ----------------
    dim_agence = dimension(clients["BRANCH_GROUP"], "code_groupe", "agence_id",
                           {c: f"Groupe d'agences {c[2:]}" for c in clients["BRANCH_GROUP"].unique()})
    dim_agence.loc[dim_agence["code_groupe"] == "AG00", "libelle"] = "Agences masquées"
    dim_agence["est_masque"] = dim_agence["code_groupe"].isin(["AG00", "ND"])

    dim_secteur = dimension(refs["INDUSTRY"]["INDUSTRY_CODE"], "code_secteur", "secteur_id", lib["INDUSTRY"])
    dim_devise = dimension(refs["CURRENCY"]["CURRENCY_CODE"], "code_devise", "devise_id", lib["CURRENCY"])
    dim_motif = dimension(refs["CLOSURE_REASON"]["REASON_ID"], "code_motif", "motif_id", lib["CLOSURE_REASON"],
                          libelle_inconnu="Sans motif (compte actif ou non saisi)")
    dim_categorie = dimension(refs["ACCOUNT_CATEGORY"]["CATEGORY_ID"], "code_categorie", "categorie_id",
                              lib["ACCOUNT_CATEGORY"])
    dim_categorie["famille"] = dim_categorie["libelle"].map(FAMILLE_COMPTE).fillna(NON_RENSEIGNE)

    produits = (comptes[["PRODUCT_GROUP", "PRODUCT_LINE"]].dropna().drop_duplicates()
                .sort_values(["PRODUCT_LINE", "PRODUCT_GROUP"]).reset_index(drop=True))
    dim_produit = pd.concat([
        pd.DataFrame({"produit_id": [0], "groupe_produit": [NON_RENSEIGNE], "ligne_produit": [NON_RENSEIGNE]}),
        pd.DataFrame({"produit_id": range(1, len(produits) + 1),
                      "groupe_produit": produits["PRODUCT_GROUP"], "ligne_produit": produits["PRODUCT_LINE"]}),
    ], ignore_index=True)

    # ---------------- dimension client ----------------
    c = clients.sort_values("CUSTOMER_NO").reset_index(drop=True)
    anciennete = (date_ref - c["CUST_OPENING_DATE"]).dt.days / 365.25
    mois_revue = (date_ref - c["LAST_REVIEW_DATE"]).dt.days / 30.4375
    dim_client = pd.DataFrame({
        "client_id": range(1, len(c) + 1),
        "code_client": c["CUSTOMER_NO"],
        "zone_nationalite": c["NATIONALITY_REGION"],
        "zone_residence": c["RESIDENCE_REGION"],
        "statut_marital": c["MARITAL_STATUS"].map(STATUT_MARITAL).fillna(NON_RENSEIGNE),
        "tranche_naissance": c["BIRTH_PERIOD"].astype("Int64"),
        "age": (date_ref.year - (c["BIRTH_PERIOD"] + 2)).astype("Int64"),
        "tranche_age": donnees.tranche_age(c["BIRTH_PERIOD"], date_ref.year),
        "nature_client": c["NATURE_CLIENT"],
        "segment": c["PARTYCLASS"],
        "ligne_metier": c["LOB"].map(lib["TARGET"]).fillna(NON_RENSEIGNE),
        "date_entree_relation": c["CUST_OPENING_DATE"].dt.date,
        "anciennete_annees": anciennete.round(2),
        "tranche_anciennete": donnees.tranche_anciennete(anciennete),
        "revenu_declare": c["SALARY"],
        "nb_comptes": c["NB_COMPTES"],
        "score_kyc": c["SCORE_KYC"].fillna(NON_RENSEIGNE),
        "dossier_complet": c["COMPLETED_FILE"] == "YES",
        "date_derniere_revue": c["LAST_REVIEW_DATE"].dt.date,
        "date_prochaine_revue": c["NEXT__REVIEW_DATE"].dt.date,
        "mois_depuis_revue": mois_revue.round(1),
        "revue_en_retard": (c["NEXT__REVIEW_DATE"] < date_ref).where(c["NEXT__REVIEW_DATE"].notna()),
        "est_churn": c["CHURN"],
    })

    # ---------------- table de faits ----------------
    k = comptes.sort_values("ACCOUNT_NO").reset_index(drop=True)
    k = k.merge(c[["CUSTOMER_NO", "BRANCH_GROUP", "INDUSTRY"]].assign(client_id=dim_client["client_id"]),
                on="CUSTOMER_NO", how="left", suffixes=("", "_CLIENT"))

    def cle(valeurs: pd.Series, dim: pd.DataFrame, code: str, ident: str) -> pd.Series:
        return valeurs.map(dict(zip(dim[code], dim[ident]))).fillna(0).astype(int)

    cle_produit = k[["PRODUCT_GROUP", "PRODUCT_LINE"]].merge(
        dim_produit, left_on=["PRODUCT_GROUP", "PRODUCT_LINE"],
        right_on=["groupe_produit", "ligne_produit"], how="left")["produit_id"].fillna(0).astype(int)
    fin = k["ACCT_CLOSE_DATE"].fillna(date_ref)
    anciennete_compte = (fin - k["ACCT_OPENING_DATE"]).dt.days
    # Anomalie de la source : pour certains comptes clos, l'ouverture est postérieure à la clôture.
    # On ne corrige pas la date ; on signale le compte et on ne calcule pas son ancienneté.
    incoherent = anciennete_compte < 0
    fait = pd.DataFrame({
        "compte_id": range(1, len(k) + 1),
        "code_compte": k["ACCOUNT_NO"],
        "client_id": k["client_id"],
        "agence_id": cle(k["BRANCH_GROUP"], dim_agence, "code_groupe", "agence_id"),
        "secteur_id": cle(k["INDUSTRY"], dim_secteur, "code_secteur", "secteur_id"),
        "categorie_id": cle(k["ACCOUNT_CATEGORY"], dim_categorie, "code_categorie", "categorie_id"),
        "devise_id": cle(k["CURRENCY"], dim_devise, "code_devise", "devise_id"),
        "motif_id": cle(k["CLOSURE_REASON"], dim_motif, "code_motif", "motif_id"),
        "produit_id": cle_produit.to_numpy(),
        "date_ouverture_id": cle_date(k["ACCT_OPENING_DATE"]),
        "date_cloture_id": cle_date(k["ACCT_CLOSE_DATE"]),
        "est_clos": k["CHURN"],
        "solde": k["ACCT_BALANCE"],
        "est_debiteur": (k["ACCT_BALANCE"] < 0).where(k["ACCT_BALANCE"].notna()),
        "montant_produit": k["AMOUNT"],
        "taux_fixe": k["FIXEDRATE"],
        "anciennete_compte_jours": anciennete_compte.where(~incoherent).astype("Int64"),
        "ouverture_apres_cloture": incoherent.to_numpy(),
        "statut_produit": k["PRODUCT_STATUS"],
        "nb_lignes_source": k["NB_LIGNES_SOURCE"],
    })
    return {
        "dwh.dim_agence": dim_agence, "dwh.dim_secteur": dim_secteur, "dwh.dim_devise": dim_devise,
        "dwh.dim_motif_cloture": dim_motif, "dwh.dim_categorie_compte": dim_categorie,
        "dwh.dim_produit": dim_produit, "dwh.dim_client": dim_client, "dwh.fait_compte": fait,
    }


def main() -> None:
    t0 = time.time()
    print("E — Extraction")
    brut = donnees.charger_brut()
    refs = donnees.charger_referentiels()
    print(f"   data_churn.csv : {len(brut):,} lignes, {brut.shape[1]} colonnes".replace(",", " "))

    print("T — Transformation")
    tables = transformer(donnees.typer(brut), refs)

    print("L — Chargement PostgreSQL")
    with connexion() as cnx, cnx.cursor() as cur:
        cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        staging = brut.rename(columns=str.lower)
        # Les tabulations et antislashs n'existent pas dans la source ; on s'en assure avant COPY.
        assert not staging.apply(lambda s: s.str.contains(r"[\t\\]", na=False)).any().any()
        copier(cur, "staging.stg_churn", staging)
        for nom, ref in refs.items():
            copier(cur, f"staging.stg_{nom.lower() if nom != 'TARGET' else 'target'}",
                   ref.rename(columns=str.lower))
        for table, df in tables.items():          # dimensions d'abord, faits en dernier
            copier(cur, table, df)
        cur.execute("ANALYZE")
    print(f"Terminé en {time.time() - t0:.0f} s.")


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
