"""VIGIE — web application of the Integrated Project (Group BI 5).

Entry point: configures the application and declares its pages.

    streamlit run 05_web_app/app.py

The application only reads the ``artifacts/`` folder (aggregates and model parameters).
"""

from __future__ import annotations

import streamlit as st

from utils import theme

PAGES = [
    st.Page("pages/0_Overview.py", title="Overview", icon="🏠", default=True),
    st.Page("pages/1_Churn_Prediction.py", title="Churn prediction", icon="🎯"),
    st.Page("pages/2_KPI_Forecast.py", title="KPI forecast", icon="📈"),
    st.Page("pages/3_Segments.py", title="Segments and profiles", icon="🧭"),
    st.Page("pages/4_Method_and_Team.py", title="Method and team", icon="📘"),
]

page = st.navigation(PAGES)
theme.configure()
page.run()
