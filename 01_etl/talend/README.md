# Jobs Talend — spécification de construction

> **État du dossier.** Ce document est le **plan de construction** des jobs. Les jobs eux-mêmes se construisent et
> s'exportent depuis Talend Studio : déposez ici l'archive exportée (`VIGIE_Talend_Jobs.zip`) et une capture de chaque
> job (`captures/J01.png` …). Tant que l'archive n'est pas déposée, le chargement de référence est
> `01_etl/pipeline_python/etl.py`, qui applique exactement les règles ci-dessous.
>
> **Recette commune.** Quel que soit l'outil, `02_data_warehouse/controles/controles.sql` doit renvoyer
> **19 / 19 OK**. C'est ce qui prouve que les jobs Talend chargent la même chose que la référence.

## Vue d'ensemble

| Job | Rôle | Entrée | Sortie | Lignes attendues |
|---|---|---|---|---:|
| `J00_Orchestration` | Enchaîne les jobs, s'arrête au premier échec | — | — | — |
| `J01_Staging` | **Extract** : copie brute des 6 fichiers | CSV + 5 Excel | `staging.stg_*` | 483 536 + 59 |
| `J02_Dim_Referentiels` | Dimensions issues des référentiels | `staging.stg_*` | 6 dimensions | 22 · 23 · 15 · 6 · 13 · 14 |
| `J03_Dim_Client` | Dimension client et variables dérivées | `staging.stg_churn` | `dwh.dim_client` | 363 024 |
| `J04_Fait_Compte` | Table de faits au grain compte | `staging.stg_churn` + dimensions | `dwh.fait_compte` | 410 309 |
| `J05_Controles` | Recette source ↔ entrepôt | `dwh.v_controles` | console / arrêt | 19 |

Le calendrier `dwh.dim_date` est créé par `create_tables.sql` (fonction `generate_series`) : aucun job n'est nécessaire.

## Préparation

1. **PostgreSQL** : créer la base `vigie_dwh` et exécuter `02_data_warehouse/schema/create_tables.sql` dans pgAdmin.
2. **Talend Studio** : créer le projet `VIGIE_BI5`.
3. **Metadata → Db Connections** : créer `PG_VIGIE` (PostgreSQL) et l'utiliser dans tous les composants `tDB*`.
4. **Contexts** : créer le groupe `ctx_vigie` et l'ajouter à chaque job.

