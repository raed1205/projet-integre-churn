# Talend jobs — build specification

> **Status of this folder.** This document is the **build plan** of the jobs. The jobs themselves are built and
> exported from Talend Studio: drop the exported archive here (`VIGIE_Talend_Jobs.zip`) together with a screenshot
> of each job (`screenshots/J01.png` …). Until the archive is added, the reference load is
> `01_etl/python_pipeline/etl.py`, which applies exactly the rules below.
>
> **Common acceptance test.** Whatever the tool, `02_data_warehouse/checks/checks.sql` must return **19 / 19 OK**.
> This is what proves that the Talend jobs load the same thing as the reference.

## Overview

| Job | Role | Input | Output | Expected rows |
|---|---|---|---|---:|
| `J00_Orchestration` | Chains the jobs, stops at the first failure | — | — | — |
| `J01_Staging` | **Extract**: raw copy of the 6 files | CSV + 5 Excel files | `staging.stg_*` | 483,536 + 59 |
| `J02_Dim_References` | Dimensions built from the reference files | `staging.stg_*` | 6 dimensions | 22 · 23 · 15 · 6 · 13 · 14 |
| `J03_Dim_Customer` | Customer dimension and derived variables | `staging.stg_churn` | `dwh.dim_customer` | 363,024 |
| `J04_Fact_Account` | Fact table at account grain | `staging.stg_churn` + dimensions | `dwh.fact_account` | 410,309 |
| `J05_Checks` | Source ↔ warehouse acceptance | `dwh.v_checks` | console / stop | 19 |

The `dwh.dim_date` calendar is created by `create_tables.sql` (`generate_series`): no job is needed for it.

## Preparation

1. **PostgreSQL**: create the `vigie_dwh` database and run `02_data_warehouse/schema/create_tables.sql` in pgAdmin.
2. **Talend Studio**: create the `VIGIE_BI5` project.
3. **Metadata → Db Connections**: create `PG_VIGIE` (PostgreSQL) and use it in every `tDB*` component.
4. **Contexts**: create the `ctx_vigie` group and add it to every job.

| Context variable | Type | Example | Use |
|---|---|---|---|
| `data_dir` | Directory | `C:/project/data/` | local location of the source files |
| `pg_host` | String | `localhost` | PostgreSQL server |
| `pg_port` | String | `5432` | |
| `pg_database` | String | `vigie_dwh` | |
| `pg_user` | String | `postgres` | |
| `pg_password` | Password | *(empty when exporting)* | **never exported** |
| `reference_date` | Date | `2024-02-19` | date of the snapshot = last account event |

> ⚠ **Before exporting**: clear `pg_password` and check that the archive holds no CSV or Excel file.
> `File → Export items` exports the jobs, not the data; do not tick "Export dependencies" on the `data/` folder.

---

## J01_Staging — extraction

Goal: land the files **as they are** in the `staging` schema. No transformation, everything as `String`.

```
tDBConnection ──OnSubjobOk──▶ tFileInputDelimited ──main──▶ tDBOutput (stg_churn)
                         ├──▶ tFileInputExcel (ACCOUNT_CATEGORY) ──▶ tDBOutput (stg_account_category)
                         ├──▶ tFileInputExcel (CLOSURE_REASON)   ──▶ tDBOutput (stg_closure_reason)
                         ├──▶ tFileInputExcel (CURRENCY)         ──▶ tDBOutput (stg_currency)
                         ├──▶ tFileInputExcel (INDUSTRY)         ──▶ tDBOutput (stg_industry)
                         └──▶ tFileInputExcel (TARGET)           ──▶ tDBOutput (stg_target)
                                                                     └──OnSubjobOk──▶ tDBCommit
```

| Component | Settings |
|---|---|
| `tFileInputDelimited` | File `context.data_dir + "data_churn.csv"` · separator `,` · header `1` · encoding `UTF-8` · schema: 32 **String** columns, all nullable |
| `tFileInputExcel` ×5 | `.xlsx` file (tick *Read excel2007 file format*) · sheet 1 · header `1` · 2 String columns |
| `tDBOutput` ×6 | Action on table: *Truncate table* · action on data: *Insert* · *Batch size* 10,000 |

Immediate check: `stg_churn` holds **483,536** rows (check C01).

