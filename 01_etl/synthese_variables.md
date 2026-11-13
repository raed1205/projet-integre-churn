# Synthèse par variable — jalon 1

> Généré par `01_etl/notebooks/01_analyse_univariee.ipynb` · VIGIE · Groupe BI 5  
> Fichier analysé : `data_churn.csv` — SHA-256 `858551b4293ee1ab…` — 483 536 lignes, 32 colonnes.

Méthode outliers : **IQR** (hors de `[Q1 − 1,5·IQR ; Q3 + 1,5·IQR]`, méthode de référence) et **z-score** (`|z| > 3`), calculés au grain naturel de la variable (compte ou client). Aucune ligne n'est supprimée pour cause d'outlier.

| Variable | Type | % manquants (lignes) | % manquants (grain naturel) | Nature du vide | Outliers IQR | Outliers z-score | Décision proposée |
|---|---|---:|---:|---|---:|---:|---|
| `CUSTOMER_NO` | Identifiant | 0.0 | 0.0 | — | — | — | Clé de la dimension client ; jamais affiché |
| `ACCOUNT_NO` | Identifiant | 9.1 | 0.0 | Structurel (client sans compte) | — | — | Clé du fait compte ; lignes sans compte → dimension client seulement |
| `NATIONALITY_REGION` | Qualitative (6) | 0.0 | 0.0 | — | — | — | Conserver ; redondante avec la résidence |
| `RESIDENCE_REGION` | Qualitative (6) | 0.0 | 0.0 | — | — | — | Conserver ; regrouper les modalités rares |
| `MARITAL_STATUS` | Qualitative (4) | 16.5 | 10.9 | Déclaratif / anonymisation | — | — | Vide → modalité « Non renseigné » |
| `CUST_OPENING_DATE` | Date (précision variable) | 3.5 | 4.3 | Anonymisation | — | — | Convertir ; dériver l'ancienneté client |
| `BIRTH_PERIOD` | Quantitative discrète | 13.2 | 6.4 | Déclaratif / anonymisation | 0 | 0 | Dériver l'âge et la tranche d'âge |
| `NATURE_CLIENT` | Qualitative (5) | 0.0 | 0.0 | — | — | — | Conserver ; TRPP/TRPM → « Autre » |
| `BRANCH_GROUP` | Qualitative (21) | 0.0 | 0.0 | — | — | — | Dimension agence ; AG00 = « masqué » |
| `SCORE_KYC` | Qualitative ordinale (5) | 0.2 | 0.2 | Résiduel | — | — | Conserver ; vide → « Non renseigné » |
| `COMPLETED_FILE` | Binaire (YES / vide) | 48.8 | 55.0 | Signifiant (dossier incomplet) | — | — | Recoder en 0/1 (vide = incomplet) |
| `LAST_REVIEW_DATE` | Date (mois) | 5.6 | 7.4 | Structurel (client sans compte) | — | — | Convertir ; dériver les mois depuis la revue |
| `NEXT__REVIEW_DATE` | Date (mois) | 5.0 | 6.6 | Structurel (client sans compte) | — | — | Convertir ; dériver les mois avant la revue |
| `ACCOUNT_STATUS` | Binaire — cible | 9.1 | 0.0 | Structurel (client sans compte) | — | — | Cible : Closed = 1, Active = 0 |
| `ACCT_OPENING_DATE` | Date (semaine) | 29.9 | 24.5 | Lié à la clôture ⚠ | — | — | Convertir ; exclue du modèle (fuite) |
| `ACCOUNT_CATEGORY` | Qualitative (14) | 29.9 | 24.5 | Lié à la clôture ⚠ | — | — | Joindre le référentiel ; exclue du modèle (fuite) |
| `ACCOUNT_TYPE_DESC` | Qualitative (14) | 29.9 | 24.5 | Lié à la clôture ⚠ | — | — | Redondante avec ACCOUNT_CATEGORY |
| `CURRENCY` | Qualitative (5) | 29.9 | 24.5 | Lié à la clôture ⚠ | — | — | Joindre le référentiel ; exclue du modèle (fuite) |
| `ACCT_CLOSE_DATE` | Date (semaine) | 63.3 | 63.9 | Métier (compte actif) | — | — | Garder la 1re date ; série temporelle ; exclue du modèle (fuite) |
| `CLOSURE_REASON` | Qualitative (12) | 70.7 | 67.2 | Métier (compte actif) | — | — | Joindre le référentiel ; exclue du modèle (fuite) |
| `ACCT_BALANCE` | Quantitative continue | 29.9 | 24.5 | Lié à la clôture ⚠ | 99 362 | 1 685 | Conserver les négatifs (débiteurs) ; médiane et tranches ; exclue du modèle (fuite) |
| `INDUSTRY` | Qualitative (21) | 0.0 | 0.0 | — | — | — | Joindre INDUSTRY.xlsx ; Z = non renseigné |
| `SALARY` | Quantitative arrondie | 71.0 | 69.1 | Déclaratif | 17 899 | 1 620 | Conserver le vide (non déclaré) ; traiter en tranches |
| `PRODUCT_GROUP` | Qualitative (12) | 41.8 | 36.9 | Lié à la clôture ⚠ | — | — | Dimension produit ; exclue du modèle (fuite) |
| `PRODUCT_LINE` | Qualitative (4) | 41.8 | 36.9 | Lié à la clôture ⚠ | — | — | Dimension produit ; exclue du modèle (fuite) |
| `STARTDATE` | Date (mois) | 88.0 | 89.6 | Métier (produit sans échéance) | — | — | Convertir ; usage descriptif |
| `MATURITYDATE` | Date (mois) | 91.6 | 92.5 | Métier (produit sans échéance) | — | — | Convertir ; usage descriptif |
| `AMOUNT` | Quantitative continue | 43.6 | 37.7 | Lié à la clôture ⚠ | 51 236 | 852 | Conserver ; pic au plafond = artefact ; exclue du modèle (fuite) |
| `FIXEDRATE` | Quantitative discrète | 89.5 | 90.1 | Métier (produit sans taux) | 4 299 | 258 | Conserver ; usage descriptif |
| `PRODUCT_STATUS` | Qualitative (7) | 88.0 | 89.6 | Métier (produit sans échéance) | — | — | Usage descriptif ; exclue du modèle (fuite) |
| `PARTYCLASS` | Qualitative (4) | 0.0 | 0.0 | — | — | — | Conserver (segment commercial) |
| `LOB` | Qualitative (6) | 0.0 | 0.0 | — | — | — | Joindre TARGET.xlsx ; redondante avec PARTYCLASS |

**Variables dérivées contrôlées** (grain client) :

| Variable dérivée | Outliers IQR | % | Outliers z-score | Commentaire |
|---|---:|---:|---:|---|
| NB_COMPTES (dérivée) | 45 465 | 14.3 | 5 325 | Distribution très concentrée sur 1 : tout client multi-comptes sort des bornes. Information utile, conservée. |
| ANCIENNETE_CLIENT (dérivée) | 0 | 0.0 | 0 | Aucune valeur aberrante. |
| MOIS_DEPUIS_REVUE (dérivée) | 10 468 | 3.1 | 6 693 | Revues très anciennes : dossiers non revus, information utile. |
