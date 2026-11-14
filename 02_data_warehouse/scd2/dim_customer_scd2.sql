-- =====================================================================
--  VIGIE · Group BI 5 — BONUS: slowly changing dimension, type 2
--
--  Goal: keep the history of the customer attributes that change over
--  time (KYC score, segment, complete file) instead of overwriting the
--  previous value.
--
--  Principle: one row per VERSION of the customer, with
--      valid_from / valid_to / is_current.
--
--  This script is self-contained and can be re-run. It works in the
--  dwh_scd2 schema and ends with a demonstration on FICTITIOUS customers.
-- =====================================================================

DROP SCHEMA IF EXISTS dwh_scd2 CASCADE;
CREATE SCHEMA dwh_scd2;

-- 1. The historised dimension -------------------------------------------------
CREATE TABLE dwh_scd2.dim_customer_history (
    customer_sk    bigserial    PRIMARY KEY,          -- surrogate key: one per VERSION
    customer_code  varchar(10)  NOT NULL,             -- business key: one per CUSTOMER
    -- tracked attributes (type 2: any change creates a new version)
    kyc_score      varchar(15)  NOT NULL,
    segment        varchar(20)  NOT NULL,
    file_complete  boolean      NOT NULL,
    -- SCD2 technical columns
    valid_from     date         NOT NULL,
    valid_to       date         NOT NULL DEFAULT DATE '9999-12-31',
    is_current     boolean      NOT NULL DEFAULT true,
    CHECK (valid_to >= valid_from)
);
-- A customer has only one current version.
CREATE UNIQUE INDEX ux_customer_current_version
    ON dwh_scd2.dim_customer_history (customer_code) WHERE is_current;

-- 2. The landing table: the state of the customers on the load date ----------
CREATE TABLE dwh_scd2.stg_customer (
    customer_code  varchar(10) PRIMARY KEY,
    kyc_score      varchar(15) NOT NULL,
    segment        varchar(20) NOT NULL,
    file_complete  boolean     NOT NULL
);

-- 3. The SCD2 load procedure ---------------------------------------------------
CREATE OR REPLACE PROCEDURE dwh_scd2.load_dim_customer(p_load_date date)
LANGUAGE plpgsql AS $$
BEGIN
    -- a) Close the current version of the customers whose tracked attributes changed.
    UPDATE dwh_scd2.dim_customer_history d
    SET valid_to   = p_load_date - 1,
        is_current = false
    FROM dwh_scd2.stg_customer s
    WHERE d.customer_code = s.customer_code
      AND d.is_current
      AND (d.kyc_score, d.segment, d.file_complete)
          IS DISTINCT FROM (s.kyc_score, s.segment, s.file_complete);

    -- b) Insert a current version for: new customers, and those closed in a).
    INSERT INTO dwh_scd2.dim_customer_history
        (customer_code, kyc_score, segment, file_complete, valid_from)
    SELECT s.customer_code, s.kyc_score, s.segment, s.file_complete, p_load_date
    FROM dwh_scd2.stg_customer s
    LEFT JOIN dwh_scd2.dim_customer_history d
           ON d.customer_code = s.customer_code AND d.is_current
    WHERE d.customer_code IS NULL;
END;
$$;

-- 4. Demonstration on FICTITIOUS customers -------------------------------------
-- Initial load: three customers.
INSERT INTO dwh_scd2.stg_customer VALUES
    ('DEMO01', 'LR', 'Retail',  false),
    ('DEMO02', 'MR', 'Retail',  true),
    ('DEMO03', 'LR', 'Premium', true);
CALL dwh_scd2.load_dim_customer(DATE '2024-01-01');

-- Next load: DEMO01 completes its file, DEMO02 changes KYC score,
-- DEMO03 does not change, DEMO04 is a new customer.
TRUNCATE dwh_scd2.stg_customer;
INSERT INTO dwh_scd2.stg_customer VALUES
    ('DEMO01', 'LR', 'Retail',  true),
    ('DEMO02', 'H1', 'Retail',  true),
    ('DEMO03', 'LR', 'Premium', true),
    ('DEMO04', 'LR', 'Retail',  false);
CALL dwh_scd2.load_dim_customer(DATE '2024-02-01');

-- Expected result: 6 rows.
--   DEMO01: 2 versions (incomplete file until 31 Jan, complete afterwards)
--   DEMO02: 2 versions (MR until 31 Jan, H1 afterwards)
--   DEMO03: 1 version  (unchanged: no row added)
--   DEMO04: 1 version  (new customer)
SELECT customer_code, kyc_score, segment, file_complete, valid_from, valid_to, is_current
FROM dwh_scd2.dim_customer_history
ORDER BY customer_code, valid_from;

-- Retrieve the state of a customer at a past date ("as of"):
SELECT customer_code, kyc_score, file_complete
FROM dwh_scd2.dim_customer_history
WHERE DATE '2024-01-15' BETWEEN valid_from AND valid_to
ORDER BY customer_code;
