# DAX measures — VIGIE Power BI report

> **Group BI 5** · Integrated Project, ESPRIT School of Business
> Each measure comes with its **grain**, its **formula** and its **expected value**. Expected values were computed in
> SQL on the loaded warehouse (see [`02_data_warehouse/kpis.md`](../02_data_warehouse/kpis.md)): a DAX measure is
> right when it shows that figure with no filter.

## 1. The semantic model

Tables imported from PostgreSQL (`dwh` schema): `fact_account`, `dim_customer`, `dim_date`, `dim_branch`,
`dim_industry`, `dim_account_category`, `dim_currency`, `dim_closure_reason`, `dim_product`.

| Relationship | Cardinality | Filter direction | State |
|---|---|---|---|
| `dim_customer[customer_id]` → `fact_account[customer_id]` | 1 : N | single | active |
| `dim_branch[branch_id]` → `fact_account[branch_id]` | 1 : N | single | active |
| `dim_industry[industry_id]` → `fact_account[industry_id]` | 1 : N | single | active |
| `dim_account_category[category_id]` → `fact_account[category_id]` | 1 : N | single | active |
| `dim_currency[currency_id]` → `fact_account[currency_id]` | 1 : N | single | active |
| `dim_closure_reason[reason_id]` → `fact_account[reason_id]` | 1 : N | single | active |
| `dim_product[product_id]` → `fact_account[product_id]` | 1 : N | single | active |
| `dim_date[date_id]` → `fact_account[closing_date_id]` | 1 : N | single | **inactive** |
| `dim_date[date_id]` → `fact_account[opening_date_id]` | 1 : N | single | **inactive** |

**Why the two date relationships are inactive.** `dim_date` plays two roles (opening and closing). If one of them
were active, a date filter would restrict *every* indicator to that role: a "2023" slicer would keep only the accounts
closed in 2023, and the churn rate would show 100%. With two inactive relationships the overall KPIs stay stable and
each time-based measure picks its role explicitly with `USERELATIONSHIP`.

**Model settings**

* Mark `dim_date` as a date table (`full_date` column).
* Hide every `*_id` column, plus `customer_code` and `account_code`, from the Report view: no identifier can be
  dragged into a visual.
* Sort `dim_date[month_name]` by `dim_date[month]`.
* Create an empty `_Measures` table and store every measure there, in display folders.

## 2. Volume measures

| Measure | Grain | Expected value |
|---|---|---:|
| `Accounts` | account | 410,309 |
| `Closed Accounts` | account | 148,215 |
| `Active Accounts` | account | 262,094 |
| `Customers` | customer | 363,024 |
| `Customers With Account` | customer | 319,040 |
| `Churned Customers` | customer | 117,345 |

```dax
Accounts = COUNTROWS ( fact_account )

Closed Accounts = SUM ( fact_account[is_closed] )

Active Accounts = [Accounts] - [Closed Accounts]

Customers = COUNTROWS ( dim_customer )

Customers With Account =
CALCULATE ( COUNTROWS ( dim_customer ), dim_customer[n_accounts] > 0 )

Churned Customers = SUM ( dim_customer[is_churned] )
```

## 3. Churn measures

| Measure | Grain | Expected value |
|---|---|---:|
| `Account Churn Rate` | account | 36.12% |
| `Customer Churn Rate` | customer | 36.78% |
| `All Customers Churn Rate` | customer | 32.32% |
| `Customer Retention Rate` | customer | 63.22% |
| `Churn Gap vs Average` | customer | 0.00 pt (no filter) |
| `Risk Index` | customer | 1.00 (no filter) |

```dax
Account Churn Rate = DIVIDE ( [Closed Accounts], [Accounts] )

Customer Churn Rate = DIVIDE ( [Churned Customers], [Customers With Account] )

All Customers Churn Rate = DIVIDE ( [Churned Customers], [Customers] )

Customer Retention Rate = 1 - [Customer Churn Rate]

-- Reference: the rate of the whole customer base, whatever filters are set on the customer.
Customer Churn Rate (overall) =
CALCULATE ( [Customer Churn Rate], REMOVEFILTERS ( dim_customer ) )

-- Gap in points to the average: used to colour the bars (red above, green below).
Churn Gap vs Average = [Customer Churn Rate] - [Customer Churn Rate (overall)]

-- 1.2 = the segment leaves 20% more often than average.
Risk Index = DIVIDE ( [Customer Churn Rate], [Customer Churn Rate (overall)] )
```

