"""Weekly KPI series and the treatment of mass operations."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def weekly_series(dates: pd.Series, start=None, end=None) -> pd.Series:
    """Number of events per week (Monday), **zero weeks included**.

    ``dates`` must already be at the right grain (one event = one row).
    """
    d = dates.dropna()
    counts = d.groupby(d).size()
    start = start if start is not None else counts.index.min()
    end = end if end is not None else counts.index.max()
    index = pd.date_range(start, end, freq="W-MON")
    series = counts.reindex(index, fill_value=0).astype(int)
    series.index.name = "week"
    return series


def mass_weeks(series: pd.Series, share: float = config.MASS_SHARE) -> pd.DatetimeIndex:
    """Mass operations = the smallest set of weeks that adds up to ``share`` of the volume.

    A simple rule with no arbitrary threshold: weeks are sorted by decreasing volume
    and we stop as soon as the cumulative share reaches ``share`` (50% by default).
    """
    ranked = series.sort_values(ascending=False)
    cumulative = ranked.cumsum() / ranked.sum()
    n = int(np.argmax(cumulative.values >= share)) + 1
    return ranked.index[:n].sort_values()


def correct_mass_weeks(series: pd.Series, mass: pd.DatetimeIndex, half_window: int = 4) -> pd.Series:
    """Corrected series: each mass week is replaced by the local median.

    The median is taken over the ``half_window`` weeks before and after, leaving out
    the other mass weeks. The ordinary volume is kept; the exceptional operation is removed.
    """
    corrected = series.astype(float).copy()
    ordinary = series.astype(float).copy()
    ordinary[mass] = np.nan
    for week in mass:
        pos = series.index.get_loc(week)
        neighbours = ordinary.iloc[max(0, pos - half_window): pos + half_window + 1]
        corrected[week] = float(np.nanmedian(neighbours.values))
    return corrected.round().astype(int)


def windows(values: np.ndarray, size: int) -> tuple[np.ndarray, np.ndarray]:
    """Sliding windows: X[i] = ``size`` weeks, y[i] = the following week."""
    X, y = [], []
    for i in range(len(values) - size):
        X.append(values[i: i + size])
        y.append(values[i + size])
    return np.asarray(X, dtype="float32"), np.asarray(y, dtype="float32")


def mae(y, p) -> float:
    return float(np.mean(np.abs(np.asarray(y, float) - np.asarray(p, float))))


def rmse(y, p) -> float:
    return float(np.sqrt(np.mean((np.asarray(y, float) - np.asarray(p, float)) ** 2)))
