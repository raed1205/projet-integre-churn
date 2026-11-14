"""Method, model card, data protection and team."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import preprocessing, theme
from utils.artifacts import ArtifactStore


@st.cache_data
def load() -> tuple[dict, dict]:
    store = ArtifactStore()
    return store.model_meta(), store.kpi_summary()


meta, kpi = load()
m = meta["test_metrics"]

theme.header("Method and team", "How the figures are produced, and by whom.")
st.write("")

st.markdown("### The decision-support chain")
stages = [
    ("1 · Data", "CSV and 5 anonymised Excel files. Univariate analysis, missing values, outliers."),
    ("2 · ETL", "Talend: extraction, cleaning, joins. Equivalent Python pipeline."),
    ("3 · Warehouse", "PostgreSQL star schema: 1 fact table at account grain, 8 dimensions, 19 checks."),
    ("4 · Reporting", "Power BI and DAX measures: overview, churn analysis, segmentation."),
    ("5 · Prediction", "LSTM for weekly closures, XGBoost for the churn score."),
    ("6 · Application", "This interface: KPIs, explained prediction, forecast."),
]
cols = st.columns(3)
for i, (title, text) in enumerate(stages):
    with cols[i % 3]:
        theme.card(title, "", text)
        st.write("")

st.markdown("### Churn model card")
left, right = st.columns([1, 1.1])
with left:
    card = pd.DataFrame({
        "": ["Model", "Grain", "Target", "Features", "Split", "Customers (test)", "ROC-AUC", "PR-AUC",
             "Recall at the alert threshold", "Precision at the alert threshold", "Alert threshold"],
        "Value": [
            "XGBoost", "Customer", "All of the customer's accounts are closed", f"{len(preprocessing.LABELS)} profile features",
            "Per customer, 70 / 15 / 15", theme.number(meta["training"]["test_customers"]),
            theme.number(m["ROC-AUC"], 3), theme.number(m["PR-AUC"], 3), theme.percent(m["Recall"]),
            theme.percent(m["Precision"]), theme.percent(meta["alert_threshold"], 0)],
    })
    st.dataframe(card, use_container_width=True, hide_index=True, height=38 + 35 * len(card))
with right:
    imp = pd.Series(meta["importance"]).sort_values()
    fig = go.Figure(go.Bar(x=imp.values, y=imp.index, orientation="h", marker_color=theme.INK,
                           text=[theme.percent(v, 0) for v in imp.values], textposition="outside"))
    fig.update_xaxes(tickformat=".0%", range=[0, imp.max() * 1.2])
    fig.update_layout(title="Feature importance (SHAP share)")
    st.plotly_chart(theme.styled(fig, 400), use_container_width=True)

st.markdown("##### Does the score keep its promises?")
levels = pd.DataFrame(meta["risk_levels"])
cols = st.columns(3)
for col, (_, row), style in zip(cols, levels.iterrows(), ["green", "", "accent"]):
    with col:
        theme.card(f"{row['level']} level", theme.percent(row["observed_rate"]),
                   f"observed departures among {theme.number(row['test_customers'])} test customers", style)
st.write("")
gains = pd.DataFrame(meta["gains"])
st.markdown(
    f"Contacting the top **{theme.percent(gains.iloc[2]['Customers targeted'], 0)}** of scored customers reaches "
    f"**{theme.percent(gains.iloc[2]['Departures captured'], 0)}** of departures; the top "
    f"{theme.percent(gains.iloc[3]['Customers targeted'], 0)}, {theme.percent(gains.iloc[3]['Departures captured'], 0)}.")

with st.expander("Target leakage check"):
    st.markdown(
        "The file is a snapshot taken **after** the closures. Some columns do not predict the departure: they record "
        "it. The balance, account family, currency, opening date, product and amount are blank for two closed accounts "
        "in three and never for an active account.\n\n"
        "These columns are **excluded** from the model. Adding them would push the ROC-AUC from 0.75 to 0.95: "
        "a score close to 100% signals a leak, not a good model.")
with st.expander("Limitations to keep in mind"):
    st.markdown(
        "- **Moderate performance** (ROC-AUC 0.75): the profile explains part of churn, not all of it. "
        "Behavioural data is missing.\n"
        "- **Single snapshot**: compliance features may partly reflect the departure itself.\n"
        "- **Mass operations**: half of the closures come from five batch operations.\n"
        "- **Use**: the score is meant to prioritise a retention action, not to decide on its own.")

st.markdown("### Data protection")
a, b, c = st.columns(3)
with a:
    theme.card("In the application", "Aggregates", "No customer row, no identifier, no export.")
with b:
    theme.card("In the repository", "0 data", "No CSV, no Excel, no serialised model, no Power BI file.")
with c:
    theme.card("Confidentiality threshold", f"{kpi['source']['min_cell_size']} individuals",
               "No aggregate is published below this count.")
st.write("")
st.caption(f"Fingerprint of the source file used for every computation (SHA-256): `{kpi['source']['sha256']}`. "
           "The model is published as trees in JSON: decision rules, no observation.")

st.markdown("### The team")
cols = st.columns(len(theme.TEAM))
for col, (name, role, email) in zip(cols, theme.TEAM):
    with col:
        theme.card(theme.GROUP, name, f"{role}<br><a href='mailto:{email}'>{email}</a>")
st.write("")
st.markdown(f"**Project supervisors:** {' and '.join(theme.SUPERVISORS)}  \n{theme.SCHOOL}")

theme.footer()
