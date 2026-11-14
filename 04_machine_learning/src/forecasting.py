"""Forecasting a weekly KPI: LSTM / RNN and reference models.

Every forecast in this module is "one step ahead": to forecast week *t*, the model only
sees the weeks strictly before *t*. The simple references are evaluated under exactly
the same conditions, on the same weeks.

Protocol (identical for every model):

    |<--------------- training --------------->|<- validation ->|<---- test ---->|
                                                 (early stopping)   (never seen)

* the split respects the order of time (no shuffling);
* the ``log(1 + x)`` transform flattens the spikes;
* the normalisation (mean, standard deviation) is computed **on the training part only**.
"""

from __future__ import annotations

import os
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from vigie import config, series  # noqa: E402

TEST_SIZE = 40          # ≈ 20% of the series: the last 40 weeks
VALIDATION_SIZE = 20    # weeks set aside for early stopping
WINDOW = 8              # the model looks at the last 8 weeks (≈ 2 months)
UNITS = 32
SEEDS = (42, 7, 123)    # three initialisations: we report the mean and the spread
HORIZON = 8             # weeks forecast beyond the end of the series


@dataclass
class Split:
    """Indices of the chronological split and normalisation parameters."""
    n: int
    train_end: int
    validation_end: int
    mean: float
    std: float

    @classmethod
    def build(cls, values: np.ndarray) -> "Split":
        n = len(values)
        validation_end = n - TEST_SIZE
        train_end = validation_end - VALIDATION_SIZE
        z = np.log1p(values[:train_end])
        return cls(n, train_end, validation_end, float(z.mean()), float(z.std()))

    def normalise(self, values) -> np.ndarray:
        return (np.log1p(np.asarray(values, dtype=float)) - self.mean) / self.std

    def denormalise(self, z) -> np.ndarray:
        return np.clip(np.expm1(np.asarray(z, dtype=float) * self.std + self.mean), 0, None)


# --------------------------------------------------------------------------
# Reference models (one line each: that is the whole point)
# --------------------------------------------------------------------------
def references(values: np.ndarray, start: int) -> dict[str, np.ndarray]:
    """One-step-ahead forecasts of the simple models, for weeks ``start`` … end."""
    v = np.asarray(values, dtype=float)
    t = range(start, len(v))
    return {
        "Naive (last value)": np.array([v[i - 1] for i in t]),
        "4-week moving average": np.array([v[i - 4:i].mean() for i in t]),
        "8-week moving median": np.array([np.median(v[i - 8:i]) for i in t]),
    }