---

## J02_Dim_References — reference dimensions

Same pattern for each dimension: one "Not provided" row with key `0`, then one row per code.

```
tFixedFlowInput (key 0) ───────────────────────────┐
                                                    ├──▶ tUnite ──▶ tDBOutput (dim_xxx)
tDBInput (staging) ──▶ tSortRow ──▶ tMap (key) ────┘
```

| Dimension | Query of the `tDBInput` | Key in the `tMap` | Row with key 0 |
|---|---|---|---|
| `dim_account_category` | `SELECT category_id, description FROM staging.stg_account_category` | `Numeric.sequence("cat", 1, 1)` | `ND` · Not provided · family Not provided |
| `dim_currency` | `SELECT currency_code, description FROM staging.stg_currency` | `Numeric.sequence("cur", 1, 1)` | `ND` · Not provided |
| `dim_closure_reason` | `SELECT reason_id, description FROM staging.stg_closure_reason` | `Numeric.sequence("rsn", 1, 1)` | `ND` · No reason (active account or not entered) |
| `dim_industry` | `SELECT industry_code, description FROM staging.stg_industry` | `Numeric.sequence("ind", 1, 1)` | `ND` · Not provided |
| `dim_branch` | `SELECT DISTINCT branch_group FROM staging.stg_churn` | `Numeric.sequence("br", 1, 1)` | `ND` · Not provided · masked |
| `dim_product` | `SELECT DISTINCT product_group, product_line FROM staging.stg_churn WHERE product_group IS NOT NULL` | `Numeric.sequence("prd", 1, 1)` | Not provided · Not provided |

`tMap` expressions:

* **`dim_account_category.family`** (the labels are those of the reference file)

  ```java
  row1.description.startsWith("Credit") || row1.description.equals("Financement court terme") ? "Loans"
  : (row1.description.equals("Autres comptes") || row1.description.equals("Coffres")
     || row1.description.equals("Contentieux")) ? "Other"
  : "Deposits"
  ```
* **`dim_branch.label`**: `row1.branch_group.equals("AG00") ? "Masked branches" : "Branch group " + row1.branch_group.substring(2)`
* **`dim_branch.is_masked`**: `row1.branch_group.equals("AG00")`

---

## J03_Dim_Customer — customer dimension

```
tDBInput (customers) ──▶ tMap ──▶ tDBOutput (dwh.dim_customer)
                          ▲  ▲
tDBInput (accounts per customer) ─┘  └── tDBInput (stg_target: label of the line of business)
```

**Main `tDBInput`** — one row per customer (customer attributes are constant from one row to the next):

```sql
SELECT DISTINCT customer_no, nationality_region, residence_region, marital_status, birth_period,
       cust_opening_date, nature_client, partyclass, lob, score_kyc, completed_file,
       last_review_date, next__review_date, salary
FROM staging.stg_churn
ORDER BY customer_no
```

**Lookup `tDBInput` "accounts per customer"** — number of accounts and churn of the customer:

```sql
SELECT customer_no,
       count(DISTINCT account_no)                AS n_accounts,
       bool_and(account_status = 'Closed')::int  AS is_churned
FROM staging.stg_churn
WHERE account_no IS NOT NULL
GROUP BY customer_no
```

`tMap` join: *Left Outer Join* on `customer_no` (customers with no account must go through).

