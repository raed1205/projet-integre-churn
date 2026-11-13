-- =====================================================================
--  VIGIE · Groupe BI 5 — Entrepôt de données « churn »
--  Projet Intégré, ESPRIT School of Business (L3 Business Computing BI)
--
--  Modèle en étoile — PostgreSQL 14+
--  À exécuter dans pgAdmin (Query Tool) sur la base  vigie_dwh.
--
--  Deux schémas :
--    staging : copie brute des fichiers source (tout en texte)
--    dwh     : modèle en étoile (1 table de faits, 8 dimensions)
--
--  GRAIN DE LA TABLE DE FAITS : une ligne = un compte (ACCOUNT_NO).
--  Le script est ré-exécutable : il supprime puis recrée les deux schémas.
-- =====================================================================

DROP SCHEMA IF EXISTS dwh CASCADE;
DROP SCHEMA IF EXISTS staging CASCADE;
CREATE SCHEMA staging;
CREATE SCHEMA dwh;

-- ---------------------------------------------------------------------
-- 1. STAGING — zone de dépôt : les fichiers tels qu'ils sont fournis
-- ---------------------------------------------------------------------
CREATE TABLE staging.stg_churn (
    customer_no         text,
    account_no          text,
    nationality_region  text,
    residence_region    text,
    marital_status      text,
    cust_opening_date   text,
    birth_period        text,
    nature_client       text,
    branch_group        text,
    score_kyc           text,
    completed_file      text,
    last_review_date    text,
    next__review_date   text,
    account_status      text,
    acct_opening_date   text,
    account_category    text,
    account_type_desc   text,
    currency            text,
    acct_close_date     text,
    closure_reason      text,
    acct_balance        text,
    industry            text,
    salary              text,
    product_group       text,
    product_line        text,
    startdate           text,
    maturitydate        text,
    amount              text,
    fixedrate           text,
    product_status      text,
    partyclass          text,
    lob                 text
);
COMMENT ON TABLE staging.stg_churn IS 'Copie brute de data_churn.csv (483 536 lignes). Aucune transformation.';

CREATE TABLE staging.stg_account_category (category_id text, description text);
CREATE TABLE staging.stg_closure_reason   (reason_id text, description text);
CREATE TABLE staging.stg_currency         (currency_code text, description text);
CREATE TABLE staging.stg_industry         (industry_code text, description text);
CREATE TABLE staging.stg_target           (target_code text, description text);

-- ---------------------------------------------------------------------
-- 2. DIMENSIONS
--    Convention : la clé 0 de chaque dimension est le membre « Non renseigné ».
--    Une valeur vide dans la source pointe vers 0 : aucun fait n'est orphelin.
-- ---------------------------------------------------------------------

-- Dimension temps : le calendrier n'est pas fourni, il est construit ici.
CREATE TABLE dwh.dim_date (
    date_id        integer     PRIMARY KEY,           -- AAAAMMJJ ; 0 = date inconnue
    date_complete  date        UNIQUE,
    annee          smallint,
    trimestre      smallint,
    mois           smallint,
    nom_mois       varchar(12),
    annee_mois     char(7),                           -- 2023-07
    semaine_iso    smallint,
    lundi_semaine  date,                              -- début de la semaine (grain des séries)
    jour_semaine   smallint,                          -- 1 = lundi … 7 = dimanche
    nom_jour       varchar(10)
);

INSERT INTO dwh.dim_date (date_id) VALUES (0);

INSERT INTO dwh.dim_date
SELECT to_char(d, 'YYYYMMDD')::integer,
       d::date,
       extract(year    FROM d)::smallint,
       extract(quarter FROM d)::smallint,
       extract(month   FROM d)::smallint,
       (ARRAY['janvier','février','mars','avril','mai','juin','juillet','août',
              'septembre','octobre','novembre','décembre'])[extract(month FROM d)::int],
       to_char(d, 'YYYY-MM'),
       extract(week FROM d)::smallint,
       date_trunc('week', d)::date,
       extract(isodow FROM d)::smallint,
       (ARRAY['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche'])[extract(isodow FROM d)::int]
FROM generate_series(DATE '1978-01-01', DATE '2031-12-31', INTERVAL '1 day') AS d;

