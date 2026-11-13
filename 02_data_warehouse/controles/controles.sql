-- =====================================================================
--  VIGIE · Groupe BI 5 — Contrôles du chargement de l'entrepôt
--
--  À exécuter dans pgAdmin après les jobs Talend (ou après etl.py).
--  Chaque contrôle compare la SOURCE (schéma staging) à la CIBLE (schéma dwh)
--  et renvoie une ligne avec un verdict OK / KO.
--
--  La requête finale (section 4) rassemble tous les verdicts en un seul tableau.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. VOLUMES : la cible contient-elle ce que la source annonce ?
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW dwh.v_controles AS

-- C01 : toutes les lignes du CSV sont arrivées en staging
SELECT 'C01' AS controle, 'Lignes chargées en staging' AS libelle,
       483536::numeric AS attendu, count(*)::numeric AS obtenu
FROM staging.stg_churn

UNION ALL
-- C02 : un compte de la source = une ligne de faits
SELECT 'C02', 'Comptes distincts : source = table de faits',
       (SELECT count(DISTINCT account_no) FROM staging.stg_churn),
       (SELECT count(*) FROM dwh.fait_compte)

UNION ALL
-- C03 : un client de la source = une ligne de dimension
SELECT 'C03', 'Clients distincts : source = dimension client',
       (SELECT count(DISTINCT customer_no) FROM staging.stg_churn),
       (SELECT count(*) FROM dwh.dim_client)

UNION ALL
-- C04 : la somme des lignes fusionnées redonne les lignes source avec compte
SELECT 'C04', 'Lignes source avec compte = somme de nb_lignes_source',
       (SELECT count(*) FROM staging.stg_churn WHERE account_no IS NOT NULL),
       (SELECT sum(nb_lignes_source) FROM dwh.fait_compte)

UNION ALL
-- C05 : les clients sans compte sont bien dans la dimension, sans fait
SELECT 'C05', 'Clients sans compte (nb_comptes = 0)',
       (SELECT count(DISTINCT customer_no) FROM staging.stg_churn WHERE account_no IS NULL),
       (SELECT count(*) FROM dwh.dim_client WHERE nb_comptes = 0)

-- ---------------------------------------------------------------------
-- 2. INDICATEURS : les KPI sont-ils identiques des deux côtés ?
-- ---------------------------------------------------------------------
UNION ALL
-- C06 : nombre de comptes clos
SELECT 'C06', 'Comptes clos : source = table de faits',
       (SELECT count(DISTINCT account_no) FROM staging.stg_churn WHERE account_status = 'Closed'),
       (SELECT sum(est_clos) FROM dwh.fait_compte)

UNION ALL
-- C07 : taux de churn au grain compte (en %)
SELECT 'C07', 'Taux de churn par compte (%)',
       (SELECT round(count(DISTINCT account_no) FILTER (WHERE account_status = 'Closed') * 100.0
                     / count(DISTINCT account_no), 2) FROM staging.stg_churn),
       (SELECT round(avg(est_clos) * 100, 2) FROM dwh.fait_compte)

UNION ALL
-- C08 : clients partis (tous leurs comptes sont clos)
SELECT 'C08', 'Clients en churn : source = dimension client',
       (SELECT count(*) FROM (
            SELECT customer_no FROM staging.stg_churn WHERE account_no IS NOT NULL
            GROUP BY customer_no HAVING bool_and(account_status = 'Closed')) s),
       (SELECT sum(est_churn) FROM dwh.dim_client)

UNION ALL
-- C09 : la première date de clôture a bien été retenue pour chaque compte
SELECT 'C09', 'Comptes dont la date de clôture n''est pas la première (doit valoir 0)',
       0,
       (SELECT count(*) FROM dwh.fait_compte f
        JOIN (SELECT account_no, min(acct_close_date)::integer AS premiere
              FROM staging.stg_churn WHERE acct_close_date IS NOT NULL GROUP BY account_no) s
          ON s.account_no = f.code_compte
        WHERE f.date_cloture_id <> s.premiere)

UNION ALL
-- C10 : somme des soldes (comparaison des montants)
SELECT 'C10', 'Somme des soldes : source dédoublonnée = table de faits',
       (SELECT sum(solde) FROM (SELECT DISTINCT account_no, acct_balance::numeric AS solde
                                FROM staging.stg_churn WHERE account_no IS NOT NULL) s),
       (SELECT sum(solde) FROM dwh.fait_compte)

UNION ALL
-- C11 : série hebdomadaire — total des clôtures
SELECT 'C11', 'Série hebdomadaire : total des clôtures',
       (SELECT sum(est_clos) FROM dwh.fait_compte),
       (SELECT sum(nb_clotures) FROM dwh.v_clotures_hebdo)

-- ---------------------------------------------------------------------
-- 3. INTÉGRITÉ : clés, doublons, cohérence
-- ---------------------------------------------------------------------
UNION ALL
-- C12 : aucun compte en double dans les faits
SELECT 'C12', 'Comptes en double dans les faits (doit valoir 0)',
       0, (SELECT count(*) - count(DISTINCT code_compte) FROM dwh.fait_compte)

