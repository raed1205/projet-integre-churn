# 04 — Predictive models

Two models, two questions:

| Question | Model | Main result |
|---|---|---|
| **How many accounts will close next week?** | LSTM (Keras) on the weekly closures series | MAE of 287 closures, i.e. **−40%** against the naive forecast |
| **Is this customer likely to leave?** | XGBoost on 12 customer-profile features | **ROC-AUC 0.751 · PR-AUC 0.611** · recall 79% |

All comparison tables are in [`comparison.md`](comparison.md).

## Contents

| File | Role |
|---|---|
| [`notebooks/01_kpi_time_series.ipynb`](notebooks/01_kpi_time_series.ipynb) | KPI choice, series construction, spikes, regimes, seasonality, ACF / PACF, stationarity |
| [`notebooks/02_lstm_rnn.ipynb`](notebooks/02_lstm_rnn.ipynb) | LSTM and RNN against 4 references, error analysis, 8-week forecast, second KPI (bonus) |
| [`notebooks/03_churn_ml.ipynb`](notebooks/03_churn_ml.ipynb) | Target leakage check, 3 models, tuning, sensitivity, calibration, SHAP |
| [`src/forecasting.py`](src/forecasting.py) | Chronological split, references, recurrent networks |
| [`src/churn.py`](src/churn.py) | Per-customer split, models, metrics, leakage audit |
| [`src/export_app.py`](src/export_app.py) | Export of the aggregates and model parameters for the application |
| [`src/train.py`](src/train.py) | Re-trains everything in one command and checks the published results |
| [`src/comparison_report.py`](src/comparison_report.py) | Generates `comparison.md` from the results |
| [`results/`](results/) | Metrics and aggregated series (JSON) written by the notebooks |
| `models/` | Saved models — **folder outside the repository** (`.gitignore`) |

## 1. The KPI and its time series

**KPI: weekly number of account closures.** It is the direct measure of churn, it is actionable (sizing the
retention teams) and it is available weekly (202 points, against 47 monthly).

| Finding | Decision |
|---|---|
| 5 weeks out of 202 carry **51%** of closures: mass operations | **Corrected** series (local median); the mass flag is kept for display |
| 11 weeks with no closure | Added as zeros; MAPE ruled out (undefined) |
| Three **regimes**: continuous flow → batch processing → continuous flow | Strict chronological split, no seasonal component |
| PACF useful up to 5 weeks | **8-week** sliding window |
| Non-stationary in log, stationary after differencing | Reference ARIMA with `d = 1` |

![Corrected series](../06_rapport/figures/04_corrected_series.png)

## 2. LSTM against simple references

Evaluated on the **last 40 weeks**, one-step-ahead, normalisation computed on the training part only.

| Model | MAE | RMSE | MAE vs naive |
|---|---:|---:|---:|
| 8-week moving median | 272.4 | 549.8 | −43% |
| **LSTM** (mean of 3 seeds) | **287.2** | **577.2** | **−40%** |
| Simple RNN | 323.6 | 607.7 | −32% |
| ARIMA(2, 1, 2) | 334.7 | 576.7 | −30% |
| 4-week moving average | 373.0 | 575.3 | −22% |
| Naive (last value) | 478.3 | 859.5 | — |

**Honest conclusion.** The LSTM proves its worth against the naive forecast, the simple RNN and ARIMA, but it does
not beat a moving median. With 134 training windows, a regime change between training and test and unpredictable
spikes, this is the expected result — and the project guide states it is acceptable *if demonstrated*. On the second
KPI (customers lost per week), the LSTM has the best MAE.

![LSTM vs references](../06_rapport/figures/04_lstm_vs_references.png)

## 3. Target leakage check

The file is a snapshot taken **after** the closures. For each column we measure the AUC obtained with the single
"value is blank" flag.

* **10 columns excluded** (blank AUC ≥ 0.80): closing date and reason, balance, opening date, account family,
  currency, amount, product group and line. `PRODUCT_STATUS` is excluded for its values.
* **Proof by example**: adding three blank flags raises the ROC-AUC from 0.751 to **0.951**. A score close to 100%
  signals a leak, not a good model.

## 4. Churn model

* **Grain: the customer** (319,040 customers with at least one account; 36.8% left). No customer has both an active
  and a closed account.
* **12 features** known before a departure: demographics (age, marital status, residence), relationship (tenure,
  number of accounts, type, segment, income), compliance (KYC score, complete file, last and next review).
* **Per-customer split** (`GroupShuffleSplit`, 70 / 15 / 15): no customer shared between two sets.
* **No rebalancing**: the imbalance is moderate; the precision / recall trade-off is set by the threshold.

| Model | ROC-AUC | PR-AUC | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| Baseline (average rate) | 0.500 | 0.369 | — | — | — |
| Logistic regression | 0.686 | 0.538 | 0.518 | 0.676 | 0.586 |
| Random Forest | 0.748 | 0.607 | 0.515 | 0.813 | 0.631 |
| **Tuned XGBoost (kept)** | **0.751** | **0.611** | 0.526 | 0.790 | **0.632** |

**Why XGBoost?** The best performer and best calibrated, it handles missing values natively and exports to readable
JSON, with no observation inside.

**What makes a customer leave** (SHAP values): an overdue file review, then age (25–44), a tenure of 5 to 10 years,
a single account. The "compliance" family carries 62% of the importance.

![SHAP values](../06_rapport/figures/04_churn_shap_summary.png)

**Business use.** Contacting the top 20% of scored customers reaches 35% of departures; the top 30%, half.

## Reproduce

```bash
python 04_machine_learning/src/train.py
```

The script re-trains both models and compares its metrics with the published ones: the gap must be zero.
To re-run a notebook: `jupyter nbconvert --to notebook --execute --inplace <notebook>`.

## Where are the models?

| File | Location | In the repository? |
|---|---|---|
| `final_model.pkl` (full XGBoost) | `04_machine_learning/models/` | **No** |
| `lstm_weekly_closures.keras` | `04_machine_learning/models/` | **No** |
| `churn_model.json` (trees: thresholds and leaf values) | `05_web_app/artifacts/` | Yes — no observation |
| `kpi_forecast.json` (aggregated weekly forecasts) | `05_web_app/artifacts/` | Yes — aggregates |

The application therefore needs neither TensorFlow nor a `.pkl` file: it reads rules and aggregates.
