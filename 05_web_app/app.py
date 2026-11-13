"""VIGIE — application web du Projet Intégré (Groupe BI 5).

Point d'entrée : configure l'application et déclare ses pages.

    streamlit run 05_web_app/app.py

L'application ne lit que le dossier ``artifacts/`` (agrégats et paramètres du modèle).
"""

from __future__ import annotations

import streamlit as st

from utils import charte

PAGES = [
    st.Page("pages/0_Vue_d_ensemble.py", title="Vue d'ensemble", icon="🏠", default=True),
    st.Page("pages/1_Prediction_du_churn.py", title="Prédiction du churn", icon="🎯"),
    st.Page("pages/2_Prevision_du_KPI.py", title="Prévision du KPI", icon="📈"),
    st.Page("pages/3_Segments_et_profils.py", title="Segments et profils", icon="🧭"),
    st.Page("pages/4_Methode_et_equipe.py", title="Méthode et équipe", icon="📘"),
]

page = st.navigation(PAGES)
charte.configurer()
page.run()
