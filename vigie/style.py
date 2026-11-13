"""Matplotlib house style: every figure in the project looks the same."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

from . import config

C = config.COLORS


def apply() -> None:
    """Turn on the VIGIE theme for every matplotlib figure."""
    mpl.rcParams.update({
        "figure.figsize": (9, 4.6),
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": C["mist"],
        "axes.labelcolor": C["text"],
        "axes.titlecolor": C["ink"],
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": C["mist"],
        "grid.linewidth": 0.8,
        "xtick.color": C["grey"],
        "ytick.color": C["grey"],
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "font.family": "DejaVu Sans",
        "axes.prop_cycle": mpl.cycler(color=config.PALETTE),
    })


def sign(fig, source: str = "data_churn.csv (anonymised dataset)") -> None:
    """Add the group signature and the source under the figure (traceability)."""
    fig.text(0.005, -0.02, f"{config.PROJECT_NAME} · {config.GROUP} · Source: {source}",
             fontsize=7.5, color=C["grey"], ha="left", va="top")


def save(fig, name: str, source: str | None = None) -> Path:
    """Sign the figure, then save it to 06_rapport/figures/."""
    sign(fig, source) if source else sign(fig)
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    path = config.FIGURES / f"{name}.png"
    fig.savefig(path)
    return path


def thousands(x, _pos=None) -> str:
    """Thousands separator: 12,345."""
    return f"{x:,.0f}"


def percent(x, _pos=None) -> str:
    return f"{x:.0%}"
