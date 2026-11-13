-- =====================================================================
--  VIGIE · Groupe BI 5 — BONUS : historisation SCD de type 2
--
--  Objectif : garder l'historique des attributs d'un client qui changent
--  dans le temps (score KYC, segment, dossier complet), au lieu d'écraser
--  l'ancienne valeur.
--
--  Principe : une ligne par VERSION du client, avec
--      date_debut_validite / date_fin_validite / est_version_courante.
--
--  Ce script est autonome et ré-exécutable. Il travaille dans le schéma
--  dwh_scd2 et se termine par une démonstration sur des clients FICTIFS.
-- =====================================================================

DROP SCHEMA IF EXISTS dwh_scd2 CASCADE;
CREATE SCHEMA dwh_scd2;

-- 1. La dimension historisée ------------------------------------------------
CREATE TABLE dwh_scd2.dim_client_historise (
    client_sk             bigserial    PRIMARY KEY,          -- clé de substitution : une par VERSION
    code_client           varchar(10)  NOT NULL,             -- clé métier : une par CLIENT
    -- attributs suivis (type 2 : tout changement crée une nouvelle version)
    score_kyc             varchar(15)  NOT NULL,
    segment               varchar(20)  NOT NULL,
    dossier_complet       boolean      NOT NULL,
    -- colonnes techniques SCD2
    date_debut_validite   date         NOT NULL,
    date_fin_validite     date         NOT NULL DEFAULT DATE '9999-12-31',
    est_version_courante  boolean      NOT NULL DEFAULT true,
    CHECK (date_fin_validite >= date_debut_validite)
);
-- Un client n'a qu'une seule version courante.
CREATE UNIQUE INDEX ux_client_version_courante
    ON dwh_scd2.dim_client_historise (code_client) WHERE est_version_courante;

-- 2. La zone d'arrivée : l'état des clients à la date du chargement --------------
CREATE TABLE dwh_scd2.stg_client (
    code_client      varchar(10) PRIMARY KEY,
    score_kyc        varchar(15) NOT NULL,
    segment          varchar(20) NOT NULL,
    dossier_complet  boolean     NOT NULL
);

-- 3. La procédure de chargement SCD2 ----------------------------------------
CREATE OR REPLACE PROCEDURE dwh_scd2.charger_dim_client(p_date_chargement date)
LANGUAGE plpgsql AS $$
BEGIN
    -- a) Fermer la version courante des clients dont un attribut suivi a changé.
    UPDATE dwh_scd2.dim_client_historise d
    SET date_fin_validite    = p_date_chargement - 1,
        est_version_courante = false
    FROM dwh_scd2.stg_client s
    WHERE d.code_client = s.code_client
      AND d.est_version_courante
      AND (d.score_kyc, d.segment, d.dossier_complet)
          IS DISTINCT FROM (s.score_kyc, s.segment, s.dossier_complet);

    -- b) Insérer une version courante pour : les nouveaux clients, et ceux fermés en a).
    INSERT INTO dwh_scd2.dim_client_historise
        (code_client, score_kyc, segment, dossier_complet, date_debut_validite)
    SELECT s.code_client, s.score_kyc, s.segment, s.dossier_complet, p_date_chargement
    FROM dwh_scd2.stg_client s
    LEFT JOIN dwh_scd2.dim_client_historise d
           ON d.code_client = s.code_client AND d.est_version_courante
    WHERE d.code_client IS NULL;
END;
$$;

-- 4. Démonstration sur des clients FICTIFS ------------------------------------
-- Chargement initial : trois clients.
INSERT INTO dwh_scd2.stg_client VALUES
    ('FICTIF01', 'LR', 'Retail',  false),
    ('FICTIF02', 'MR', 'Retail',  true),
    ('FICTIF03', 'LR', 'Premium', true);
CALL dwh_scd2.charger_dim_client(DATE '2024-01-01');

-- Chargement suivant : FICTIF01 complète son dossier, FICTIF02 change de score KYC,
-- FICTIF03 ne change pas, FICTIF04 est un nouveau client.
TRUNCATE dwh_scd2.stg_client;
INSERT INTO dwh_scd2.stg_client VALUES
    ('FICTIF01', 'LR', 'Retail',  true),
    ('FICTIF02', 'H1', 'Retail',  true),
    ('FICTIF03', 'LR', 'Premium', true),
    ('FICTIF04', 'LR', 'Retail',  false);
CALL dwh_scd2.charger_dim_client(DATE '2024-02-01');

-- Résultat attendu : 6 lignes.
--   FICTIF01 : 2 versions (dossier incomplet jusqu'au 31/01, complet ensuite)
--   FICTIF02 : 2 versions (MR jusqu'au 31/01, H1 ensuite)
--   FICTIF03 : 1 version  (inchangé : aucune ligne ajoutée)
--   FICTIF04 : 1 version  (nouveau client)
SELECT code_client, score_kyc, segment, dossier_complet,
       date_debut_validite, date_fin_validite, est_version_courante
FROM dwh_scd2.dim_client_historise
ORDER BY code_client, date_debut_validite;

-- Retrouver l'état d'un client à une date passée (« as of ») :
SELECT code_client, score_kyc, dossier_complet
FROM dwh_scd2.dim_client_historise
WHERE DATE '2024-01-15' BETWEEN date_debut_validite AND date_fin_validite
ORDER BY code_client;