> ⚠ **The grain trap.** `Account Churn Rate` is read with the **account** dimensions (family, currency, product,
> reason). `Customer Churn Rate` is read with the attributes of **`dim_customer`** (segment, age band, tenure,
> KYC score, complete file). Filters flow from dimensions to facts, not the other way round: a filter on the account
> family does not filter `dim_customer`. To count customers by an account attribute, use:
>
> ```dax
> Customers (via accounts) = DISTINCTCOUNT ( fact_account[customer_id] )
> ```

## 4. Time-based measures

| Measure | Expected value |
|---|---:|
| `Closures` (no date filter) | 148,215 |
| `Closures` in 2020 · 2021 · 2022 · 2023 · 2024 | 36,815 · 41,647 · 44,042 · 18,426 · 7,285 |
| `Closures` for the week of 12/04/2021 | 24,295 |
| `Share of the 5 Mass Weeks` | 51.0% |
| `Openings` (no date filter) | 309,831 |

```dax
-- Closures dated by the closing date ("closing" role of dim_date).
Closures =
CALCULATE (
    [Closed Accounts],
    USERELATIONSHIP ( fact_account[closing_date_id], dim_date[date_id] )
)

-- Openings dated by the opening date ("opening" role). Accounts with no opening date are excluded.
Openings =
CALCULATE (
    [Accounts],
    USERELATIONSHIP ( fact_account[opening_date_id], dim_date[date_id] ),
    fact_account[opening_date_id] <> 0
)

-- Cumulative closures since the start of the period.
Cumulative Closures =
VAR last_day = MAX ( dim_date[full_date] )
RETURN
    CALCULATE ( [Closures], FILTER ( ALL ( dim_date ), dim_date[full_date] <= last_day ) )

-- 8-week moving average: smooths the spikes. Use with dim_date[week_start] on the axis.
Closures 8-Week Moving Average =
VAR last_week = MAX ( dim_date[week_start] )
RETURN
    DIVIDE (
        CALCULATE (
            [Closures],
            FILTER ( ALL ( dim_date ), dim_date[week_start] > last_week - 56 && dim_date[week_start] <= last_week )
        ),
        8
    )

-- Weight of the mass operations: share of closures carried by the 5 busiest weeks.
Share of the 5 Mass Weeks =
VAR top_weeks = TOPN ( 5, ALL ( dim_date[week_start] ), [Closures], DESC )
RETURN
    DIVIDE (
        SUMX ( top_weeks, [Closures] ),
        CALCULATE ( [Closures], ALL ( dim_date ) )
    )
```

> The dates of the dataset were shifted by the anonymisation. Time axes show **trends**; do not relate them to a real
> calendar in the titles or comments of the report.

## 5. Profile and value measures

| Measure | Grain | Expected value |
|---|---|---:|
| `Average Customer Tenure` | customer | 11.98 years |
| `Average Age of Active Accounts` | account | 8.24 years |
| `Median Balance of Active Accounts` | account | 14 |
| `Mean Balance of Active Accounts` | account | −495.46 |
| `Overdrawn Share` | account | 17.26% |
| `Multi-Account Share` | customer | 14.25% |
| `Complete File Share` | customer | 47.25% |
| `Overdue Review Share` | customer | 51.28% |
| `Accounts per Customer` | customer | 1.29 |