CREATE TABLE dwh.dim_agence (
    agence_id    smallint    PRIMARY KEY,
    code_groupe  varchar(4)  NOT NULL UNIQUE,          -- AG00 … AG20
    libelle      varchar(40) NOT NULL,
    est_masque   boolean     NOT NULL DEFAULT false    -- AG00 = agences masquées
);

CREATE TABLE dwh.dim_secteur (
    secteur_id    smallint     PRIMARY KEY,
    code_secteur  varchar(2)   NOT NULL UNIQUE,        -- A … Z (INDUSTRY.xlsx)
    libelle       varchar(60)  NOT NULL
);

CREATE TABLE dwh.dim_categorie_compte (
    categorie_id    smallint     PRIMARY KEY,
    code_categorie  varchar(6)   NOT NULL UNIQUE,      -- CAT01 … CAT14 (ACCOUNT_CATEGORY.xlsx)
    libelle         varchar(40)  NOT NULL,
    famille         varchar(15)  NOT NULL              -- Dépôts / Crédits / Autres
);

CREATE TABLE dwh.dim_devise (
    devise_id    smallint     PRIMARY KEY,
    code_devise  varchar(3)   NOT NULL UNIQUE,         -- CURRENCY.xlsx
    libelle      varchar(40)  NOT NULL
);

CREATE TABLE dwh.dim_motif_cloture (
    motif_id    smallint     PRIMARY KEY,
    code_motif  varchar(6)   NOT NULL UNIQUE,          -- RSN01 … RSN12 (CLOSURE_REASON.xlsx)
    libelle     varchar(40)  NOT NULL
);

CREATE TABLE dwh.dim_produit (
    produit_id      smallint     PRIMARY KEY,
    groupe_produit  varchar(30)  NOT NULL,
    ligne_produit   varchar(20)  NOT NULL,
    UNIQUE (groupe_produit, ligne_produit)
);

CREATE TABLE dwh.dim_client (
    client_id             integer      PRIMARY KEY,
    code_client           varchar(10)  NOT NULL UNIQUE,   -- CUSTOMER_NO (identifiant aléatoire)
    -- profil
    zone_nationalite      varchar(15)  NOT NULL,
    zone_residence        varchar(15)  NOT NULL,
    statut_marital        varchar(15)  NOT NULL,          -- Célibataire, Marié(e), … , Non renseigné
    tranche_naissance     smallint,                       -- début de la tranche de 5 ans
    age                   smallint,                       -- milieu de tranche, à la date de référence
    tranche_age           varchar(15)  NOT NULL,
    -- relation commerciale
    nature_client         varchar(5)   NOT NULL,
    segment               varchar(20)  NOT NULL,          -- PARTYCLASS
    ligne_metier          varchar(20)  NOT NULL,          -- libellé TARGET.xlsx
    date_entree_relation  date,
    anciennete_annees     numeric(5,2),
    tranche_anciennete    varchar(15)  NOT NULL,
    revenu_declare        numeric(10,2),
    nb_comptes            smallint     NOT NULL DEFAULT 0,
    -- conformité
    score_kyc             varchar(15)  NOT NULL,
    dossier_complet       boolean      NOT NULL,
    date_derniere_revue   date,
    date_prochaine_revue  date,
    mois_depuis_revue     numeric(6,1),
    revue_en_retard       boolean,
    -- churn au grain client : tous les comptes sont clos (NULL = client sans compte)
    est_churn             smallint     CHECK (est_churn IN (0, 1))
);
COMMENT ON TABLE dwh.dim_client IS 'Un client par ligne (363 024). Les 43 984 clients sans compte y figurent avec nb_comptes = 0.';