def arima(values: np.ndarray, start: int) -> tuple[np.ndarray, tuple]:
    """ARIMA on log(1 + x): order chosen by AIC before ``start``, then one-step-ahead forecasts."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    z = np.log1p(np.asarray(values, dtype=float))
    best, best_aic = None, np.inf
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p in range(3):
            for d in range(2):
                for q in range(3):
                    try:
                        res = SARIMAX(z[:start], order=(p, d, q), trend="c" if d == 0 else "n").fit(disp=False)
                    except Exception:
                        continue
                    if res.aic < best_aic:
                        best, best_aic = (p, d, q), res.aic
        res = SARIMAX(z[:start], order=best, trend="c" if best[1] == 0 else "n").fit(disp=False)
        full = res.apply(z)                                   # same parameters, whole series
        forecast = full.predict(start=start, end=len(z) - 1)  # one step ahead, no re-estimation
    return np.clip(np.expm1(forecast), 0, None), best


# --------------------------------------------------------------------------
# Recurrent networks
# --------------------------------------------------------------------------
def build_network(layer_type: str = "lstm", window: int = WINDOW, units: int = UNITS):
    """One recurrent layer + one output: deliberately small (≈ 200 training points)."""
    import tensorflow as tf
    from tensorflow import keras

    tf.get_logger().setLevel("ERROR")
    layer = {"lstm": keras.layers.LSTM, "rnn": keras.layers.SimpleRNN}[layer_type]
    model = keras.Sequential([
        keras.layers.Input((window, 1)),
        layer(units),
        keras.layers.Dense(1),
    ])
    # Absolute error: less sensitive to spikes than squared error.
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.005), loss="mae")
    return model


@dataclass
class NetworkResult:
    layer_type: str
    seed: int
    test_forecast: np.ndarray
    epochs: int
    history: dict = field(default_factory=dict)
    model: object = None


def train_network(values: np.ndarray, split: Split, layer_type: str = "lstm",
                  seed: int = config.SEED) -> NetworkResult:
    """Train a network and return its one-step-ahead forecasts over the test period."""
    from tensorflow import keras

    keras.utils.set_random_seed(seed)
    z = split.normalise(values)
    X, y = series.windows(z, WINDOW)
    target = np.arange(WINDOW, split.n)                      # index of the week each window forecasts
    train = target < split.train_end
    validation = (target >= split.train_end) & (target < split.validation_end)
    test = target >= split.validation_end

    model = build_network(layer_type)
    stop = keras.callbacks.EarlyStopping(monitor="val_loss", patience=30, restore_best_weights=True)
    hist = model.fit(X[train][..., None], y[train], validation_data=(X[validation][..., None], y[validation]),
                     epochs=300, batch_size=16, shuffle=True, verbose=0, callbacks=[stop])
    forecast = split.denormalise(model.predict(X[test][..., None], verbose=0).ravel())
    return NetworkResult(layer_type, seed, forecast, len(hist.history["loss"]),
                         {k: [float(v) for v in vals] for k, vals in hist.history.items()}, model)


def forecast_future(model, values: np.ndarray, split: Split, horizon: int = HORIZON) -> np.ndarray:
    """Recursive forecast: each forecast week becomes an input for the next one."""
    window = list(split.normalise(values[-WINDOW:]))
    outputs = []
    for _ in range(horizon):
        x = np.asarray(window[-WINDOW:], dtype="float32")[None, :, None]
        z = float(model.predict(x, verbose=0).ravel()[0])
        outputs.append(z)
        window.append(z)
    return split.denormalise(outputs)


# --------------------------------------------------------------------------
# Full evaluation of one KPI
# --------------------------------------------------------------------------
def evaluate_kpi(serie: pd.Series, seeds=SEEDS, with_arima: bool = True) -> dict:
    """Compare LSTM, RNN and references over the last ``TEST_SIZE`` weeks of a series.

    Returns a serialisable dictionary (comparison table, forecasts, future forecast).
    """
    values = serie.to_numpy(dtype=float)
    split = Split.build(values)
    actual = values[split.validation_end:]
    test_weeks = serie.index[split.validation_end:]

    forecasts = references(values, split.validation_end)
    rows = [{"Model": name, "Type": "Reference", "MAE": series.mae(actual, p), "RMSE": series.rmse(actual, p)}
            for name, p in forecasts.items()]
    arima_order = None
    if with_arima:
        forecasts["ARIMA"], arima_order = arima(values, split.validation_end)
        rows.append({"Model": f"ARIMA{arima_order}", "Type": "Reference",
                     "MAE": series.mae(actual, forecasts["ARIMA"]), "RMSE": series.rmse(actual, forecasts["ARIMA"])})

    networks = {}
    for layer_type, name in (("lstm", "LSTM"), ("rnn", "Simple RNN")):
        runs = [train_network(values, split, layer_type, s) for s in seeds]
        maes = [series.mae(actual, r.test_forecast) for r in runs]
        rmses = [series.rmse(actual, r.test_forecast) for r in runs]
        networks[layer_type] = runs
        forecasts[name] = runs[0].test_forecast          # main seed (42) for the charts
        rows.append({"Model": name, "Type": "Deep Learning", "MAE": float(np.mean(maes)),
                     "RMSE": float(np.mean(rmses)), "MAE std": float(np.std(maes)),
                     "RMSE std": float(np.std(rmses)), "Epochs": [r.epochs for r in runs]})

    lstm = networks["lstm"][0]
    future = forecast_future(lstm.model, values, split)
    # Empirical interval: 10% / 90% quantiles of the actual / forecast ratio observed on the test.
    ratio = np.log1p(actual) - np.log1p(lstm.test_forecast)
    low, high = np.quantile(ratio, [0.10, 0.90])
    future_weeks = pd.date_range(serie.index[-1] + pd.Timedelta(weeks=1), periods=HORIZON, freq="W-MON")

    return {
        "split": {"weeks": split.n, "train": split.train_end, "validation": VALIDATION_SIZE,
                  "test": TEST_SIZE, "window": WINDOW, "test_start": str(test_weeks[0].date()),
                  "test_end": str(test_weeks[-1].date())},
        "comparison": rows,
        "arima_order": list(arima_order) if arima_order else None,
        "test": {"weeks": [str(s.date()) for s in test_weeks], "actual": [int(v) for v in actual],
                 "forecasts": {name: [round(float(v), 1) for v in p] for name, p in forecasts.items()}},
        "future": {"weeks": [str(s.date()) for s in future_weeks],
                   "forecast": [round(float(v), 1) for v in future],
                   "low": [round(float(np.expm1(np.log1p(v) + low)), 1) for v in future],
                   "high": [round(float(np.expm1(np.log1p(v) + high)), 1) for v in future]},
        "lstm_history": lstm.history,
        "_lstm_model": lstm.model,       # removed before serialisation
    }
