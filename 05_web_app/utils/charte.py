"""Charte graphique et composants d'affichage partagés par toutes les pages."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

NOM = "VIGIE"
SIGNATURE = "Voir le churn venir, agir avant la clôture."
GROUPE = "Groupe BI 5"
ECOLE = "ESPRIT School of Business · L3 Business Computing BI · Projet Intégré 2026"
EQUIPE = [
    ("Raed Meddeb", "Chef de projet · Machine Learning & application web"),
    ("Salsabil Ben Elhadj", "Data Warehouse & ETL (Talend, PostgreSQL)"),
    ("Salah Chebbi", "Séries temporelles & Deep Learning (LSTM)"),
    ("Ines Ayed", "Reporting Power BI, DAX & qualité des données"),
]
TUTEURS = ["Aymen Ben Brik", "Hela Hammami"]

ENCRE, CHURN, RETENTION, AMBRE, CIEL = "#14213D", "#D62839", "#2A9D8F", "#F4A261", "#457B9D"
BRUME, PAPIER, GRIS, TEXTE = "#E9ECEF", "#FAFAF7", "#6B7280", "#1F2937"

ASSETS = Path(__file__).resolve().parents[1] / "assets"

CSS = f"""
<style>
  .block-container {{ padding-top: 2.2rem; max-width: 1180px; }}
  h1, h2, h3 {{ color: {ENCRE}; letter-spacing: -0.01em; }}
  [data-testid="stSidebar"] {{ background: {ENCRE}; }}
  [data-testid="stSidebar"] * {{ color: #F3F4F6 !important; }}
  [data-testid="stSidebarNav"] a[aria-current="page"] {{ background: rgba(255,255,255,.12); }}
  .vigie-entete {{ display: flex; align-items: center; gap: 16px; margin-bottom: 4px; }}
  .vigie-entete img {{ width: 58px; height: 58px; }}
  .vigie-entete .titre {{ font-size: 1.9rem; font-weight: 800; color: {ENCRE}; line-height: 1.1; }}
  .vigie-entete .sous-titre {{ color: {GRIS}; font-size: .98rem; }}
  .vigie-carte {{ background: #fff; border: 1px solid {BRUME}; border-radius: 14px; padding: 16px 18px;
                 height: 100%; box-shadow: 0 1px 2px rgba(20,33,61,.04); }}
  .vigie-carte .etiquette {{ color: {GRIS}; font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }}
  .vigie-carte .valeur {{ color: {ENCRE}; font-size: 1.75rem; font-weight: 800; line-height: 1.25; }}
  .vigie-carte .detail {{ color: {GRIS}; font-size: .82rem; }}
  .vigie-carte.accent {{ border-left: 5px solid {CHURN}; }}
  .vigie-carte.vert {{ border-left: 5px solid {RETENTION}; }}
  .vigie-pastille {{ display: inline-block; padding: 4px 14px; border-radius: 999px; color: #fff;
                    font-weight: 700; font-size: .95rem; }}
  .vigie-note {{ background: #fff; border: 1px solid {BRUME}; border-left: 5px solid {CIEL}; border-radius: 10px;
                padding: 12px 16px; color: {TEXTE}; font-size: .9rem; }}
  .vigie-pied {{ color: {GRIS}; font-size: .78rem; border-top: 1px solid {BRUME}; margin-top: 2.2rem; padding-top: .8rem; }}
</style>
"""


def nombre(x: float, decimales: int = 0) -> str:
    """Format français : 12 345,6."""
    texte = f"{x:,.{decimales}f}".replace(",", " ").replace(".", ",")
    return texte


def pourcent(x: float, decimales: int = 1) -> str:
    return f"{100 * x:.{decimales}f}".replace(".", ",") + " %"


def _logo_base64() -> str:
    return base64.b64encode((ASSETS / "logo.svg").read_bytes()).decode()


def configurer() -> None:
    """Appelée une fois par app.py : configuration de la page, styles, barre latérale."""
    st.set_page_config(page_title=f"{NOM} · {GROUPE}", page_icon=str(ASSETS / "logo.svg"), layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"### {NOM}")
        st.caption(SIGNATURE)
        st.caption(f"**{GROUPE}**  \n" + "  \n".join(nom for nom, _ in EQUIPE))
        st.caption("Tuteurs : " + " · ".join(TUTEURS))
        st.caption("Agrégats et profils fictifs uniquement. Aucune donnée client.")


def entete(titre: str, sous_titre: str) -> None:
    st.markdown(
        f"""<div class="vigie-entete">
              <img src="data:image/svg+xml;base64,{_logo_base64()}" alt="VIGIE"/>
              <div><div class="titre">{titre}</div><div class="sous-titre">{sous_titre}</div></div>
            </div>""", unsafe_allow_html=True)


def carte(etiquette: str, valeur: str, detail: str = "", style: str = "") -> None:
    st.markdown(
        f"""<div class="vigie-carte {style}">
              <div class="etiquette">{etiquette}</div>
              <div class="valeur">{valeur}</div>
              <div class="detail">{detail}</div>
            </div>""", unsafe_allow_html=True)


def note(texte: str) -> None:
    st.markdown(f'<div class="vigie-note">{texte}</div>', unsafe_allow_html=True)


def pied() -> None:
    st.markdown(
        f'<div class="vigie-pied">{NOM} · {GROUPE} · {ECOLE}<br>'
        "Données anonymisées : dates décalées, montants arrondis. "
        "L'application n'affiche que des agrégats et des profils fictifs.</div>", unsafe_allow_html=True)


def mise_en_forme(fig, hauteur: int = 380):
    """Applique la charte à une figure plotly."""
    fig.update_layout(
        height=hauteur, margin=dict(l=10, r=10, t=48, b=10), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXTE, size=13),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0),
        separators=", ",
    )
    fig.update_xaxes(gridcolor=BRUME, zeroline=False)
    fig.update_yaxes(gridcolor=BRUME, zeroline=False)
    return fig
