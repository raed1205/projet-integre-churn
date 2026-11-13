"""Prévision du KPI : clôtures hebdomadaires, prévision LSTM et comparaison aux références."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import charte
from utils.artefacts import DepotArtefacts



@st.cache_data
def charger() -> dict:
    return DepotArtefacts().prevision_kpi()


p = charger()
h, test, futur, dec = p["historique"], p["test"], p["futur"], p["decoupage"]
comparaison = pd.DataFrame(p["comparaison"]).set_index("Modèle")
naive = comparaison.loc["Naïve (dernière valeur)"]
lstm = comparaison.loc["LSTM"]
meilleur = comparaison["MAE"].idxmin()

charte.entete("Prévision du KPI", "Nombre de comptes clos par semaine — prévision par réseau LSTM.")
st.write("")

c1, c2, c3, c4 = st.columns(4)
with c1:
    charte.carte("Prévision semaine suivante", charte.nombre(futur["prevision"][0]),
                 f"intervalle 10–90 % : {charte.nombre(futur['bas'][0])} à {charte.nombre(futur['haut'][0])}", "accent")
with c2:
    charte.carte("Erreur moyenne du LSTM", f"{charte.nombre(lstm['MAE'])} clôtures", f"MAE sur {dec['test']} semaines de test")
with c3:
    charte.carte("Gain sur la prévision naïve", charte.pourcent(lstm["MAE"] / naive["MAE"] - 1, 0),
                 f"MAE naïve : {charte.nombre(naive['MAE'])}", "vert")
with c4:
    ecart = lstm["MAE"] / comparaison.loc[meilleur, "MAE"] - 1
    charte.carte("Écart à la meilleure référence", ("+" if ecart > 0 else "") + charte.pourcent(ecart, 0),
                 f"{meilleur.lower()} : {charte.nombre(comparaison.loc[meilleur, 'MAE'])}")

st.write("")
gauche, droite = st.columns([3, 1])
with droite:
    serie = st.radio("Série affichée", ["Corrigée", "Brute"], help="La série corrigée retire les 5 opérations de masse.")
    recul = st.select_slider("Historique affiché", ["52 semaines", "104 semaines", "Tout"], "104 semaines")
    montrer_ref = st.checkbox("Afficher la médiane mobile", value=True)
    montrer_naive = st.checkbox("Afficher la prévision naïve", value=False)
valeurs = h["corrigee"] if serie == "Corrigée" else h["brute"]
n = {"52 semaines": 52, "104 semaines": 104, "Tout": len(valeurs)}[recul]

with gauche:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=futur["semaines"] + futur["semaines"][::-1], y=futur["haut"] + futur["bas"][::-1],
                             mode="lines", fill="toself", fillcolor="rgba(214,40,57,.12)", line=dict(width=0),
                             name="Intervalle empirique 10–90 %", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=h["semaines"][-n:], y=valeurs[-n:], mode="lines", name="Observé",
                             line=dict(color=charte.ENCRE, width=1.8)))
    fig.add_trace(go.Scatter(x=test["semaines"], y=test["previsions"]["LSTM"], mode="lines", name="LSTM — test (à un pas)",
                             line=dict(color=charte.CHURN, width=1.6, dash="dot")))
    if montrer_ref:
        fig.add_trace(go.Scatter(x=test["semaines"], y=test["previsions"]["Médiane mobile 8 semaines"], mode="lines",
                                 name="Médiane mobile 8 semaines", line=dict(color=charte.RETENTION, width=1.4, dash="dash")))
    if montrer_naive:
        fig.add_trace(go.Scatter(x=test["semaines"], y=test["previsions"]["Naïve (dernière valeur)"], mode="lines",
                                 name="Naïve", line=dict(color=charte.GRIS, width=1, dash="dash")))
    fig.add_trace(go.Scatter(x=futur["semaines"], y=futur["prevision"], mode="lines+markers", name="LSTM — 8 prochaines semaines",
                             line=dict(color=charte.CHURN, width=2.6)))
    fig.add_vline(x=h["semaines"][-1], line_dash="dash", line_color=charte.GRIS)
    if serie == "Corrigée":
        fig.update_yaxes(rangemode="tozero")
    fig.update_layout(title="Comptes clos par semaine : observé, test et prévision")
    st.plotly_chart(charte.mise_en_forme(fig, 430), use_container_width=True)

st.caption(p["note_dates"])

# ------------------------------------------------------------------ prévision détaillée
st.markdown("### Les 8 prochaines semaines")
table = pd.DataFrame({
    "Semaine du": pd.to_datetime(futur["semaines"]).strftime("%d/%m/%Y"),
    "Prévision LSTM": [charte.nombre(v) for v in futur["prevision"]],
    "Borne basse (10 %)": [charte.nombre(v) for v in futur["bas"]],
    "Borne haute (90 %)": [charte.nombre(v) for v in futur["haut"]],
})
st.dataframe(table, use_container_width=True, hide_index=True)
charte.note(
    "<b>Comment lire cette prévision.</b> Elle est <i>récursive</i> : chaque semaine prévue sert d'entrée à la suivante, "
    "si bien que la courbe revient peu à peu vers le niveau moyen appris. Elle est fiable surtout pour la ou les deux "
    "premières semaines et doit être recalculée chaque semaine. La borne haute, large, rappelle qu'un pic reste possible : "
    "les opérations de masse ne sont pas prévisibles à partir du passé de la série.")

# ------------------------------------------------------------------ le LSTM prouve-t-il son intérêt ?
st.markdown("### Le LSTM prouve-t-il son intérêt ?")
gauche, droite = st.columns([1.15, 1])
with gauche:
    tri = comparaison.sort_values("MAE", ascending=False)
    fig = go.Figure(go.Bar(
        x=tri["MAE"], y=tri.index, orientation="h",
        marker_color=[charte.CHURN if t == "Deep Learning" else charte.CIEL for t in tri["Type"]],
        text=[charte.nombre(v) for v in tri["MAE"]], textposition="outside"))
    fig.update_layout(title="Erreur absolue moyenne sur le test (plus bas = mieux)", xaxis_title="MAE (clôtures par semaine)")
    fig.update_xaxes(range=[0, tri["MAE"].max() * 1.15])
    st.plotly_chart(charte.mise_en_forme(fig, 330), use_container_width=True)
with droite:
    affichage = comparaison.sort_values("MAE")[["MAE", "RMSE"]].copy()
    affichage["MAE vs naïve"] = [charte.pourcent(v / naive["MAE"] - 1, 0) for v in affichage["MAE"]]
    affichage["MAE"] = affichage["MAE"].map(lambda v: charte.nombre(v, 1))
    affichage["RMSE"] = affichage["RMSE"].map(lambda v: charte.nombre(v, 1))
    st.dataframe(affichage, use_container_width=True)
    st.caption(f"Test : {dec['test']} semaines, prévision à un pas. Fenêtre de {dec['fenetre']} semaines. "
               "Le MAPE n'est pas utilisé : il n'est pas défini sur les semaines à zéro.")

st.markdown(
    f"**Oui face à la prévision naïve** (MAE réduite de {charte.pourcent(1 - lstm['MAE'] / naive['MAE'], 0)}), au RNN simple et à "
    f"ARIMA. **Non face à la meilleure règle simple** : la médiane mobile sur 8 semaines fait légèrement mieux. "
    "Avec environ 200 semaines, trois changements de rythme et des pics imprévisibles, c'est un résultat attendu, "
    "que nous présentons tel quel.")

with st.expander("Bonus — un second KPI : les clients perdus par semaine"):
    second = pd.DataFrame(p["second_kpi"]["comparaison"]).set_index("Modèle").sort_values("MAE")
    naive2 = second.loc["Naïve (dernière valeur)", "MAE"]
    second["MAE vs naïve"] = [charte.pourcent(v / naive2 - 1, 0) for v in second["MAE"]]
    second["MAE"] = second["MAE"].map(lambda v: charte.nombre(v, 1))
    second["RMSE"] = second["RMSE"].map(lambda v: charte.nombre(v, 1))
    st.dataframe(second[["Type", "MAE", "RMSE", "MAE vs naïve"]], use_container_width=True)
    st.caption("Même démarche, appliquée au nombre de clients dont le dernier compte se ferme dans la semaine. "
               "Sur ce KPI, le LSTM obtient la meilleure MAE.")

charte.pied()