-- ---------------------------------------------------------------------
-- 3. TABLE DE FAITS — grain : 1 ligne = 1 compte
-- ---------------------------------------------------------------------
CREATE TABLE dwh.fait_compte (
    compte_id               integer      PRIMARY KEY,
    code_compte             varchar(10)  NOT NULL UNIQUE,   -- ACCOUNT_NO (dimension dégénérée)
    -- clés étrangères
    client_id               integer      NOT NULL REFERENCES dwh.dim_client (client_id),
    agence_id               smallint     NOT NULL REFERENCES dwh.dim_agence (agence_id),
    secteur_id              smallint     NOT NULL REFERENCES dwh.dim_secteur (secteur_id),
    categorie_id            smallint     NOT NULL REFERENCES dwh.dim_categorie_compte (categorie_id),
    devise_id               smallint     NOT NULL REFERENCES dwh.dim_devise (devise_id),
    motif_id                smallint     NOT NULL REFERENCES dwh.dim_motif_cloture (motif_id),
    produit_id              smallint     NOT NULL REFERENCES dwh.dim_produit (produit_id),
    date_ouverture_id       integer      NOT NULL REFERENCES dwh.dim_date (date_id),
    date_cloture_id         integer      NOT NULL REFERENCES dwh.dim_date (date_id),
    -- mesures
    est_clos                smallint     NOT NULL CHECK (est_clos IN (0, 1)),   -- la cible : 1 = churn
    solde                   numeric(14,2),
    est_debiteur            boolean,                        -- solde < 0
    montant_produit         numeric(16,2),
    taux_fixe               numeric(5,2),
    anciennete_compte_jours integer,                        -- jusqu'à la clôture, sinon jusqu'à la date de référence ;
                                                            -- NULL si les dates sont incohérentes
    ouverture_apres_cloture boolean      NOT NULL DEFAULT false,  -- anomalie source : ouverture postérieure à la clôture
    -- attributs descriptifs et traçabilité
    statut_produit          varchar(20),
    nb_lignes_source        smallint     NOT NULL           -- lignes du CSV fusionnées dans ce compte
);
COMMENT ON TABLE dwh.fait_compte IS 'Grain : un compte (410 309). Si plusieurs dates de clôture en source, la première est retenue.';

CREATE INDEX ix_fait_client        ON dwh.fait_compte (client_id);
CREATE INDEX ix_fait_date_cloture  ON dwh.fait_compte (date_cloture_id);
CREATE INDEX ix_fait_categorie     ON dwh.fait_compte (categorie_id);
CREATE INDEX ix_fait_agence        ON dwh.fait_compte (agence_id);

-- ---------------------------------------------------------------------
-- 4. VUES ANALYTIQUES (lues par Power BI et par les contrôles)
-- ---------------------------------------------------------------------

-- KPI globaux : une seule ligne.
CREATE VIEW dwh.v_kpi_global AS
SELECT
    (SELECT count(*) FROM dwh.fait_compte)                                   AS nb_comptes,
    (SELECT sum(est_clos) FROM dwh.fait_compte)                              AS nb_comptes_clos,
    (SELECT round(avg(est_clos) * 100, 2) FROM dwh.fait_compte)              AS taux_churn_comptes_pct,
    (SELECT count(*) FROM dwh.dim_client)                                    AS nb_clients,
    (SELECT count(*) FROM dwh.dim_client WHERE nb_comptes > 0)               AS nb_clients_avec_compte,
    (SELECT sum(est_churn) FROM dwh.dim_client)                              AS nb_clients_churn,
    (SELECT round(avg(est_churn) * 100, 2) FROM dwh.dim_client)              AS taux_churn_clients_pct,
    (SELECT round(sum(est_churn) * 100.0 / count(*), 2) FROM dwh.dim_client) AS taux_churn_tous_clients_pct;

-- Série hebdomadaire des clôtures, semaines à zéro incluses (KPI de la phase 4).
CREATE VIEW dwh.v_clotures_hebdo AS
WITH bornes AS (
    SELECT min(d.date_complete) AS debut, max(d.date_complete) AS fin
    FROM dwh.fait_compte f JOIN dwh.dim_date d ON d.date_id = f.date_cloture_id
    WHERE f.est_clos = 1
),
semaines AS (
    SELECT generate_series(debut, fin, INTERVAL '7 days')::date AS semaine FROM bornes
)
SELECT s.semaine,
       count(f.compte_id) AS nb_clotures
FROM semaines s
LEFT JOIN dwh.dim_date d    ON d.date_complete = s.semaine
LEFT JOIN dwh.fait_compte f ON f.date_cloture_id = d.date_id AND f.est_clos = 1
GROUP BY s.semaine
ORDER BY s.semaine;

-- Churn par segment client (grain client).
CREATE VIEW dwh.v_churn_segment_client AS
SELECT segment, tranche_age, tranche_anciennete, score_kyc, dossier_complet,
       count(*)                       AS nb_clients,
       sum(est_churn)                 AS nb_churn,
       round(avg(est_churn) * 100, 2) AS taux_churn_pct
FROM dwh.dim_client
WHERE est_churn IS NOT NULL
GROUP BY segment, tranche_age, tranche_anciennete, score_kyc, dossier_complet;