| Variable de contexte | Type | Exemple | Usage |
|---|---|---|---|
| `dossier_donnees` | Directory | `C:/projet/data/` | emplacement local des fichiers source |
| `pg_hote` | String | `localhost` | serveur PostgreSQL |
| `pg_port` | String | `5432` | |
| `pg_base` | String | `vigie_dwh` | |
| `pg_utilisateur` | String | `postgres` | |
| `pg_mot_de_passe` | Password | *(vide à l'export)* | **jamais exporté** |
| `date_reference` | Date | `2024-02-19` | date de la photographie = dernier événement de compte |

> ⚠ **Avant l'export** : vider `pg_mot_de_passe` et vérifier que l'archive ne contient ni CSV ni Excel.
> `File → Export items` exporte les jobs, pas les données ; ne cochez pas « Export dependencies » sur le dossier `data/`.

---

## J01_Staging — extraction

Objectif : déposer les fichiers **tels quels** dans le schéma `staging`. Aucune transformation, tout en `String`.

```
tDBConnection ──OnSubjobOk──▶ tFileInputDelimited ──main──▶ tDBOutput (stg_churn)
                         ├──▶ tFileInputExcel (ACCOUNT_CATEGORY) ──▶ tDBOutput (stg_account_category)
                         ├──▶ tFileInputExcel (CLOSURE_REASON)   ──▶ tDBOutput (stg_closure_reason)
                         ├──▶ tFileInputExcel (CURRENCY)         ──▶ tDBOutput (stg_currency)
                         ├──▶ tFileInputExcel (INDUSTRY)         ──▶ tDBOutput (stg_industry)
                         └──▶ tFileInputExcel (TARGET)           ──▶ tDBOutput (stg_target)
                                                                     └──OnSubjobOk──▶ tDBCommit
```

| Composant | Réglages |
|---|---|
| `tFileInputDelimited` | Fichier `context.dossier_donnees + "data_churn.csv"` · séparateur `,` · en-tête `1` · encodage `UTF-8` · schéma : 32 colonnes **String**, toutes « nullable » |
| `tFileInputExcel` ×5 | Fichier `.xlsx` (cocher *Read excel2007 file format*) · feuille 1 · en-tête `1` · 2 colonnes String |
| `tDBOutput` ×6 | Action sur la table : *Truncate table* · action sur les données : *Insert* · *Batch size* 10 000 |

Contrôle immédiat : `stg_churn` contient **483 536** lignes (contrôle C01).

---

## J02_Dim_Referentiels — dimensions de référence

Même motif pour les cinq dimensions : une ligne « Non renseigné » de clé `0`, puis une ligne par code.

```
tFixedFlowInput (clé 0) ───────────────────────────┐
                                                    ├──▶ tUnite ──▶ tDBOutput (dim_xxx)
tDBInput (staging) ──▶ tSortRow ──▶ tMap (clé) ────┘
```

| Dimension | Requête du `tDBInput` | Clé dans le `tMap` | Ligne de clé 0 |
|---|---|---|---|
| `dim_categorie_compte` | `SELECT category_id, description FROM staging.stg_account_category` | `Numeric.sequence("cat", 1, 1)` | `ND` · Non renseigné · famille Non renseigné |
| `dim_devise` | `SELECT currency_code, description FROM staging.stg_currency` | `Numeric.sequence("dev", 1, 1)` | `ND` · Non renseigné |
| `dim_motif_cloture` | `SELECT reason_id, description FROM staging.stg_closure_reason` | `Numeric.sequence("mot", 1, 1)` | `ND` · Sans motif (compte actif ou non saisi) |
| `dim_secteur` | `SELECT industry_code, description FROM staging.stg_industry` | `Numeric.sequence("sec", 1, 1)` | `ND` · Non renseigné |
| `dim_agence` | `SELECT DISTINCT branch_group FROM staging.stg_churn` | `Numeric.sequence("ag", 1, 1)` | `ND` · Non renseigné · masqué |
| `dim_produit` | `SELECT DISTINCT product_group, product_line FROM staging.stg_churn WHERE product_group IS NOT NULL` | `Numeric.sequence("prd", 1, 1)` | Non renseigné · Non renseigné |

Expressions du `tMap` :

* **`dim_categorie_compte.famille`**

  ```java
  row1.description.startsWith("Credit") || row1.description.equals("Financement court terme") ? "Crédits"
  : (row1.description.equals("Autres comptes") || row1.description.equals("Coffres")
     || row1.description.equals("Contentieux")) ? "Autres"
  : "Dépôts"
  ```
* **`dim_agence.libelle`** : `row1.branch_group.equals("AG00") ? "Agences masquées" : "Groupe d'agences " + row1.branch_group.substring(2)`
* **`dim_agence.est_masque`** : `row1.branch_group.equals("AG00")`

---

## J03_Dim_Client — dimension client

```
tDBInput (clients) ──▶ tMap ──▶ tDBOutput (dwh.dim_client)
                        ▲  ▲
tDBInput (comptes par client) ─┘  └── tDBInput (stg_target : libellé de la ligne métier)
```

**`tDBInput` principal** — une ligne par client (les attributs client sont constants d'une ligne à l'autre) :

```sql
SELECT DISTINCT customer_no, nationality_region, residence_region, marital_status, birth_period,
       cust_opening_date, nature_client, partyclass, lob, score_kyc, completed_file,
       last_review_date, next__review_date, salary
FROM staging.stg_churn
ORDER BY customer_no
```

**`tDBInput` lookup « comptes par client »** — nombre de comptes et churn du client :

```sql
SELECT customer_no,
       count(DISTINCT account_no)                    AS nb_comptes,
       bool_and(account_status = 'Closed')::int      AS est_churn
FROM staging.stg_churn
WHERE account_no IS NOT NULL
GROUP BY customer_no
```

Jointure du `tMap` : *Left Outer Join* sur `customer_no` (les clients sans compte doivent passer).

| Colonne cible | Expression `tMap` |
|---|---|
| `client_id` | `Numeric.sequence("client", 1, 1)` |
| `code_client` | `row1.customer_no` |
| `statut_marital` | `"C".equals(row1.marital_status) ? "Célibataire" : "M".equals(row1.marital_status) ? "Marié(e)" : "D".equals(row1.marital_status) ? "Divorcé(e)" : "V".equals(row1.marital_status) ? "Veuf / veuve" : "Non renseigné"` |
| `tranche_naissance` | `row1.birth_period == null ? null : (int) Double.parseDouble(row1.birth_period)` |
| `age` | `row1.birth_period == null ? null : TalendDate.getPartOfDate("YEAR", context.date_reference) - ((int) Double.parseDouble(row1.birth_period) + 2)` |
| `tranche_age` | voir la règle ci-dessous |
| `segment` | `row1.partyclass` |
| `ligne_metier` | `cible.description == null ? "Non renseigné" : cible.description` |
| `date_entree_relation` | `row1.cust_opening_date == null ? null : TalendDate.parseDate("yyyyMMdd", row1.cust_opening_date)` |
| `anciennete_annees` | `Var.date_entree == null ? null : TalendDate.diffDate(context.date_reference, Var.date_entree, "dd") / 365.25` |
| `revenu_declare` | `row1.salary == null ? null : new java.math.BigDecimal(row1.salary)` |
| `nb_comptes` | `comptes.nb_comptes == null ? 0 : comptes.nb_comptes` |
| `score_kyc` | `row1.score_kyc == null ? "Non renseigné" : row1.score_kyc` |
| `dossier_complet` | `"YES".equals(row1.completed_file)` |
| `mois_depuis_revue` | `Var.date_revue == null ? null : TalendDate.diffDate(context.date_reference, Var.date_revue, "dd") / 30.4375` |
| `revue_en_retard` | `Var.date_prochaine == null ? null : Var.date_prochaine.before(context.date_reference)` |
| `est_churn` | `comptes.est_churn` *(reste `null` pour un client sans compte)* |

**Tranches** (à placer dans les variables `Var` du `tMap`) :

| Variable | Bornes | Libellés |
|---|---|---|
| `tranche_age` | âge ≤ 17 · 18–24 · 25–34 · 35–44 · 45–54 · 55–64 · ≥ 65 · vide | `< 18 ans` · `18–24 ans` · `25–34 ans` · `35–44 ans` · `45–54 ans` · `55–64 ans` · `65 ans et +` · `Non renseigné` |
| `tranche_anciennete` | ≤ 2 · ]2 ; 5] · ]5 ; 10] · ]10 ; 15] · > 15 · vide | `< 2 ans` · `2–5 ans` · `5–10 ans` · `10–15 ans` · `15 ans et +` · `Non renseigné` |

