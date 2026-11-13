-- =====================================================================
--  VIGIE · Group BI 5 — "churn" data warehouse
--  Integrated Project, ESPRIT School of Business (Business Computing BI)
--
--  Star schema — PostgreSQL 14+
--  Run in pgAdmin (Query Tool) on the  vigie_dwh  database.
--
--  Two schemas:
--    staging : raw copy of the source files (everything as text)
--    dwh     : star schema (1 fact table, 8 dimensions)
--
--  GRAIN OF THE FACT TABLE: one row = one account (ACCOUNT_NO).
--  The script can be re-run: it drops and recreates both schemas.
-- =====================================================================

DROP SCHEMA IF EXISTS dwh CASCADE;
DROP SCHEMA IF EXISTS staging CASCADE;
CREATE SCHEMA staging;
CREATE SCHEMA dwh;

-- ---------------------------------------------------------------------
-- 1. STAGING — landing zone: the files exactly as they were provided
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
COMMENT ON TABLE staging.stg_churn IS 'Raw copy of data_churn.csv (483,536 rows). No transformation.';

CREATE TABLE staging.stg_account_category (category_id text, description text);
CREATE TABLE staging.stg_closure_reason   (reason_id text, description text);
CREATE TABLE staging.stg_currency         (currency_code text, description text);
CREATE TABLE staging.stg_industry         (industry_code text, description text);
CREATE TABLE staging.stg_target           (target_code text, description text);

-- ---------------------------------------------------------------------
-- 2. DIMENSIONS
--    Convention: key 0 of every dimension is the "Not provided" member.
--    A blank value in the source points to 0: no fact is ever orphaned.
-- ---------------------------------------------------------------------

-- Time dimension: the calendar is not provided, it is built here.
CREATE TABLE dwh.dim_date (
    date_id      integer     PRIMARY KEY,           -- YYYYMMDD ; 0 = unknown date
    full_date    date        UNIQUE,
    year         smallint,
    quarter      smallint,
    month        smallint,
    month_name   varchar(12),
    year_month   char(7),                           -- 2023-07
    iso_week     smallint,
    week_start   date,                              -- Monday of the week (grain of the series)
    day_of_week  smallint,                          -- 1 = Monday … 7 = Sunday
    day_name     varchar(10)
);

INSERT INTO dwh.dim_date (date_id) VALUES (0);

