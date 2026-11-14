"""Re-train the two final models in one command and check the published results.

    python 04_machine_learning/src/train.py              # churn + time series
    python 04_machine_learning/src/train.py --churn      # churn only
    python 04_machine_learning/src/train.py --series     # time series only

This script uses exactly the same functions as the notebooks (``churn.py``,
``forecasting.py``). It:

1. rebuilds the datasets from ``data/``;
2. re-trains the final XGBoost and the LSTM;
3. saves the models to ``04_machine_learning/models/`` (a folder **outside the repository**);
4. compares the metrics obtained with those published in ``results/*.json``:
   if everything is reproducible, the gap displayed is zero.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import churn  # noqa: E402
import forecasting  # noqa: E402
from vigie import config, data, features, series  # noqa: E402

warnings.filterwarnings("ignore")


def check(name: str, obtained: float, published: float, tolerance: float = 1e-3) -> bool:
    gap = abs(obtained - published)
    verdict = "OK" if gap <= tolerance else "GAP"
    print(f"   {name:<30} obtained {obtained:>9.4f}   published {published:>9.4f}   {verdict}")
    return gap <= tolerance


def train_churn(df: pd.DataFrame) -> bool:
    print("\n=== Churn model (XGBoost, customer grain) ===")
    accounts = data.account_grain(df)
    customers = data.customer_grain(df, accounts)
    _, X, y, groups = features.modelling_set(customers, data.reference_date(df))
    parts = churn.split(y, groups)
    print(f"   {len(y):,} customers · training {len(parts['train']):,} · validation {len(parts['validation']):,} · "
          f"test {len(parts['test']):,}")

    published = json.loads((config.ML_RESULTS / "churn_ml.json").read_text(encoding="utf-8"))
    model = churn.xgboost(**published["hyperparameters"]).fit(X.iloc[parts["train"]], y[parts["train"]])
    threshold = churn.f1_threshold(y[parts["validation"]], model.predict_proba(X.iloc[parts["validation"]])[:, 1])
    metrics = churn.evaluate(y[parts["test"]], model.predict_proba(X.iloc[parts["test"]])[:, 1], threshold)

    config.MODELS.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "columns": list(X.columns), "threshold": threshold}, config.MODELS / "final_model.pkl")
    print("   model saved: 04_machine_learning/models/final_model.pkl (outside the repository)")

    reference = published["model_comparison"]["Tuned XGBoost (kept)"]
    return all([check(k, metrics[k], reference[k]) for k in ("ROC-AUC", "PR-AUC", "Precision", "Recall", "F1")])


def train_series(df: pd.DataFrame) -> bool:
    print("\n=== KPI forecast (LSTM, weekly closures) ===")
    accounts = data.account_grain(df)
    raw = series.weekly_series(accounts.loc[accounts["CHURN"] == 1, "ACCT_CLOSE_DATE"])
    serie = series.correct_mass_weeks(raw, series.mass_weeks(raw))
    print(f"   {len(serie)} weeks · {int(raw.sum()):,} closures")

    result = forecasting.evaluate_kpi(serie)
    model = result.pop("_lstm_model")
    config.MODELS.mkdir(parents=True, exist_ok=True)
    model.save(config.MODELS / "lstm_weekly_closures.keras")
    print("   model saved: 04_machine_learning/models/lstm_weekly_closures.keras (outside the repository)")

    published = json.loads((config.ML_RESULTS / "kpi_forecast.json").read_text(encoding="utf-8"))
    reference = {row["Model"]: row for row in published["weekly_closures"]["comparison"]}
    ok = []
    for row in result["comparison"]:
        ok.append(check(f"MAE  {row['Model']}"[:30], row["MAE"], reference[row["Model"]]["MAE"], 0.5))
        ok.append(check(f"RMSE {row['Model']}"[:30], row["RMSE"], reference[row["Model"]]["RMSE"], 0.5))
    return all(ok)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--churn", action="store_true", help="re-train the churn model only")
    parser.add_argument("--series", action="store_true", help="re-train the LSTM only")
    args = parser.parse_args()
    everything = not (args.churn or args.series)

    print(f"{config.PROJECT_NAME} · {config.GROUP} — re-training the models")
    print("Source file:", data.fingerprint()["sha256"][:16], "…")
    df = data.load()
    outcomes = []
    if everything or args.churn:
        outcomes.append(train_churn(df))
    if everything or args.series:
        outcomes.append(train_series(df))
    reproducible = all(outcomes)
    print("\nPublished results reproduced exactly." if reproducible
          else "\nWARNING: gap with the published results (different library versions?).")
    return 0 if reproducible else 1


if __name__ == "__main__":
    sys.exit(main())