Contrôles : **363 024** lignes (C03) dont **43 984** avec `nb_comptes = 0` (C05) et **117 345** avec `est_churn = 1` (C08).

---

## J04_Fait_Compte — table de faits

```
tDBInput (lignes avec compte) ──▶ tAggregateRow ──▶ tMap (8 lookups) ──▶ tDBOutput (dwh.fait_compte)
                                   (grain compte)        │
                                                         └──rejets──▶ tLogRow (« compte sans client »)
```

**Passage au grain compte.** Le plus simple et le plus sûr est de le faire dans la requête du `tDBInput` :

```sql
SELECT account_no,
       min(customer_no)                           AS customer_no,
       min(account_status)                        AS account_status,
       min(acct_opening_date)                     AS acct_opening_date,
       min(acct_close_date)                       AS acct_close_date,     -- PREMIÈRE clôture
       (array_agg(closure_reason ORDER BY acct_close_date, closure_reason))[1] AS closure_reason,
       min(account_category)                      AS account_category,
       min(currency)                              AS currency,
       min(acct_balance)                          AS acct_balance,
       min(product_group)                         AS product_group,
       min(product_line)                          AS product_line,
       min(amount)                                AS amount,
       max(fixedrate::numeric)                    AS fixedrate,           -- le plus élevé si plusieurs
       min(product_status)                        AS product_status,
       min(branch_group)                          AS branch_group,
       min(industry)                              AS industry,
       count(*)                                   AS nb_lignes_source
FROM staging.stg_churn
WHERE account_no IS NOT NULL
GROUP BY account_no
```

> Variante 100 % composants : `tSortRow` (`account_no`, `acct_close_date` croissants) → `tAggregateRow`
> (group by `account_no` ; `acct_close_date` : *min* ; les autres colonnes : *first* ; `nb_lignes_source` : *count*).
> Les deux variantes donnent les mêmes 410 309 lignes.

**Lookups du `tMap`** (tous en *Left Outer Join*, modèle de correspondance *Unique match*) :

| Lookup | Clé de jointure | Clé rapportée | Si absent |
|---|---|---|---|
| `dwh.dim_client` | `customer_no = code_client` | `client_id` | **rejet** (ne doit jamais arriver : C13) |
| `dwh.dim_agence` | `branch_group = code_groupe` | `agence_id` | `0` |
| `dwh.dim_secteur` | `industry = code_secteur` | `secteur_id` | `0` |
| `dwh.dim_categorie_compte` | `account_category = code_categorie` | `categorie_id` | `0` |
| `dwh.dim_devise` | `currency = code_devise` | `devise_id` | `0` |
| `dwh.dim_motif_cloture` | `closure_reason = code_motif` | `motif_id` | `0` |
| `dwh.dim_produit` | `product_group` et `product_line` | `produit_id` | `0` |