```dax
Average Customer Tenure =
CALCULATE ( AVERAGE ( dim_customer[tenure_years] ), dim_customer[n_accounts] > 0 )

Average Age of Active Accounts =
DIVIDE (
    CALCULATE ( AVERAGE ( fact_account[account_age_days] ), fact_account[is_closed] = 0 ),
    365.25
)

-- The median, not the mean: a few large loan balances pull the mean down.
Median Balance of Active Accounts =
CALCULATE ( MEDIAN ( fact_account[balance] ), fact_account[is_closed] = 0 )

Mean Balance of Active Accounts =
CALCULATE ( AVERAGE ( fact_account[balance] ), fact_account[is_closed] = 0 )

Overdrawn Share =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_account ), fact_account[is_closed] = 0, fact_account[is_overdrawn] = TRUE () ),
    CALCULATE ( COUNTROWS ( fact_account ), fact_account[is_closed] = 0 )
)

Multi-Account Share =
DIVIDE (
    CALCULATE ( COUNTROWS ( dim_customer ), dim_customer[n_accounts] > 1 ),
    [Customers With Account]
)

Complete File Share =
DIVIDE (
    CALCULATE ( COUNTROWS ( dim_customer ), dim_customer[n_accounts] > 0, dim_customer[file_complete] = TRUE () ),
    [Customers With Account]
)

Overdue Review Share =
DIVIDE (
    CALCULATE ( COUNTROWS ( dim_customer ), dim_customer[n_accounts] > 0, dim_customer[review_overdue] = TRUE () ),
    CALCULATE ( COUNTROWS ( dim_customer ), dim_customer[n_accounts] > 0, NOT ISBLANK ( dim_customer[review_overdue] ) )
)

Accounts per Customer = DIVIDE ( [Accounts], [Customers With Account] )

-- Value of a customer: sum of the balances of their active accounts, then median over the customers of the segment.
Median Balance per Customer =
MEDIANX (
    FILTER ( VALUES ( dim_customer[customer_id] ), CALCULATE ( [Active Accounts] ) > 0 ),
    CALCULATE ( SUM ( fact_account[balance] ), fact_account[is_closed] = 0 )
)
```

## 6. Check values per segment

To compare with page 3 of the report (filter on `dim_customer[segment]`).

| Segment | `Customers With Account` | `Customer Churn Rate` | `Average Customer Tenure` | `Accounts per Customer` | `Multi-Account Share` | `Complete File Share` | `Median Balance per Customer` |
|---|---:|---:|---:|---:|---:|---:|---:|
| Retail | 290,629 | 37.0% | 11.8 years | 1.17 | 10.8% | 48.1% | 88 |
| Corporate Small | 23,216 | 34.1% | 13.3 years | 1.98 | 44.4% | 33.7% | 78 |
| Corporate | 3,097 | 31.8% | 15.3 years | 5.76 | 78.6% | 52.0% | −79 |
| Premium | 2,098 | 37.7% | 14.6 years | 2.68 | 57.6% | 68.2% | 385 |

By age band and by account family: see the tables in [`kpis.md`](../02_data_warehouse/kpis.md).

## 7. Conditional formatting and dynamic labels

```dax
-- Bar colour: red above average, green below (Format → Colours → fx → Field value).
Churn Colour = IF ( [Churn Gap vs Average] > 0, "#D62839", "#2A9D8F" )

-- Dynamic title of page 1.
Overview Title =
"Churn: " & FORMAT ( [Account Churn Rate], "0.0%" ) & " of accounts · "
    & FORMAT ( [Customer Churn Rate], "0.0%" ) & " of customers"

-- Warning displayed when a visual by family, currency or product is on screen.
Not Provided Warning =
"Reading: " & FORMAT (
    DIVIDE ( CALCULATE ( [Closed Accounts], dim_account_category[category_id] = 0 ), [Closed Accounts] ), "0%"
) & " of closed accounts no longer have a family; the rate of the other families is understated."
```

Expected value of the percentage in `Not Provided Warning`: **68%** (100,478 closed accounts out of 148,215).

## 8. Measure checklist

- [ ] With no filter, the six volume measures show the expected values.
- [ ] `Account Churn Rate` = 36.12% and `Customer Churn Rate` = 36.78%.
- [ ] The sum of `Closures` per year gives back 148,215.
- [ ] A slicer on `dim_date[year]` does not change `Accounts` (the date relationships are indeed inactive).
- [ ] The per-segment table matches section 6.
- [ ] No visual exposes `customer_code` or `account_code`.
