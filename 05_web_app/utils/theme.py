"""Visual identity and display components shared by every page."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

NAME = "VIGIE"
TAGLINE = "See churn coming. Act before the account closes."
GROUP = "Group BI 5"
SCHOOL = "ESPRIT School of Business · Business Computing (BI) · Integrated Project 2026"
TEAM = [
    ("Raed Meddeb", "Project lead · Churn modelling (Machine Learning)", "raed.meddeb@esprit.tn"),
    ("Ibrahim Grira", "Web application, UML & DevOps (tests, CI)", "ibrahim.grira@esprit.tn"),
    ("Salsabil Ben Elhadj", "Data Warehouse & ETL (Talend, PostgreSQL)", "BenElhadj.Salsabil@esprit.tn"),
    ("Salah Chebbi", "Time series & Deep Learning (LSTM)", "salah.chebbi@esprit.tn"),
    ("Ines Ayed", "Power BI reporting, DAX & data quality", "ines.ayed@esprit.tn"),
]
SUPERVISORS = ["Aymen Ben Brik", "Hela Hammami"]

INK, CHURN, RETENTION, AMBER, SKY = "#14213D", "#D62839", "#2A9D8F", "#F4A261", "#457B9D"
MIST, PAPER, GREY, TEXT = "#E9ECEF", "#FAFAF7", "#6B7280", "#1F2937"

ASSETS = Path(__file__).resolve().parents[1] / "assets"

CSS = f"""
<style>
  .block-container {{ padding-top: 2.2rem; max-width: 1180px; }}
  h1, h2, h3 {{ color: {INK}; letter-spacing: -0.01em; }}
  [data-testid="stSidebar"] {{ background: {INK}; }}
  [data-testid="stSidebar"] * {{ color: #F3F4F6 !important; }}
  .vigie-header {{ display: flex; align-items: center; gap: 16px; margin-bottom: 4px; }}
  .vigie-header img {{ width: 58px; height: 58px; }}
  .vigie-header .title {{ font-size: 1.9rem; font-weight: 800; color: {INK}; line-height: 1.1; }}
  .vigie-header .subtitle {{ color: {GREY}; font-size: .98rem; }}
  .vigie-card {{ background: #fff; border: 1px solid {MIST}; border-radius: 14px; padding: 16px 18px;
                height: 100%; box-shadow: 0 1px 2px rgba(20,33,61,.04); }}
  .vigie-card .label {{ color: {GREY}; font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }}
  .vigie-card .value {{ color: {INK}; font-size: 1.75rem; font-weight: 800; line-height: 1.25; }}
  .vigie-card .detail {{ color: {GREY}; font-size: .82rem; }}
  .vigie-card.accent {{ border-left: 5px solid {CHURN}; }}
  .vigie-card.green {{ border-left: 5px solid {RETENTION}; }}
  .vigie-pill {{ display: inline-block; padding: 4px 14px; border-radius: 999px; color: #fff;
                font-weight: 700; font-size: .95rem; }}
  .vigie-note {{ background: #fff; border: 1px solid {MIST}; border-left: 5px solid {SKY}; border-radius: 10px;
                padding: 12px 16px; color: {TEXT}; font-size: .9rem; }}
  .vigie-footer {{ color: {GREY}; font-size: .78rem; border-top: 1px solid {MIST}; margin-top: 2.2rem; padding-top: .8rem; }}
</style>
"""


def number(x: float, decimals: int = 0) -> str:
    """Thousands separator: 12,345.6."""
    return f"{x:,.{decimals}f}"


def percent(x: float, decimals: int = 1) -> str:
    return f"{100 * x:.{decimals}f}%"


def _logo_base64() -> str:
    return base64.b64encode((ASSETS / "logo.svg").read_bytes()).decode()


def configure() -> None:
    """Called once by app.py: page configuration, styles, sidebar."""
    st.set_page_config(page_title=f"{NAME} · {GROUP}", page_icon=str(ASSETS / "logo.svg"), layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"### {NAME}")
        st.caption(TAGLINE)
        st.caption(f"**{GROUP}**  \n" + "  \n".join(name for name, _, _ in TEAM))
        st.caption("Supervisors: " + " · ".join(SUPERVISORS))
        st.caption("Aggregates and fictitious profiles only. No customer data.")


def header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""<div class="vigie-header">
              <img src="data:image/svg+xml;base64,{_logo_base64()}" alt="VIGIE"/>
              <div><div class="title">{title}</div><div class="subtitle">{subtitle}</div></div>
            </div>""", unsafe_allow_html=True)


def card(label: str, value: str, detail: str = "", style: str = "") -> None:
    st.markdown(
        f"""<div class="vigie-card {style}">
              <div class="label">{label}</div>
              <div class="value">{value}</div>
              <div class="detail">{detail}</div>
            </div>""", unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="vigie-note">{text}</div>', unsafe_allow_html=True)


def footer() -> None:
    st.markdown(
        f'<div class="vigie-footer">{NAME} · {GROUP} · {SCHOOL}<br>'
        "Anonymised data: dates shifted, amounts rounded. "
        "The application only displays aggregates and fictitious profiles.</div>", unsafe_allow_html=True)


def styled(fig, height: int = 380):
    """Apply the house style to a plotly figure."""
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=48, b=10), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT, size=13),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0),
    )
    fig.update_xaxes(gridcolor=MIST, zeroline=False)
    fig.update_yaxes(gridcolor=MIST, zeroline=False)
    return fig