| Target column | `tMap` expression |
|---|---|
| `customer_id` | `Numeric.sequence("customer", 1, 1)` |
| `customer_code` | `row1.customer_no` |
| `marital_status` | `"C".equals(row1.marital_status) ? "Single" : "M".equals(row1.marital_status) ? "Married" : "D".equals(row1.marital_status) ? "Divorced" : "V".equals(row1.marital_status) ? "Widowed" : "Not provided"` |
| `birth_period` | `row1.birth_period == null ? null : (int) Double.parseDouble(row1.birth_period)` |
| `age` | `row1.birth_period == null ? null : TalendDate.getPartOfDate("YEAR", context.reference_date) - ((int) Double.parseDouble(row1.birth_period) + 2)` |
| `age_band` | see the rule below |
| `customer_type` | `row1.nature_client` |
| `segment` | `row1.partyclass` |
| `line_of_business` | `target.description == null ? "Not provided" : target.description` |
| `relationship_start_date` | `row1.cust_opening_date == null ? null : TalendDate.parseDate("yyyyMMdd", row1.cust_opening_date)` |
| `tenure_years` | `Var.start_date == null ? null : TalendDate.diffDate(context.reference_date, Var.start_date, "dd") / 365.25` |
| `declared_income` | `row1.salary == null ? null : new java.math.BigDecimal(row1.salary)` |
| `n_accounts` | `accounts.n_accounts == null ? 0 : accounts.n_accounts` |
| `kyc_score` | `row1.score_kyc == null ? "Not provided" : row1.score_kyc` |
| `file_complete` | `"YES".equals(row1.completed_file)` |
| `months_since_review` | `Var.last_review == null ? null : TalendDate.diffDate(context.reference_date, Var.last_review, "dd") / 30.4375` |
| `review_overdue` | `Var.next_review == null ? null : Var.next_review.before(context.reference_date)` |
| `is_churned` | `accounts.is_churned` *(stays `null` for a customer with no account)* |

**Bands** (to place in the `Var` variables of the `tMap`):

| Variable | Bounds | Labels |
|---|---|---|
| `age_band` | age ≤ 17 · 18–24 · 25–34 · 35–44 · 45–54 · 55–64 · ≥ 65 · blank | `Under 18` · `18–24` · `25–34` · `35–44` · `45–54` · `55–64` · `65 and over` · `Not provided` |
| `tenure_band` | ≤ 2 · ]2 ; 5] · ]5 ; 10] · ]10 ; 15] · > 15 · blank | `Under 2 years` · `2–5 years` · `5–10 years` · `10–15 years` · `15 years and over` · `Not provided` |

Checks: **363,024** rows (C03), of which **43,984** with `n_accounts = 0` (C05) and **117,345** with `is_churned = 1` (C08).

---

## J04_Fact_Account — fact table

```
tDBInput (rows with an account, GROUP BY) ──▶ tMap (7 lookups) ──▶ tDBOutput (dwh.fact_account)
                                                 │
                                                 └──rejects──▶ tLogRow ("account without a customer")
```

**Moving to account grain.** The simplest and safest way is to do it in the query of the `tDBInput`:

```sql
SELECT account_no,
       min(customer_no)                           AS customer_no,
       min(account_status)                        AS account_status,
       min(acct_opening_date)                     AS acct_opening_date,
       min(acct_close_date)                       AS acct_close_date,     -- FIRST closing
       (array_agg(closure_reason ORDER BY acct_close_date, closure_reason))[1] AS closure_reason,
       min(account_category)                      AS account_category,
       min(currency)                              AS currency,
       min(acct_balance)                          AS acct_balance,
       min(product_group)                         AS product_group,
       min(product_line)                          AS product_line,
       min(amount)                                AS amount,
       max(fixedrate::numeric)                    AS fixedrate,           -- the highest when several
       min(product_status)                        AS product_status,
       min(branch_group)                          AS branch_group,
       min(industry)                              AS industry,
       count(*)                                   AS n_source_rows
FROM staging.stg_churn
WHERE account_no IS NOT NULL
GROUP BY account_no
```

> All-component variant: `tSortRow` (`account_no`, `acct_close_date` ascending) → `tAggregateRow`
> (group by `account_no`; `acct_close_date`: *min*; `fixedrate`: *max*; the other columns: *first*;
> `n_source_rows`: *count*). Both variants give the same 410,309 rows.

**Lookups of the `tMap`** (all *Left Outer Join*, match model *Unique match*):

| Lookup | Join key | Key brought back | If missing |
|---|---|---|---|
| `dwh.dim_customer` | `customer_no = customer_code` | `customer_id` | **reject** (must never happen: C13) |
| `dwh.dim_branch` | `branch_group = group_code` | `branch_id` | `0` |
| `dwh.dim_industry` | `industry = industry_code` | `industry_id` | `0` |
| `dwh.dim_account_category` | `account_category = category_code` | `category_id` | `0` |
| `dwh.dim_currency` | `currency = currency_code` | `currency_id` | `0` |
| `dwh.dim_closure_reason` | `closure_reason = reason_code` | `reason_id` | `0` |
| `dwh.dim_product` | `product_group` and `product_line` | `product_id` | `0` |