INSERT INTO dwh.dim_date
SELECT to_char(d, 'YYYYMMDD')::integer,
       d::date,
       extract(year    FROM d)::smallint,
       extract(quarter FROM d)::smallint,
       extract(month   FROM d)::smallint,
       (ARRAY['January','February','March','April','May','June','July','August',
              'September','October','November','December'])[extract(month FROM d)::int],
       to_char(d, 'YYYY-MM'),
       extract(week FROM d)::smallint,
       date_trunc('week', d)::date,
       extract(isodow FROM d)::smallint,
       (ARRAY['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])[extract(isodow FROM d)::int]
FROM generate_series(DATE '1978-01-01', DATE '2031-12-31', INTERVAL '1 day') AS d;

CREATE TABLE dwh.dim_branch (
    branch_id   smallint    PRIMARY KEY,
    group_code  varchar(4)  NOT NULL UNIQUE,          -- AG00 … AG20
    label       varchar(40) NOT NULL,
    is_masked   boolean     NOT NULL DEFAULT false    -- AG00 = masked branches
);

CREATE TABLE dwh.dim_industry (
    industry_id    smallint     PRIMARY KEY,
    industry_code  varchar(2)   NOT NULL UNIQUE,      -- A … Z (INDUSTRY.xlsx)
    label          varchar(60)  NOT NULL
);

CREATE TABLE dwh.dim_account_category (
    category_id    smallint     PRIMARY KEY,
    category_code  varchar(6)   NOT NULL UNIQUE,      -- CAT01 … CAT14 (ACCOUNT_CATEGORY.xlsx)
    label          varchar(40)  NOT NULL,
    family         varchar(15)  NOT NULL              -- Deposits / Loans / Other
);

CREATE TABLE dwh.dim_currency (
    currency_id    smallint     PRIMARY KEY,
    currency_code  varchar(3)   NOT NULL UNIQUE,      -- CURRENCY.xlsx
    label          varchar(40)  NOT NULL
);

CREATE TABLE dwh.dim_closure_reason (
    reason_id    smallint     PRIMARY KEY,
    reason_code  varchar(6)   NOT NULL UNIQUE,        -- RSN01 … RSN12 (CLOSURE_REASON.xlsx)
    label        varchar(50)  NOT NULL
);

CREATE TABLE dwh.dim_product (
    product_id     smallint     PRIMARY KEY,
    product_group  varchar(30)  NOT NULL,
    product_line   varchar(20)  NOT NULL,
    UNIQUE (product_group, product_line)
);

CREATE TABLE dwh.dim_customer (
    customer_id              integer      PRIMARY KEY,
    customer_code            varchar(10)  NOT NULL UNIQUE,   -- CUSTOMER_NO (random identifier)
    -- profile
    nationality_zone         varchar(15)  NOT NULL,
    residence_zone           varchar(15)  NOT NULL,
    marital_status           varchar(15)  NOT NULL,          -- Single, Married, … , Not provided
    birth_period             smallint,                       -- start of the 5-year band
    age                      smallint,                       -- middle of the band, at the reference date
    age_band                 varchar(20)  NOT NULL,
    -- commercial relationship
    customer_type            varchar(5)   NOT NULL,          -- NATURE_CLIENT
    segment                  varchar(20)  NOT NULL,          -- PARTYCLASS
    line_of_business         varchar(20)  NOT NULL,          -- label from TARGET.xlsx
    relationship_start_date  date,
    tenure_years             numeric(5,2),
    tenure_band              varchar(20)  NOT NULL,
    declared_income          numeric(10,2),
    n_accounts               smallint     NOT NULL DEFAULT 0,
    -- compliance
    kyc_score                varchar(15)  NOT NULL,
    file_complete            boolean      NOT NULL,
    last_review_date         date,
    next_review_date         date,
    months_since_review      numeric(6,1),
    review_overdue           boolean,
    -- churn at customer grain: all accounts are closed (NULL = customer with no account)
    is_churned               smallint     CHECK (is_churned IN (0, 1))
);
COMMENT ON TABLE dwh.dim_customer IS 'One customer per row (363,024). The 43,984 customers with no account are included with n_accounts = 0.';

-- ---------------------------------------------------------------------
-- 3. FACT TABLE — grain: 1 row = 1 account
-- ---------------------------------------------------------------------
CREATE TABLE dwh.fact_account (
    account_id            integer      PRIMARY KEY,
    account_code          varchar(10)  NOT NULL UNIQUE,   -- ACCOUNT_NO (degenerate dimension)
    -- foreign keys
    customer_id           integer      NOT NULL REFERENCES dwh.dim_customer (customer_id),
    branch_id             smallint     NOT NULL REFERENCES dwh.dim_branch (branch_id),
    industry_id           smallint     NOT NULL REFERENCES dwh.dim_industry (industry_id),
    category_id           smallint     NOT NULL REFERENCES dwh.dim_account_category (category_id),
    currency_id           smallint     NOT NULL REFERENCES dwh.dim_currency (currency_id),
    reason_id             smallint     NOT NULL REFERENCES dwh.dim_closure_reason (reason_id),
    product_id            smallint     NOT NULL REFERENCES dwh.dim_product (product_id),
    opening_date_id       integer      NOT NULL REFERENCES dwh.dim_date (date_id),
    closing_date_id       integer      NOT NULL REFERENCES dwh.dim_date (date_id),
    -- measures
    is_closed             smallint     NOT NULL CHECK (is_closed IN (0, 1)),   -- the target: 1 = churn
    balance               numeric(14,2),
    is_overdrawn          boolean,                        -- balance < 0
    product_amount        numeric(16,2),
    fixed_rate            numeric(5,2),
    account_age_days      integer,                        -- up to the closing, otherwise up to the reference date;
                                                          -- NULL when the dates are inconsistent
    opened_after_closing  boolean      NOT NULL DEFAULT false,  -- source anomaly: opening later than closing
    -- descriptive attributes and traceability
    product_status        varchar(20),
    n_source_rows         smallint     NOT NULL           -- CSV rows merged into this account
);
COMMENT ON TABLE dwh.fact_account IS 'Grain: one account (410,309). If the source holds several closing dates, the first one is kept.';

CREATE INDEX ix_fact_customer      ON dwh.fact_account (customer_id);
CREATE INDEX ix_fact_closing_date  ON dwh.fact_account (closing_date_id);
CREATE INDEX ix_fact_category      ON dwh.fact_account (category_id);
CREATE INDEX ix_fact_branch        ON dwh.fact_account (branch_id);

-- ---------------------------------------------------------------------
-- 4. ANALYTICAL VIEWS (read by Power BI and by the checks)
-- ---------------------------------------------------------------------

-- Overall KPIs: a single row.
CREATE VIEW dwh.v_kpi_overall AS
SELECT
    (SELECT count(*) FROM dwh.fact_account)                                      AS n_accounts,
    (SELECT sum(is_closed) FROM dwh.fact_account)                                AS n_closed_accounts,
    (SELECT round(avg(is_closed) * 100, 2) FROM dwh.fact_account)                AS account_churn_rate_pct,
    (SELECT count(*) FROM dwh.dim_customer)                                      AS n_customers,
    (SELECT count(*) FROM dwh.dim_customer WHERE n_accounts > 0)                 AS n_customers_with_account,
    (SELECT sum(is_churned) FROM dwh.dim_customer)                               AS n_churned_customers,
    (SELECT round(avg(is_churned) * 100, 2) FROM dwh.dim_customer)               AS customer_churn_rate_pct,
    (SELECT round(sum(is_churned) * 100.0 / count(*), 2) FROM dwh.dim_customer)  AS all_customers_churn_rate_pct;

-- Weekly closures series, zero weeks included (the phase 4 KPI).
CREATE VIEW dwh.v_weekly_closures AS
WITH bounds AS (
    SELECT min(d.full_date) AS first_week, max(d.full_date) AS last_week
    FROM dwh.fact_account f JOIN dwh.dim_date d ON d.date_id = f.closing_date_id
    WHERE f.is_closed = 1
),
weeks AS (
    SELECT generate_series(first_week, last_week, INTERVAL '7 days')::date AS week_start FROM bounds
)
SELECT w.week_start,
       count(f.account_id) AS n_closures
FROM weeks w
LEFT JOIN dwh.dim_date d     ON d.full_date = w.week_start
LEFT JOIN dwh.fact_account f ON f.closing_date_id = d.date_id AND f.is_closed = 1
GROUP BY w.week_start
ORDER BY w.week_start;

-- Churn by customer segment (customer grain).
CREATE VIEW dwh.v_churn_by_customer_segment AS
SELECT segment, age_band, tenure_band, kyc_score, file_complete,
       count(*)                        AS n_customers,
       sum(is_churned)                 AS n_churned,
       round(avg(is_churned) * 100, 2) AS churn_rate_pct
FROM dwh.dim_customer
WHERE is_churned IS NOT NULL
GROUP BY segment, age_band, tenure_band, kyc_score, file_complete;
