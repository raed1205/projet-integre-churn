"""Prédiction individuelle : un profil fictif → un score de churn expliqué."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from utils import charte, preprocessing
from utils.model import GenerateurFictif, ModeleChurn, niveau_de_risque



@st.cache_resource
def charger_modele() -> ModeleChurn:
    return ModeleChurn()


modele = charger_modele()
meta = modele.meta
L = preprocessing.LIBELLES
M = preprocessing.LIBELLES_MODALITES

# Conseils associés au facteur de risque principal (suggestions, à valider par le métier).
ACTIONS = {
    "MOIS_AVANT_PROCHAINE_REVUE": "Planifier sans attendre la revue du dossier : c'est le premier signal de risque.",
    "MOIS_DEPUIS_REVUE": "Revoir le dossier : l'ancienneté de la dernière revue pèse sur le score.",
    "NB_COMPTES": "Regarder l'équipement du client : en moyenne, les clients à deux ou trois comptes partent moins.",
    "ANCIENNETE_CLIENT": "Client dans la zone de fragilité de la relation : prévoir un point de suivi.",
    "AGE": "Tranche d'âge la plus mobile : vérifier l'adéquation de l'offre.",
    "DOSSIER_COMPLET": "Compléter le dossier client.",
    "SCORE_KYC": "Vérifier le niveau de suivi associé au score KYC.",
}

charte.entete("Prédiction du churn", "Saisissez un profil fictif : le modèle estime sa probabilité de départ et l'explique.")
st.write("")

onglet_profil, onglet_portefeuille = st.tabs(["Un profil", "Un portefeuille fictif"])

# ====================================================================== un profil
with onglet_profil:
    defaut = preprocessing.profil_par_defaut()
    with st.form("profil"):
        st.markdown("##### Profil")
        a, b, c = st.columns(3)
        age = a.slider(L["AGE"], 18, 90, int(defaut["AGE"]))
        statut = b.selectbox(L["STATUT_MARITAL"], preprocessing.CATEGORIELLES["STATUT_MARITAL"], index=1,
                             format_func=lambda v: M["STATUT_MARITAL"][v])
        zone = c.selectbox(L["ZONE_RESIDENCE"], preprocessing.CATEGORIELLES["ZONE_RESIDENCE"],
                           format_func=lambda v: M["ZONE_RESIDENCE"][v])

        st.markdown("##### Relation commerciale")
        a, b, c = st.columns(3)
        anciennete = a.slider(L["ANCIENNETE_CLIENT"], 0.0, 25.0, float(defaut["ANCIENNETE_CLIENT"]), 0.5)
        nb_comptes = b.number_input(L["NB_COMPTES"], 1, 20, int(defaut["NB_COMPTES"]))
        nature = c.selectbox(L["NATURE_CLIENT"], preprocessing.CATEGORIELLES["NATURE_CLIENT"],
                             format_func=lambda v: M["NATURE_CLIENT"][v])
        a, b, c = st.columns(3)
        segment = a.selectbox(L["SEGMENT"], preprocessing.CATEGORIELLES["SEGMENT"])
        revenu_connu = b.checkbox("Le client a déclaré un revenu", value=False)
        salaire = c.select_slider(L["SALAIRE"], [400, 500, 600, 700, 800, 900, 1000, 2000, 3000, 4000, 5000], 1000,
                                  disabled=False, help="Pris en compte seulement si la case « Le client a déclaré un revenu » est cochée.")

        st.markdown("##### Conformité du dossier")
        a, b, c = st.columns(3)
        kyc = a.selectbox(L["SCORE_KYC"], preprocessing.CATEGORIELLES["SCORE_KYC"][:-1], format_func=lambda v: M["SCORE_KYC"][v])
        dossier = b.radio(L["DOSSIER_COMPLET"], ["Oui", "Non"], horizontal=True)
        depuis_revue = c.slider(L["MOIS_DEPUIS_REVUE"], 0, 150, int(defaut["MOIS_DEPUIS_REVUE"]))
        st.caption("La date de la prochaine revue est déduite automatiquement : le cycle de revue dure 48 mois pour un "
                   "score KYC « LR », 36 mois pour « MR » et 24 mois pour « H1 » à « H3 ».")
        st.form_submit_button("Calculer le score", type="primary")

    avant_revue = preprocessing.mois_avant_prochaine_revue(kyc, depuis_revue)

    profil = {
        "AGE": age, "ANCIENNETE_CLIENT": anciennete, "NB_COMPTES": nb_comptes,
        "SALAIRE": float(salaire) if revenu_connu else np.nan, "DOSSIER_COMPLET": 1 if dossier == "Oui" else 0,
        "MOIS_DEPUIS_REVUE": depuis_revue, "MOIS_AVANT_PROCHAINE_REVUE": avant_revue,
        "STATUT_MARITAL": statut, "NATURE_CLIENT": nature, "SEGMENT": segment, "SCORE_KYC": kyc,
        "ZONE_RESIDENCE": zone,
    }
    p = modele.predire(profil)

    st.markdown("### Résultat")
    cycle = preprocessing.CYCLE_REVUE_MOIS[kyc]
    etat_revue = (f"prochaine revue dans **{avant_revue:.0f} mois**" if avant_revue >= 0
                  else f"revue **en retard de {-avant_revue:.0f} mois**")
    st.caption(f"Profil saisi : cycle de revue de {cycle} mois (score KYC {kyc}) → {etat_revue}.")
    jauge, lecture = st.columns([1, 1.25])
    with jauge:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=100 * p.score, number={"suffix": " %", "font": {"size": 46, "color": charte.ENCRE}},
            gauge={"axis": {"range": [0, 100], "ticksuffix": " %"}, "bar": {"color": p.couleur, "thickness": .32},
                   "steps": [{"range": [0, 25], "color": "#E3F3F1"}, {"range": [25, 50], "color": "#FCEBDD"},
                             {"range": [50, 100], "color": "#F9DFE2"}],
                   "threshold": {"line": {"color": charte.ENCRE, "width": 3}, "value": 100 * modele.seuil_alerte}}))
        st.plotly_chart(charte.mise_en_forme(fig, 260), use_container_width=True)
        st.caption(f"Trait noir : seuil d'alerte du modèle ({charte.pourcent(modele.seuil_alerte, 0)}).")
    with lecture:
        st.markdown(f'Niveau de risque : <span class="vigie-pastille" style="background:{p.couleur}">{p.niveau}</span>',
                    unsafe_allow_html=True)
        st.write("")
        st.markdown(f"**Probabilité de départ estimée : {charte.pourcent(p.score)}** "
                    f"(moyenne de la clientèle : {charte.pourcent(meta['taux_de_base'])}).")
        if p.taux_observe is not None:
            st.markdown(f"Parmi les clients du jeu de test ayant un score comparable, "
                        f"**{charte.pourcent(p.taux_observe, 0)} sont effectivement partis**.")
        st.markdown("Au-dessus du seuil d'alerte : " + ("**oui** — profil à inclure dans une action de rétention."
                                                        if p.au_dessus_du_seuil else "**non**."))
        principal = p.facteurs(12)
        principal = principal[principal["effet"] > 0]
        if p.au_dessus_du_seuil and len(principal) and principal.iloc[0]["variable"] in ACTIONS:
            charte.note("<b>Piste d'action :</b> " + ACTIONS[principal.iloc[0]["variable"]])

    st.markdown("### Pourquoi ce score ?")
    f = p.facteurs(8).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=f["effet"], y=f["libelle"], orientation="h",
        marker_color=[charte.CHURN if e > 0 else charte.RETENTION for e in f["effet"]],
        hovertemplate="%{y} : %{x:+.2f}<extra></extra>"))
    fig.add_vline(x=0, line_color=charte.ENCRE, line_width=1)
    fig.update_layout(title="Rouge : le facteur augmente le risque · Vert : il le réduit", xaxis_title="Effet sur le score (valeur SHAP)")
    st.plotly_chart(charte.mise_en_forme(fig, 360), use_container_width=True)
    st.caption("Chaque barre est la contribution exacte de la variable à ce score (valeurs SHAP, en log-odds). "
               "Le score est une aide à la priorisation, pas une décision automatique.")

# ====================================================================== un portefeuille fictif
with onglet_portefeuille:
    st.markdown("Générez un portefeuille de **profils fictifs** et repérez ceux à contacter en priorité. "
                "Chaque caractéristique est tirée au hasard, indépendamment des autres, à partir de distributions agrégées : "
                "aucun profil ne correspond à un client réel.")
    a, b = st.columns([1, 3])
    taille = a.select_slider("Taille du portefeuille", [50, 100, 200, 500], 200)
    graine = a.number_input("Tirage n°", 1, 999, 1, help="Changer le numéro pour tirer un autre portefeuille.")
    profils = GenerateurFictif(meta["marginales"], graine=int(graine)).generer(int(taille))
    scores = modele.scores(profils)
    table = profils.assign(Score=scores, Niveau=[niveau_de_risque(s)[0] for s in scores]).sort_values("Score", ascending=False)

    with b:
        fig = go.Figure(go.Histogram(x=scores, xbins=dict(start=0, end=1, size=0.05), marker_color=charte.ENCRE))
        fig.add_vline(x=modele.seuil_alerte, line_dash="dash", line_color=charte.CHURN,
                      annotation_text="seuil d'alerte", annotation_position="top right")
        fig.update_xaxes(tickformat=".0%", range=[0, 1])
        fig.update_layout(title="Distribution des scores du portefeuille fictif", bargap=.05)
        st.plotly_chart(charte.mise_en_forme(fig, 280), use_container_width=True)

    n_alerte = int((scores >= modele.seuil_alerte).sum())
    c1, c2, c3 = st.columns(3)
    with c1:
        charte.carte("Profils au-dessus du seuil", f"{n_alerte} / {len(scores)}", charte.pourcent(n_alerte / len(scores), 0), "accent")
    with c2:
        charte.carte("Score moyen", charte.pourcent(float(scores.mean())), "portefeuille fictif")
    with c3:
        charte.carte("Risque élevé (≥ 50 %)", str(int((scores >= .5).sum())), "profils à traiter en premier", "accent")

    st.markdown("##### Les 15 profils fictifs les plus à risque")
    affichage = table.head(15)[["Score", "Niveau", "AGE", "ANCIENNETE_CLIENT", "NB_COMPTES", "DOSSIER_COMPLET",
                                "MOIS_AVANT_PROCHAINE_REVUE", "SEGMENT", "SCORE_KYC"]].copy()
    affichage["Score"] = affichage["Score"].map(charte.pourcent)
    affichage["AGE"] = affichage["AGE"].map(lambda v: "n. r." if v != v else f"{v:.0f}")
    affichage["NB_COMPTES"] = affichage["NB_COMPTES"].astype(int)
    affichage["DOSSIER_COMPLET"] = affichage["DOSSIER_COMPLET"].map({1.0: "Oui", 0.0: "Non"})
    affichage["ANCIENNETE_CLIENT"] = affichage["ANCIENNETE_CLIENT"].round(1)
    affichage["MOIS_AVANT_PROCHAINE_REVUE"] = affichage["MOIS_AVANT_PROCHAINE_REVUE"].round(0)
    affichage = affichage.rename(columns={c: L[c] for c in affichage.columns if c in L})
    st.dataframe(affichage, use_container_width=True, height=38 + 35 * len(affichage))

charte.pied()