For each key: `dim.xxx_id == null ? 0 : dim.xxx_id`.

| Target column | `tMap` expression |
|---|---|
| `account_id` | `Numeric.sequence("account", 1, 1)` |
| `account_code` | `row1.account_no` |
| `opening_date_id` | `row1.acct_opening_date == null ? 0 : Integer.parseInt(row1.acct_opening_date)` |
| `closing_date_id` | `row1.acct_close_date == null ? 0 : Integer.parseInt(row1.acct_close_date)` |
| `is_closed` | `"Closed".equals(row1.account_status) ? 1 : 0` |
| `balance` | `row1.acct_balance == null ? null : new java.math.BigDecimal(row1.acct_balance)` |
| `is_overdrawn` | `Var.balance == null ? null : Var.balance.signum() < 0` |
| `product_amount` | `row1.amount == null ? null : new java.math.BigDecimal(row1.amount)` |
| `fixed_rate` | `row1.fixedrate` *(already numeric in the query output)* |
| `opened_after_closing` | `Var.opening != null && Var.closing != null && Var.closing.before(Var.opening)` |
| `account_age_days` | `Var.opening == null \|\| Var.opened_after_closing ? null : (int) TalendDate.diffDate(Var.closing == null ? context.reference_date : Var.closing, Var.opening, "dd")` |
| `product_status` | `row1.product_status` |
| `n_source_rows` | `row1.n_source_rows` |

`tDBOutput`: *Insert*, *Batch size* 10,000, **after** `J02` and `J03` (the foreign keys must exist).

Checks: **410,309** rows (C02), **148,215** closed accounts (C06), sum of `n_source_rows` = **439,552** (C04).

---

## J05_Checks — acceptance

```
tDBRow (checks.sql: creates the view) ──OnComponentOk──▶ tDBInput (dwh.v_checks)
        ──▶ tMap (verdict) ──▶ tLogRow (table)
                          └──filter "KO"──▶ tDie ("Check failed")
```

* `tDBInput`: `SELECT check_id, label, expected, actual FROM dwh.v_checks ORDER BY check_id`
* `tMap`: `verdict = row1.expected.compareTo(row1.actual) == 0 ? "OK" : "KO"`
* A filtered output `"KO".equals(verdict)` linked to a `tDie`: the job fails if a single check is wrong.

## J00_Orchestration

```
tPrejob ──▶ tDBConnection
tRunJob(J01) ─OnSubjobOk▶ tRunJob(J02) ─OnSubjobOk▶ tRunJob(J03) ─OnSubjobOk▶ tRunJob(J04) ─OnSubjobOk▶ tRunJob(J05)
tPostjob ──▶ tDBClose
```

Each `tRunJob`: tick *Die on child error* and *Transmit whole context*.

---

## Talend ↔ Python pipeline mapping

| Step | Talend | Python (`etl.py`) |
|---|---|---|
| Reading CSV / Excel | `tFileInputDelimited`, `tFileInputExcel` | `data.load_raw()`, `data.load_references()` |
| Landing in staging | `tDBOutput` (truncate + insert) | `bulk_load()` (`COPY`) |
| Typing the dates | `TalendDate.parseDate("yyyyMMdd", …)` | `data.cast_types()` |
| Account grain | `tAggregateRow` / `GROUP BY account_no` | `data.account_grain()` |
| Customer grain | `tDBInput DISTINCT` + aggregated lookup | `data.customer_grain()` |
| Surrogate keys | `Numeric.sequence` | `range(1, n + 1)` |
| "Not provided" member | `tFixedFlowInput` + `tUnite` | `dimension()` |
| Joins | `tMap` lookups | `map()` / `merge()` |
| Acceptance | `J05_Checks` | `checks.sql` |

Surrogate keys may differ from one tool to the other (they depend on the insertion order); the **volumes and the
KPIs must be identical**: this is what the 19 checks verify.

## Checklist before adding the export

- [ ] `J00_Orchestration` runs end to end without error.
- [ ] `checks.sql` returns 19 / 19 OK in pgAdmin.
- [ ] The context password is empty.
- [ ] The archive holds no `.csv` or `.xlsx` file.
- [ ] A screenshot of each job is added to `screenshots/`.