UNION ALL
-- C13 : aucun fait sans client
SELECT 'C13', 'Faits sans client dans la dimension (doit valoir 0)',
       0, (SELECT count(*) FROM dwh.fait_compte f
           LEFT JOIN dwh.dim_client c USING (client_id) WHERE c.client_id IS NULL)

UNION ALL
-- C14 : un compte actif n'a pas de date de clôture, un compte clos en a une
SELECT 'C14', 'Incohérences statut / date de clôture (doit valoir 0)',
       0, (SELECT count(*) FROM dwh.fait_compte
           WHERE (est_clos = 0 AND date_cloture_id <> 0) OR (est_clos = 1 AND date_cloture_id = 0))

UNION ALL
-- C15 : toute clôture antérieure à l'ouverture (anomalie de la source) est signalée
--       par ouverture_apres_cloture, et son ancienneté n'est pas calculée
SELECT 'C15', 'Clôtures antérieures à l''ouverture non signalées (doit valoir 0)',
       0, (SELECT count(*) FROM dwh.fait_compte
           WHERE date_ouverture_id <> 0 AND date_cloture_id <> 0 AND date_cloture_id < date_ouverture_id
             AND (NOT ouverture_apres_cloture OR anciennete_compte_jours IS NOT NULL))

UNION ALL
-- C19 : aucune ancienneté de compte négative
SELECT 'C19', 'Anciennetés de compte négatives (doit valoir 0)',
       0, (SELECT count(*) FROM dwh.fait_compte WHERE anciennete_compte_jours < 0)

UNION ALL
-- C16 : nb_comptes de la dimension client = nombre de faits du client
SELECT 'C16', 'Clients dont nb_comptes ne correspond pas aux faits (doit valoir 0)',
       0, (SELECT count(*) FROM dwh.dim_client c
           LEFT JOIN (SELECT client_id, count(*) AS n FROM dwh.fait_compte GROUP BY client_id) f USING (client_id)
           WHERE c.nb_comptes <> coalesce(f.n, 0))

UNION ALL
-- C17 : aucun client n'a à la fois un compte actif et un compte clos
SELECT 'C17', 'Clients à statut mixte actif / clos (doit valoir 0)',
       0, (SELECT count(*) FROM (SELECT client_id FROM dwh.fait_compte
                                 GROUP BY client_id HAVING min(est_clos) <> max(est_clos)) m)

UNION ALL
-- C18 : toutes les dates des faits existent dans le calendrier
SELECT 'C18', 'Dates des faits absentes de dim_date (doit valoir 0)',
       0, (SELECT count(*) FROM dwh.fait_compte f
           LEFT JOIN dwh.dim_date d1 ON d1.date_id = f.date_ouverture_id
           LEFT JOIN dwh.dim_date d2 ON d2.date_id = f.date_cloture_id
           WHERE d1.date_id IS NULL OR d2.date_id IS NULL);

-- ---------------------------------------------------------------------
-- 4. TABLEAU DE BORD DES CONTRÔLES
-- ---------------------------------------------------------------------
SELECT controle, libelle, attendu, obtenu,
       CASE WHEN attendu = obtenu THEN 'OK' ELSE 'KO' END AS verdict
FROM dwh.v_controles
ORDER BY controle;

-- ---------------------------------------------------------------------
-- 5. CONTRÔLES DE RÉPARTITION (à comparer visuellement avec le notebook 01)
-- ---------------------------------------------------------------------
-- Membres « Non renseigné » par dimension : quelle part des faits pointe vers la clé 0 ?
SELECT 'categorie' AS dimension, round(avg((categorie_id = 0)::int) * 100, 1) AS pct_non_renseigne FROM dwh.fait_compte
UNION ALL SELECT 'devise',         round(avg((devise_id = 0)::int) * 100, 1)         FROM dwh.fait_compte
UNION ALL SELECT 'produit',        round(avg((produit_id = 0)::int) * 100, 1)        FROM dwh.fait_compte
UNION ALL SELECT 'motif',          round(avg((motif_id = 0)::int) * 100, 1)          FROM dwh.fait_compte
UNION ALL SELECT 'date_ouverture', round(avg((date_ouverture_id = 0)::int) * 100, 1) FROM dwh.fait_compte
UNION ALL SELECT 'date_cloture',   round(avg((date_cloture_id = 0)::int) * 100, 1)   FROM dwh.fait_compte;

-- Anomalie de la source : comptes clos dont l'ouverture est postérieure à la clôture.
SELECT count(*) FILTER (WHERE est_clos = 1 AND date_ouverture_id <> 0)  AS comptes_clos_avec_date_ouverture,
       count(*) FILTER (WHERE ouverture_apres_cloture)                  AS ouverture_apres_cloture,
       round(count(*) FILTER (WHERE ouverture_apres_cloture) * 100.0
             / count(*) FILTER (WHERE est_clos = 1 AND date_ouverture_id <> 0), 1) AS part_pct
FROM dwh.fait_compte;

-- Les cinq semaines les plus chargées en clôtures (opérations de masse).
SELECT semaine, nb_clotures,
       round(nb_clotures * 100.0 / sum(nb_clotures) OVER (), 1) AS part_pct
FROM dwh.v_clotures_hebdo
ORDER BY nb_clotures DESC
LIMIT 5;
