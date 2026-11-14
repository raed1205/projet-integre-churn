# KPI catalogue — VIGIE · Group BI 5

Every KPI has **a grain, a formula and a reference value**. The reference value is the one the loaded warehouse
returns; it is used to check that Power BI (DAX) and the application display the same figure.

> **Golden rule: a rate is always computed at its grain.** A "per row" churn rate (40.3%) is neither the rate per
> account (36.1%) nor the rate per customer (36.8%). Since the warehouse is at account grain, no confusion is possible.

## 1. Volume KPIs

| # | KPI | Grain | SQL formula (`dwh` schema) | Reference value |
|---|---|---|---|---:|
| K01 | Number of accounts | account | `count(*) FROM fact_account` | **410,309** |
| K02 | Active accounts | account | `count(*) FILTER (WHERE is_closed = 0)` | **262,094** |
| K03 | Closed accounts | account | `sum(is_closed)` | **148,215** |
| K04 | Number of customers | customer | `count(*) FROM dim_customer` | **363,024** |
| K05 | Customers with at least one account | customer | `count(*) FILTER (WHERE n_accounts > 0)` | **319,040** |
| K06 | Churned customers | customer | `sum(is_churned)` | **117,345** |

## 2. Churn KPIs

| # | KPI | Grain | Formula | Reference value |
|---|---|---|---|---:|
| K07 | **Churn rate (accounts)** | account | `sum(is_closed) / count(*)` | **36.12%** |
| K08 | **Churn rate (customers)** | customer | `sum(is_churned) / count(*)` over customers with an account | **36.78%** |
| K09 | Churn rate (all customers) | customer | `sum(is_churned) / count(*)` over all customers | **32.32%** |
| K10 | Retention rate (customers) | customer | `1 − K08` | **63.22%** |
| K11 | Weekly closures | week | `count(*)` per `week_start` of the closing date, zero weeks included | median **165.5** · mean **733.7** |
| K12 | Share of mass operations | week | share of closures carried by the 5 busiest weeks | **51.0%** |

**Definition of churn.** An account is churned when it is closed (`ACCOUNT_STATUS = 'Closed'`). A customer is churned
when **all** of their accounts are closed. Since no customer holds both an active and a closed account (check C17),
the two readings are consistent with each other.

## 3. Profile and value KPIs

| # | KPI | Grain | Formula | Reference value |
|---|---|---|---|---:|
| K13 | Average customer tenure | customer | `avg(tenure_years)` (customers with an account) | **11.98 years** (median 11.13) |
| K14 | Average age of active accounts | account | `avg(account_age_days) / 365.25` over `is_closed = 0` | **8.24 years** |
| K15 | Median balance of active accounts | account | `percentile_cont(0.5)` of `balance` over `is_closed = 0` | **14** |
| K16 | Mean balance of active accounts | account | `avg(balance)` over `is_closed = 0` | **−495.46** |
| K17 | Share of overdrawn accounts (active) | account | `avg(is_overdrawn)` over `is_closed = 0` | **17.26%** |
| K18 | Multi-account rate | customer | share of customers holding more than one account | **14.25%** |
| K19 | Share of complete files | customer | `avg(file_complete)` (customers with an account) | **47.25%** |
| K20 | Share of overdue reviews | customer | `avg(review_overdue)` (customers with an account) | **51.28%** |

## 4. Calculation rules and pitfalls

1. **Mean balance ≠ median balance.** The mean balance of active accounts is negative (−495) whereas the median is
   14: a few large loan balances pull the mean down. We display the **median**; the mean is given for the record
   only. Since amounts are rounded and capped, they serve to **compare**, never as a real outstanding amount.
2. **Balance and account-age KPIs are read on active accounts.** For 68% of closed accounts, the balance, family,
   currency and opening date are blank. Computing them over "all accounts" would mix two populations that are not
   filled in the same way.
3. **Churn by account family is understated.** The 100,478 closed accounts with no family fall into the
   "Not provided" member (100% churn rate). The rate of the other families therefore only covers the closed
   accounts *whose family is known*. This member must stay **visible** in any chart by family, currency or
   product; it must not be filtered out.
4. **Account age is not computed when the dates are inconsistent.** 20,166 closed accounts have an opening date
   later than their closing date; they are flagged by `opened_after_closing` and their age is `NULL`.
5. **Dates are shifted** (anonymisation). We read durations and trends, never calendar dates.
6. **No aggregate is published below 20 individuals** (application, screenshots, report).

## 5. Reference values per axis (to check Power BI)

**Churn rate by commercial segment (customer grain)**

| Segment | Customers | Churn rate | Average tenure | Accounts per customer |
|---|---:|---:|---:|---:|
| Retail | 290,629 | 37.0% | 11.8 years | 1.17 |
| Corporate Small | 23,216 | 34.1% | 13.3 years | 1.98 |
| Corporate | 3,097 | 31.8% | 15.3 years | 5.76 |
| Premium | 2,098 | 37.7% | 14.6 years | 2.68 |

**Churn rate by age band (customer grain)**

| Age band | Customers | Churn rate |
|---|---:|---:|
| Under 18 | 10,067 | 8.4% |
| 18–24 | 9,054 | 23.2% |
| 25–34 | 52,602 | 44.4% |
| 35–44 | 66,685 | 41.3% |
| 45–54 | 60,413 | 37.1% |
| 55–64 | 47,878 | 35.2% |
| 65 and over | 52,315 | 34.7% |
| Not provided | 20,026 | 30.3% |

**Churn rate by account family (account grain)** — see pitfall no. 3. Family labels are those of the reference file.

| Account family | Accounts | Closed accounts | Churn rate |
|---|---:|---:|---:|
| Epargne (savings) | 176,588 | 13,247 | 7.5% |
| *Not provided* | 100,478 | 100,478 | 100.0% |
| Financement court terme (short-term financing) | 22,270 | 6,583 | 29.6% |
| Comptes courants (current accounts) | 22,224 | 3,786 | 17.0% |
| Credit immobilier (mortgage) | 15,953 | 3,367 | 21.1% |
| Credit consommation (consumer credit) | 15,495 | 3,545 | 22.9% |
| Contentieux (litigation) | 14,289 | 3,449 | 24.1% |
| Comptes en devises (foreign-currency accounts) | 13,837 | 3,199 | 23.1% |
| Exigibles (demand deposits) | 8,779 | 1,500 | 17.1% |
| Autres comptes (other accounts) | 6,080 | 1,800 | 29.6% |
| Placements a terme (term deposits) | 5,790 | 4,779 | 82.5% |
| Credit investissement (investment loan) | 3,403 | 886 | 26.0% |
| Comptes indisponibles (blocked accounts) | 3,321 | 1,186 | 35.7% |
| Credit automobile (car loan) | 1,187 | 271 | 22.8% |
| Coffres (safe-deposit boxes) | 615 | 139 | 22.6% |

**Closures per year**: 2020: 36,815 · 2021: 41,647 · 2022: 44,042 · 2023: 18,426 · 2024: 7,285 (total 148,215).
