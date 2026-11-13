"""Page d'accueil : les KPI de synthèse du churn, tous agrégés."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from utils import charte
from utils.artefacts import DepotArtefacts


@st.cache_data
def charger() -> tuple[dict, dict]:
    depot = DepotArtefacts()
    return depot.kpi_synthese(), depot.prevision_kpi()


kpi, prevision = charger()
g = kpi["global"]

charte.entete("VIGIE — vue d'ensemble du churn", charte.SIGNATURE)
st.write("")

# ------------------------------------------------------------------ KPI de synthèse
c1, c2, c3, c4 = st.columns(4)
with c1:
    charte.carte("Taux de churn · comptes", charte.pourcent(g["taux_churn_comptes"]),
                 f"{charte.nombre(g['comptes_clos'])} comptes clos sur {charte.nombre(g['comptes'])}", "accent")
with c2:
    charte.carte("Taux de churn · clients", charte.pourcent(g["taux_churn_clients"]),
                 f"{charte.nombre(g['clients_partis'])} clients partis sur {charte.nombre(g['clients_avec_compte'])}", "accent")
with c3:
    charte.carte("Comptes actifs", charte.nombre(g["comptes_actifs"]),
                 f"solde médian : {charte.nombre(g['solde_median_comptes_actifs'])}", "vert")
with c4:
    charte.carte("Ancienneté moyenne", f"{charte.nombre(g['anciennete_moyenne_clients'], 1)} ans",
                 f"{charte.pourcent(g['part_multi_equipes'])} de clients multi-équipés", "vert")

st.write("")
c5, c6, c7, c8 = st.columns(4)
with c5:
    charte.carte("Clients", charte.nombre(g["clients"]),
                 f"dont {charte.nombre(g['clients'] - g['clients_avec_compte'])} sans compte")
with c6:
    charte.carte("Dossiers complets", charte.pourcent(g["part_dossier_complet"]), "clients ayant au moins un compte")
with c7:
    charte.carte("Revues en retard", charte.pourcent(g["part_revue_en_retard"]), "premier signal de risque du modèle")
with c8:
    charte.carte("Comptes débiteurs", charte.pourcent(g["part_comptes_debiteurs_actifs"]), "parmi les comptes actifs")

st.write("")
charte.note(
    "<b>Un taux se lit toujours à son grain.</b> "
    f"Le même fichier donne {charte.pourcent(g['taux_churn_lignes'])} de churn par ligne, "
    f"{charte.pourcent(g['taux_churn_comptes'])} par compte et {charte.pourcent(g['taux_churn_clients'])} par client "
    f"({charte.pourcent(g['taux_churn_tous_clients'])} en comptant aussi les clients sans compte). "
    "Tous les indicateurs de cette application sont calculés au grain compte ou au grain client, jamais par ligne.")

# ------------------------------------------------------------------ Qui part ?
st.markdown("### Qui part ?")
gauche, droite = st.columns([1, 2.4])
with gauche:
    axe = st.radio("Lire le taux de churn par", list(kpi["axes_client"].keys())[:6], index=0)
    st.caption("Grain client. Les modalités de moins de 20 clients ne sont pas affichées.")
donnees_axe = kpi["axes_client"][axe]
moyenne = g["taux_churn_clients"]
with droite:
    fig = go.Figure(go.Bar(
        x=[d["modalite"] for d in donnees_axe], y=[d["taux_churn"] for d in donnees_axe],
        marker_color=[charte.CHURN if d["taux_churn"] > moyenne else charte.RETENTION for d in donnees_axe],
        text=[charte.pourcent(d["taux_churn"], 0) for d in donnees_axe], textposition="outside",
        customdata=[charte.nombre(d["effectif"]) for d in donnees_axe],
        hovertemplate="%{x}<br>Taux de churn : %{y:.1%}<br>Clients : %{customdata}<extra></extra>"))
    fig.add_hline(y=moyenne, line_dash="dash", line_color=charte.ENCRE,
                  annotation_text=f"moyenne {charte.pourcent(moyenne)}", annotation_position="top left")
    fig.update_yaxes(tickformat=".0%", range=[0, max(d["taux_churn"] for d in donnees_axe) * 1.22])
    fig.update_layout(title=f"Taux de churn par {axe.lower()}")
    st.plotly_chart(charte.mise_en_forme(fig), use_container_width=True)

# ------------------------------------------------------------------ Le KPI dans le temps
st.markdown("### Les clôtures dans le temps")
h = prevision["historique"]
part_masse = sum(h["brute"][h["semaines"].index(s)] for s in h["semaines_de_masse"]) / sum(h["brute"])
fig = go.Figure()
fig.add_trace(go.Scatter(x=h["semaines"], y=h["corrigee"], mode="lines", name="Clôtures par semaine (série corrigée)",
                         line=dict(color=charte.ENCRE, width=1.6), fill="tozeroy", fillcolor="rgba(20,33,61,.07)"))
for s in h["semaines_de_masse"]:
    fig.add_vline(x=s, line_dash="dot", line_color=charte.CHURN, opacity=.6)
fig.add_trace(go.Scatter(x=prevision["futur"]["semaines"], y=prevision["futur"]["prevision"], mode="lines+markers",
                         name="Prévision LSTM (8 semaines)", line=dict(color=charte.CHURN, width=2.4)))
fig.update_layout(title="Comptes clos par semaine — pointillés rouges : opérations de masse retirées de la série")
st.plotly_chart(charte.mise_en_forme(fig, 340), use_container_width=True)
st.caption(
    f"{len(h['semaines'])} semaines. {len(h['semaines_de_masse'])} opérations de masse concentrent "
    f"{charte.pourcent(part_masse, 0)} des clôtures ; elles sont remplacées par un niveau ordinaire. "
    + prevision["note_dates"])

st.markdown("### Aller plus loin")
a, b, c = st.columns(3)
with a:
    st.page_link("pages/1_Prediction_du_churn.py", label="**Prédire le risque d'un profil**", icon="🎯")
    st.caption("Saisir un profil fictif, obtenir son score et les facteurs qui l'expliquent.")
with b:
    st.page_link("pages/2_Prevision_du_KPI.py", label="**Prévoir les clôtures**", icon="📈")
    st.caption("La prévision du LSTM, comparée à des règles simples.")
with c:
    st.page_link("pages/3_Segments_et_profils.py", label="**Explorer les segments**", icon="🧭")
    st.caption("Taux de churn et profil de valeur par segment.")

charte.pied()
