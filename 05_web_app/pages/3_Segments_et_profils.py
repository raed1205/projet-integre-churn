"""Segmentation : taux de churn par axe et profil de valeur par segment (agrégats uniquement)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import charte
from utils.artefacts import DepotArtefacts



@st.cache_data
def charger() -> dict:
    return DepotArtefacts().kpi_synthese()


kpi = charger()
g = kpi["global"]

charte.entete("Segments et profils", "Où se concentre le churn, et à quoi ressemblent les segments de clientèle.")
st.write("")

onglet_client, onglet_compte, onglet_valeur = st.tabs(["Par profil client", "Par type de compte", "Valeur des segments"])


def graphique(donnees: list[dict], titre: str, moyenne: float, unite: str):
    table = pd.DataFrame(donnees)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=table["modalite"], y=table["taux_churn"], name="Taux de churn",
        marker_color=[charte.CHURN if v > moyenne else charte.RETENTION for v in table["taux_churn"]],
        text=[charte.pourcent(v, 0) for v in table["taux_churn"]], textposition="outside",
        customdata=[charte.nombre(v) for v in table["effectif"]],
        hovertemplate="%{x}<br>Taux de churn : %{y:.1%}<br>" + unite + " : %{customdata}<extra></extra>"))
    fig.add_hline(y=moyenne, line_dash="dash", line_color=charte.ENCRE,
                  annotation_text=f"moyenne {charte.pourcent(moyenne)}", annotation_position="top left")
    fig.update_yaxes(tickformat=".0%", range=[0, min(1.12, table["taux_churn"].max() * 1.22)])
    fig.update_layout(title=titre)
    return charte.mise_en_forme(fig, 400), table


with onglet_client:
    axe = st.selectbox("Axe d'analyse", list(kpi["axes_client"].keys()))
    fig, table = graphique(kpi["axes_client"][axe], f"Taux de churn par {axe.lower()} — grain client",
                           g["taux_churn_clients"], "Clients")
    st.plotly_chart(fig, use_container_width=True)
    ecart = table.loc[table["taux_churn"].idxmax()], table.loc[table["taux_churn"].idxmin()]
    st.markdown(f"Le taux de churn va de **{charte.pourcent(ecart[1]['taux_churn'])}** ({ecart[1]['modalite']}) à "
                f"**{charte.pourcent(ecart[0]['taux_churn'])}** ({ecart[0]['modalite']}).")
    table["Part des clients"] = (table["effectif"] / table["effectif"].sum()).map(charte.pourcent)
    table["effectif"] = table["effectif"].map(charte.nombre)
    table["taux_churn"] = table["taux_churn"].map(charte.pourcent)
    st.dataframe(table.rename(columns={"modalite": axe, "effectif": "Clients", "taux_churn": "Taux de churn"}),
                 use_container_width=True, hide_index=True)

with onglet_compte:
    axe = st.selectbox("Axe d'analyse", list(kpi["axes_compte"].keys()))
    fig, table = graphique(kpi["axes_compte"][axe], f"Taux de churn par {axe.lower()} — grain compte",
                           g["taux_churn_comptes"], "Comptes")
    st.plotly_chart(fig, use_container_width=True)
    charte.note(
        "<b>Attention à la modalité « Non renseigné ».</b> Pour environ deux comptes clos sur trois, la famille, la devise "
        "et le produit ne sont plus renseignés : ces comptes forment une modalité à 100 % de churn. Le taux des autres "
        "modalités est donc <b>sous-estimé</b>. Ces axes décrivent le portefeuille ; ils ne servent pas à prédire le churn "
        "(ce serait une fuite de cible).")
    table["effectif"] = table["effectif"].map(charte.nombre)
    table["taux_churn"] = table["taux_churn"].map(charte.pourcent)
    st.dataframe(table.rename(columns={"modalite": axe, "effectif": "Comptes", "taux_churn": "Taux de churn"}),
                 use_container_width=True, hide_index=True)

    st.markdown("##### Motifs de clôture déclarés")
    motifs = pd.DataFrame(kpi["motifs_cloture"])
    motifs["Part"] = (motifs["comptes"] / motifs["comptes"].sum()).map(charte.pourcent)
    motifs["comptes"] = motifs["comptes"].map(charte.nombre)
    st.dataframe(motifs.rename(columns={"motif": "Motif", "comptes": "Comptes clos"}), use_container_width=True, hide_index=True)
    st.caption("Le motif « Autre » domine : le motif déclaré n'explique pas le churn, d'où l'intérêt d'un modèle fondé sur le profil.")

with onglet_valeur:
    segments = pd.DataFrame(kpi["segments"])
    fig = go.Figure(go.Scatter(
        x=segments["comptes_par_client"], y=segments["taux_churn"], mode="markers+text", text=segments["segment"],
        textposition="top center",
        marker=dict(size=(segments["clients"] ** 0.5) / 6 + 14, color=charte.ENCRE, opacity=.85,
                    line=dict(color="white", width=2)),
        customdata=[charte.nombre(v) for v in segments["clients"]],
        hovertemplate="%{text}<br>Comptes par client : %{x:.2f}<br>Taux de churn : %{y:.1%}<br>Clients : %{customdata}<extra></extra>"))
    fig.update_yaxes(tickformat=".0%", title="Taux de churn", range=[0.28, 0.42])
    fig.update_xaxes(title="Nombre moyen de comptes par client (équipement)")
    fig.update_layout(title="Segments : équipement et churn (taille de la bulle = nombre de clients)")
    st.plotly_chart(charte.mise_en_forme(fig, 400), use_container_width=True)

    affichage = pd.DataFrame({
        "Segment": segments["segment"],
        "Clients": segments["clients"].map(charte.nombre),
        "Taux de churn": segments["taux_churn"].map(charte.pourcent),
        "Ancienneté moyenne": segments["anciennete_moyenne"].map(lambda v: f"{charte.nombre(v, 1)} ans"),
        "Comptes par client": segments["comptes_par_client"].map(lambda v: charte.nombre(v, 2)),
        "Multi-équipés": segments["part_multi_equipes"].map(charte.pourcent),
        "Dossiers complets": segments["part_dossier_complet"].map(charte.pourcent),
        "Solde médian (clients actifs)": segments["solde_median_clients_actifs"].map(charte.nombre),
    })
    st.dataframe(affichage, use_container_width=True, hide_index=True)
    st.caption("Solde médian : somme des soldes des comptes actifs d'un client, médiane par segment. Montants arrondis et "
               "plafonnés par l'anonymisation : ils servent à comparer les segments, pas à mesurer un encours réel.")

charte.pied()
