-- =====================================================================
--  VIGIE · Group BI 5 — Checks on the warehouse load
--
--  Run in pgAdmin after the Talend jobs (or after etl.py).
--  Each check compares the SOURCE (staging schema) with the TARGET (dwh schema)
--  and returns one row with an OK / KO verdict.
--
--  The final query (section 4) gathers every verdict in a single table.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. VOLUMES: does the target hold what the source announces?
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW dwh.v_checks AS

-- C01: every row of the CSV reached staging
SELECT 'C01' AS check_id, 'Rows loaded into staging' AS label,
       483536::numeric AS expected, count(*)::numeric AS actual
FROM staging.stg_churn

UNION ALL
-- C02: one source account = one fact row
SELECT 'C02', 'Distinct accounts: source = fact table',
       (SELECT count(DISTINCT account_no) FROM staging.stg_churn),
       (SELECT count(*) FROM dwh.fact_account)

UNION ALL
-- C03: one source customer = one dimension row
SELECT 'C03', 'Distinct customers: source = customer dimension',
       (SELECT count(DISTINCT customer_no) FROM staging.stg_churn),
       (SELECT count(*) FROM dwh.dim_customer)

UNION ALL
-- C04: the merged rows add up to the source rows that have an account
SELECT 'C04', 'Source rows with an account = sum of n_source_rows',
       (SELECT count(*) FROM staging.stg_churn WHERE account_no IS NOT NULL),
       (SELECT sum(n_source_rows) FROM dwh.fact_account)

UNION ALL
-- C05: customers with no account are in the dimension, without any fact
SELECT 'C05', 'Customers with no account (n_accounts = 0)',
       (SELECT count(DISTINCT customer_no) FROM staging.stg_churn WHERE account_no IS NULL),
       (SELECT count(*) FROM dwh.dim_customer WHERE n_accounts = 0)

-- ---------------------------------------------------------------------
-- 2. INDICATORS: are the KPIs identical on both sides?
-- ---------------------------------------------------------------------
UNION ALL
-- C06: number of closed accounts
SELECT 'C06', 'Closed accounts: source = fact table',
       (SELECT count(DISTINCT account_no) FROM staging.stg_churn WHERE account_status = 'Closed'),
       (SELECT sum(is_closed) FROM dwh.fact_account)

UNION ALL
-- C07: churn rate at account grain (in %)
SELECT 'C07', 'Churn rate per account (%)',
       (SELECT round(count(DISTINCT account_no) FILTER (WHERE account_status = 'Closed') * 100.0
                     / count(DISTINCT account_no), 2) FROM staging.stg_churn),
       (SELECT round(avg(is_closed) * 100, 2) FROM dwh.fact_account)

UNION ALL
-- C08: churned customers (all their accounts are closed)
SELECT 'C08', 'Churned customers: source = customer dimension',
       (SELECT count(*) FROM (
            SELECT customer_no FROM staging.stg_churn WHERE account_no IS NOT NULL
            GROUP BY customer_no HAVING bool_and(account_status = 'Closed')) s),
       (SELECT sum(is_churned) FROM dwh.dim_customer)

UNION ALL
-- C09: the first closing date was kept for every account
SELECT 'C09', 'Accounts whose closing date is not the first one (must be 0)',
       0,
       (SELECT count(*) FROM dwh.fact_account f
        JOIN (SELECT account_no, min(acct_close_date)::integer AS first_closing
              FROM staging.stg_churn WHERE acct_close_date IS NOT NULL GROUP BY account_no) s
          ON s.account_no = f.account_code
        WHERE f.closing_date_id <> s.first_closing)

UNION ALL
-- C10: sum of balances (amount reconciliation)
SELECT 'C10', 'Sum of balances: de-duplicated source = fact table',
       (SELECT sum(balance) FROM (SELECT DISTINCT account_no, acct_balance::numeric AS balance
                                  FROM staging.stg_churn WHERE account_no IS NOT NULL) s),
       (SELECT sum(balance) FROM dwh.fact_account)

UNION ALL
-- C11: weekly series — total closures
SELECT 'C11', 'Weekly series: total closures',
       (SELECT sum(is_closed) FROM dwh.fact_account),
       (SELECT sum(n_closures) FROM dwh.v_weekly_closures)

-- ---------------------------------------------------------------------
-- 3. INTEGRITY: keys, duplicates, consistency
-- ---------------------------------------------------------------------
UNION ALL
-- C12: no duplicate account in the facts
SELECT 'C12', 'Duplicate accounts in the facts (must be 0)',
       0, (SELECT count(*) - count(DISTINCT account_code) FROM dwh.fact_account)