Pour chaque clé : `dim.xxx_id == null ? 0 : dim.xxx_id`.

| Colonne cible | Expression `tMap` |
|---|---|
| `compte_id` | `Numeric.sequence("compte", 1, 1)` |
| `date_ouverture_id` | `row1.acct_opening_date == null ? 0 : Integer.parseInt(row1.acct_opening_date)` |
| `date_cloture_id` | `row1.acct_close_date == null ? 0 : Integer.parseInt(row1.acct_close_date)` |
| `est_clos` | `"Closed".equals(row1.account_status) ? 1 : 0` |
| `solde` | `row1.acct_balance == null ? null : new java.math.BigDecimal(row1.acct_balance)` |
| `est_debiteur` | `Var.solde == null ? null : Var.solde.signum() < 0` |
| `montant_produit` | `row1.amount == null ? null : new java.math.BigDecimal(row1.amount)` |
| `taux_fixe` | `row1.fixedrate` *(déjà numérique en sortie de la requête)* |
| `ouverture_apres_cloture` | `Var.d_ouv != null && Var.d_clo != null && Var.d_clo.before(Var.d_ouv)` |
| `anciennete_compte_jours` | `Var.d_ouv == null \|\| Var.ouverture_apres_cloture ? null : (int) TalendDate.diffDate(Var.d_clo == null ? context.date_reference : Var.d_clo, Var.d_ouv, "dd")` |
| `statut_produit` | `row1.product_status` |
| `nb_lignes_source` | `row1.nb_lignes_source` |

`tDBOutput` : *Insert*, *Batch size* 10 000, **après** `J02` et `J03` (les clés étrangères doivent exister).

Contrôles : **410 309** lignes (C02), **148 215** comptes clos (C06), somme de `nb_lignes_source` = **439 552** (C04).

---

## J05_Controles — recette

```
tDBRow (controles.sql : création de la vue) ──OnComponentOk──▶ tDBInput (dwh.v_controles)
        ──▶ tMap (verdict) ──▶ tLogRow (tableau)
                          └──filtre « KO »──▶ tDie (« Contrôle en échec »)
```

* `tDBInput` : `SELECT controle, libelle, attendu, obtenu FROM dwh.v_controles ORDER BY controle`
* `tMap` : `verdict = row1.attendu.compareTo(row1.obtenu) == 0 ? "OK" : "KO"`
* Une sortie filtrée `"KO".equals(verdict)` reliée à un `tDie` : le job échoue si un seul contrôle est faux.

## J00_Orchestration

```
tPrejob ──▶ tDBConnection
tRunJob(J01) ─OnSubjobOk▶ tRunJob(J02) ─OnSubjobOk▶ tRunJob(J03) ─OnSubjobOk▶ tRunJob(J04) ─OnSubjobOk▶ tRunJob(J05)
tPostjob ──▶ tDBClose
```

Chaque `tRunJob` : cocher *Die on child error* et *Transmit whole context*.

---

## Correspondance Talend ↔ pipeline Python

| Étape | Talend | Python (`etl.py`) |
|---|---|---|
| Lecture CSV / Excel | `tFileInputDelimited`, `tFileInputExcel` | `donnees.charger_brut()`, `charger_referentiels()` |
| Dépôt en staging | `tDBOutput` (truncate + insert) | `copier()` (`COPY`) |
| Typage des dates | `TalendDate.parseDate("yyyyMMdd", …)` | `donnees.typer()` |
| Grain compte | `tAggregateRow` / `GROUP BY account_no` | `donnees.grain_compte()` |
| Grain client | `tDBInput DISTINCT` + lookup agrégé | `donnees.grain_client()` |
| Clés de substitution | `Numeric.sequence` | `range(1, n + 1)` |
| Membre « Non renseigné » | `tFixedFlowInput` + `tUnite` | `dimension()` |
| Jointures | lookups du `tMap` | `map()` / `merge()` |
| Recette | `J05_Controles` | `controles.sql` |

Les clés de substitution peuvent différer d'un outil à l'autre (elles dépendent de l'ordre d'insertion) ; les
**volumes et les KPI, eux, doivent être identiques** : c'est ce que vérifient les 19 contrôles.

## Liste de vérification avant de déposer l'export

- [ ] `J00_Orchestration` s'exécute de bout en bout sans erreur.
- [ ] `controles.sql` renvoie 19 / 19 OK dans pgAdmin.
- [ ] Le mot de passe du contexte est vide.
- [ ] L'archive ne contient aucun `.csv` ni `.xlsx`.
- [ ] Une capture de chaque job est déposée dans `captures/`.
