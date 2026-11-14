# Results of the load checks

> Run of `checks.sql` on the loaded warehouse — **19 checks, 19 OK**.
> Source = `staging` schema (raw copy of the files) · Target = `dwh` schema (star schema).
> Re-run in pgAdmin after every Talend load: the table must be identical.

| Check | Label | Expected | Actual | Verdict |
|---|---|---:|---:|:---:|
| C01 | Rows loaded into staging | 483,536 | 483,536 | ✔ OK |
| C02 | Distinct accounts: source = fact table | 410,309 | 410,309 | ✔ OK |
| C03 | Distinct customers: source = customer dimension | 363,024 | 363,024 | ✔ OK |
| C04 | Source rows with an account = sum of n_source_rows | 439,552 | 439,552 | ✔ OK |
| C05 | Customers with no account (n_accounts = 0) | 43,984 | 43,984 | ✔ OK |
| C06 | Closed accounts: source = fact table | 148,215 | 148,215 | ✔ OK |
| C07 | Churn rate per account (%) | 36.12 | 36.12 | ✔ OK |
| C08 | Churned customers: source = customer dimension | 117,345 | 117,345 | ✔ OK |
| C09 | Accounts whose closing date is not the first one (must be 0) | 0 | 0 | ✔ OK |
| C10 | Sum of balances: de-duplicated source = fact table | -636,613,392.10 | -636,613,392.10 | ✔ OK |
| C11 | Weekly series: total closures | 148,215 | 148,215 | ✔ OK |
| C12 | Duplicate accounts in the facts (must be 0) | 0 | 0 | ✔ OK |
| C13 | Facts without a customer in the dimension (must be 0) | 0 | 0 | ✔ OK |
| C14 | Status / closing date inconsistencies (must be 0) | 0 | 0 | ✔ OK |
| C15 | Closings earlier than the opening that are not flagged (must be 0) | 0 | 0 | ✔ OK |
| C16 | Customers whose n_accounts does not match the facts (must be 0) | 0 | 0 | ✔ OK |
| C17 | Customers with a mixed active / closed status (must be 0) | 0 | 0 | ✔ OK |
| C18 | Fact dates missing from dim_date (must be 0) | 0 | 0 | ✔ OK |
| C19 | Negative account ages (must be 0) | 0 | 0 | ✔ OK |

## Distribution checks

**Share of facts attached to the "Not provided" member (key 0)**

| Dimension | % of accounts |
|---|---:|
| Account family | 24.5 |
| Closing date (active accounts) | 63.9 |
| Opening date | 24.5 |
| Product | 36.9 |
| Closure reason | 67.2 |
| Currency | 24.5 |

These shares are identical to the missing-value rates measured at account grain in the univariate analysis notebook: no information was lost or invented during the load.

**Source anomaly — flagged, not corrected**

| Indicator | Value |
|---|---:|
| Closed accounts whose opening date is filled in | 47,737 |
| … of which opening later than closing | 20,166 |
| Share | 42.2% |

For these accounts the opening date cannot be used to compute an age. The warehouse keeps the source value, sets `opened_after_closing = true` and leaves `account_age_days` as `NULL`.

**The five busiest closing weeks (mass operations)**

| Week (Monday) | Closures | Share of total |
|---|---:|---:|
| 12/04/2021 | 24,295 | 16.4% |
| 21/09/2020 | 22,525 | 15.2% |
| 07/11/2022 | 16,301 | 11.0% |
| 03/10/2022 | 8,794 | 5.9% |
| 01/11/2021 | 3,641 | 2.5% |

These five weeks carry 51.0% of the 148,215 closures. The dates were shifted by the anonymisation, so they match no real calendar.