UNION ALL
-- C13: no fact without a customer
SELECT 'C13', 'Facts without a customer in the dimension (must be 0)',
       0, (SELECT count(*) FROM dwh.fact_account f
           LEFT JOIN dwh.dim_customer c USING (customer_id) WHERE c.customer_id IS NULL)

UNION ALL
-- C14: an active account has no closing date, a closed account has one
SELECT 'C14', 'Status / closing date inconsistencies (must be 0)',
       0, (SELECT count(*) FROM dwh.fact_account
           WHERE (is_closed = 0 AND closing_date_id <> 0) OR (is_closed = 1 AND closing_date_id = 0))

UNION ALL
-- C15: every closing earlier than the opening (a source anomaly) is flagged
--      by opened_after_closing, and its age is not computed
SELECT 'C15', 'Closings earlier than the opening that are not flagged (must be 0)',
       0, (SELECT count(*) FROM dwh.fact_account
           WHERE opening_date_id <> 0 AND closing_date_id <> 0 AND closing_date_id < opening_date_id
             AND (NOT opened_after_closing OR account_age_days IS NOT NULL))

UNION ALL
-- C16: n_accounts in the customer dimension = number of facts of the customer
SELECT 'C16', 'Customers whose n_accounts does not match the facts (must be 0)',
       0, (SELECT count(*) FROM dwh.dim_customer c
           LEFT JOIN (SELECT customer_id, count(*) AS n FROM dwh.fact_account GROUP BY customer_id) f USING (customer_id)
           WHERE c.n_accounts <> coalesce(f.n, 0))

UNION ALL
-- C17: no customer holds both an active and a closed account
SELECT 'C17', 'Customers with a mixed active / closed status (must be 0)',
       0, (SELECT count(*) FROM (SELECT customer_id FROM dwh.fact_account
                                 GROUP BY customer_id HAVING min(is_closed) <> max(is_closed)) m)

UNION ALL
-- C18: every date of the facts exists in the calendar
SELECT 'C18', 'Fact dates missing from dim_date (must be 0)',
       0, (SELECT count(*) FROM dwh.fact_account f
           LEFT JOIN dwh.dim_date d1 ON d1.date_id = f.opening_date_id
           LEFT JOIN dwh.dim_date d2 ON d2.date_id = f.closing_date_id
           WHERE d1.date_id IS NULL OR d2.date_id IS NULL)

UNION ALL
-- C19: no negative account age
SELECT 'C19', 'Negative account ages (must be 0)',
       0, (SELECT count(*) FROM dwh.fact_account WHERE account_age_days < 0);

-- ---------------------------------------------------------------------
-- 4. CHECK DASHBOARD
-- ---------------------------------------------------------------------
SELECT check_id, label, expected, actual,
       CASE WHEN expected = actual THEN 'OK' ELSE 'KO' END AS verdict
FROM dwh.v_checks
ORDER BY check_id;

-- ---------------------------------------------------------------------
-- 5. DISTRIBUTION CHECKS (to compare by eye with notebook 01)
-- ---------------------------------------------------------------------
-- "Not provided" members per dimension: what share of the facts points to key 0?
SELECT 'category' AS dimension, round(avg((category_id = 0)::int) * 100, 1) AS pct_not_provided FROM dwh.fact_account
UNION ALL SELECT 'currency',     round(avg((currency_id = 0)::int) * 100, 1)     FROM dwh.fact_account
UNION ALL SELECT 'product',      round(avg((product_id = 0)::int) * 100, 1)      FROM dwh.fact_account
UNION ALL SELECT 'reason',       round(avg((reason_id = 0)::int) * 100, 1)       FROM dwh.fact_account
UNION ALL SELECT 'opening_date', round(avg((opening_date_id = 0)::int) * 100, 1) FROM dwh.fact_account
UNION ALL SELECT 'closing_date', round(avg((closing_date_id = 0)::int) * 100, 1) FROM dwh.fact_account;

-- Source anomaly: closed accounts whose opening is later than their closing.
SELECT count(*) FILTER (WHERE is_closed = 1 AND opening_date_id <> 0)  AS closed_accounts_with_opening_date,
       count(*) FILTER (WHERE opened_after_closing)                    AS opened_after_closing,
       round(count(*) FILTER (WHERE opened_after_closing) * 100.0
             / count(*) FILTER (WHERE is_closed = 1 AND opening_date_id <> 0), 1) AS share_pct
FROM dwh.fact_account;

-- The five busiest closing weeks (mass operations).
SELECT week_start, n_closures,
       round(n_closures * 100.0 / sum(n_closures) OVER (), 1) AS share_pct
FROM dwh.v_weekly_closures
ORDER BY n_closures DESC
LIMIT 5;
