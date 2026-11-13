"""Méthode, fiche du modèle, protection des données et équipe."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import charte, preprocessing
from utils.artefacts import DepotArtefacts



@st.cache_data
def charger() -> tuple[dict, dict]:
    depot = DepotArtefacts()
    return depot.meta_modele(), depot.kpi_synthese()


meta, kpi = charger()
m = meta["metriques_test"]

charte.entete("Méthode et équipe", "Comment les chiffres sont produits, et par qui.")
st.write("")

st.markdown("### La chaîne décisionnelle")
etapes = [
    ("1 · Données", "CSV et 5 fichiers Excel anonymisés. Analyse univariée, valeurs manquantes, outliers."),
    ("2 · ETL", "Talend : extraction, nettoyage, jointures. Pipeline Python équivalent."),
    ("3 · Entrepôt", "PostgreSQL, modèle en étoile : 1 table de faits au grain compte, 8 dimensions, 19 contrôles."),
    ("4 · Reporting", "Power BI et mesures DAX : vue d'ensemble, analyse du churn, segmentation."),
    ("5 · Prédiction", "LSTM pour les clôtures hebdomadaires, XGBoost pour le score de churn."),
    ("6 · Application", "Cette interface : KPI, prédiction expliquée, prévision."),
]
colonnes = st.columns(3)
for i, (titre, texte) in enumerate(etapes):
    with colonnes[i % 3]:
        charte.carte(titre, "", texte)
        st.write("")

st.markdown("### Fiche du modèle de churn")
gauche, droite = st.columns([1, 1.1])
with gauche:
    fiche = pd.DataFrame({
        "": ["Modèle", "Grain", "Cible", "Variables", "Découpage", "Clients (test)", "ROC-AUC", "PR-AUC",
             "Recall au seuil d'alerte", "Precision au seuil d'alerte", "Seuil d'alerte"],
        "Valeur": [
            "XGBoost", "Client", "Tous les comptes du client sont clos", f"{len(preprocessing.LIBELLES)} variables du profil",
            "Par client, 70 / 15 / 15", charte.nombre(meta["entrainement"]["clients_test"]),
            charte.nombre(m["ROC-AUC"], 3), charte.nombre(m["PR-AUC"], 3), charte.pourcent(m["Recall"]),
            charte.pourcent(m["Precision"]), charte.pourcent(meta["seuil_alerte"], 0)],
    })
    st.dataframe(fiche, use_container_width=True, hide_index=True, height=38 + 35 * len(fiche))
with droite:
    imp = pd.Series(meta["importance"]).sort_values()
    fig = go.Figure(go.Bar(x=imp.values, y=imp.index, orientation="h", marker_color=charte.ENCRE,
                           text=[charte.pourcent(v, 0) for v in imp.values], textposition="outside"))
    fig.update_xaxes(tickformat=".0%", range=[0, imp.max() * 1.2])
    fig.update_layout(title="Importance des variables (part SHAP)")
    st.plotly_chart(charte.mise_en_forme(fig, 400), use_container_width=True)

st.markdown("##### Le score tient-il ses promesses ?")
niveaux = pd.DataFrame(meta["niveaux_de_risque"])
c = st.columns(3)
for col, (_, ligne), style in zip(c, niveaux.iterrows(), ["vert", "", "accent"]):
    with col:
        charte.carte(f"Niveau {ligne['niveau']}", charte.pourcent(ligne["taux_observe"]),
                     f"de départs observés sur {charte.nombre(ligne['clients_test'])} clients de test", style)
st.write("")
gains = pd.DataFrame(meta["gains"])
st.markdown(
    f"En contactant les **{charte.pourcent(gains.iloc[2]['Clients ciblés'], 0)}** de clients les mieux scorés, on touche "
    f"**{charte.pourcent(gains.iloc[2]['Départs captés'], 0)}** des départs ; avec "
    f"{charte.pourcent(gains.iloc[3]['Clients ciblés'], 0)}, {charte.pourcent(gains.iloc[3]['Départs captés'], 0)}.")

with st.expander("Contrôle de la fuite de cible"):
    st.markdown(
        "Le fichier est une photographie prise **après** les clôtures. Certaines colonnes ne prédisent pas le départ : "
        "elles le constatent. Le solde, la famille de compte, la devise, la date d'ouverture, le produit et le montant sont "
        "vides pour deux comptes clos sur trois et jamais pour un compte actif.\n\n"
        "Ces colonnes sont **exclues** du modèle. En les ajoutant, la ROC-AUC passerait de 0,75 à 0,95 : "
        "un score proche de 100 % signale une fuite, pas un bon modèle.")
with st.expander("Limites à garder en tête"):
    st.markdown(
        "- **Performance modérée** (ROC-AUC 0,75) : le profil explique une partie du churn, pas tout. "
        "Il manque les données de comportement.\n"
        "- **Photographie unique** : les variables de conformité peuvent refléter en partie le départ lui-même.\n"
        "- **Opérations de masse** : la moitié des clôtures vient de cinq opérations par lots.\n"
        "- **Usage** : le score sert à prioriser une action de rétention, pas à décider seul.")

st.markdown("### Protection des données")
a, b, c = st.columns(3)
with a:
    charte.carte("Dans l'application", "Agrégats", "Aucune ligne client, aucun identifiant, aucun export.")
with b:
    charte.carte("Dans le dépôt", "0 donnée", "Ni CSV, ni Excel, ni modèle sérialisé, ni fichier Power BI.")
with c:
    charte.carte("Seuil de confidentialité", f"{kpi['source']['seuil_petit_effectif']} individus",
                 "Aucun agrégat publié en dessous de cet effectif.")
st.write("")
st.caption(f"Empreinte du fichier source utilisé pour tous les calculs (SHA-256) : `{kpi['source']['sha256']}`. "
           "Le modèle est publié sous forme d'arbres en JSON : des règles de décision, aucune observation.")

st.markdown("### L'équipe")
colonnes = st.columns(4)
for col, (nom, role) in zip(colonnes, charte.EQUIPE):
    with col:
        charte.carte(charte.GROUPE, nom, role)
st.write("")
st.markdown(f"**Tuteurs du projet :** {' et '.join(charte.TUTEURS)}  \n{charte.ECOLE}")

charte.pied()
