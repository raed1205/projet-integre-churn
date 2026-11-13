"""Charte graphique matplotlib : toutes les figures du projet se ressemblent."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

from . import config

C = config.COULEURS


def appliquer() -> None:
    """Active le thème VIGIE pour toutes les figures matplotlib / seaborn."""
    mpl.rcParams.update({
        "figure.figsize": (9, 4.6),
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": C["brume"],
        "axes.labelcolor": C["texte"],
        "axes.titlecolor": C["encre"],
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": C["brume"],
        "grid.linewidth": 0.8,
        "xtick.color": C["gris"],
        "ytick.color": C["gris"],
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "font.family": "DejaVu Sans",
        "axes.prop_cycle": mpl.cycler(color=config.PALETTE),
    })


def signer(fig, source: str = "data_churn.csv (jeu anonymisé)") -> None:
    """Ajoute la signature du groupe et la source sous la figure (traçabilité)."""
    fig.text(
        0.005, -0.02,
        f"{config.NOM_PROJET} · {config.GROUPE} · Source : {source}",
        fontsize=7.5, color=C["gris"], ha="left", va="top",
    )


def enregistrer(fig, nom: str, source: str | None = None) -> Path:
    """Signe puis enregistre la figure dans 06_rapport/figures/."""
    signer(fig, source) if source else signer(fig)
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    chemin = config.FIGURES / f"{nom}.png"
    fig.savefig(chemin)
    return chemin


def milliers(x, _pos=None) -> str:
    """Format français des milliers : 12 345."""
    return f"{x:,.0f}".replace(",", " ")


def pourcent(x, _pos=None) -> str:
    return f"{x:.0%}"


def nouvelle_figure(**kw):
    appliquer()
    return plt.subplots(**kw)
