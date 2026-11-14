"""Home page: the summary churn KPIs, all aggregated."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from utils import theme
from utils.artifacts import ArtifactStore


@st.cache_data
def load() -> tuple[dict, dict]:
    store = ArtifactStore()
    return store.kpi_summary(), store.kpi_forecast()


kpi, forecast = load()
g = kpi["overall"]

theme.header("VIGIE — churn overview", theme.TAGLINE)
st.write("")

c1, c2, c3, c4 = st.columns(4)
with c1:
    theme.card("Churn rate · accounts", theme.percent(g["account_churn_rate"]),
               f"{theme.number(g['closed_accounts'])} closed out of {theme.number(g['accounts'])}", "accent")
with c2:
    theme.card("Churn rate · customers", theme.percent(g["customer_churn_rate"]),
               f"{theme.number(g['churned_customers'])} left out of {theme.number(g['customers_with_account'])}", "accent")
with c3:
    theme.card("Active accounts", theme.number(g["active_accounts"]),
               f"median balance: {theme.number(g['median_balance_active_accounts'])}", "green")
with c4:
    theme.card("Average tenure", f"{theme.number(g['average_customer_tenure'], 1)} years",
               f"{theme.percent(g['multi_account_share'])} hold several accounts", "green")

st.write("")
c5, c6, c7, c8 = st.columns(4)
with c5:
    theme.card("Customers", theme.number(g["customers"]),
               f"of which {theme.number(g['customers'] - g['customers_with_account'])} with no account")
with c6:
    theme.card("Complete files", theme.percent(g["complete_file_share"]), "customers with at least one account")
with c7:
    theme.card("Overdue reviews", theme.percent(g["overdue_review_share"]), "first risk signal of the model")
with c8:
    theme.card("Overdrawn accounts", theme.percent(g["overdrawn_share_active"]), "among active accounts")

st.write("")
theme.note(
    "<b>A rate is always read at its grain.</b> "
    f"The same file gives {theme.percent(g['row_churn_rate'])} churn per row, "
    f"{theme.percent(g['account_churn_rate'])} per account and {theme.percent(g['customer_churn_rate'])} per customer "
    f"({theme.percent(g['all_customers_churn_rate'])} when customers with no account are included). "
    "Every indicator in this application is computed at account or customer grain, never per row.")

st.markdown("### Who leaves?")
left, right = st.columns([1, 2.4])
with left:
    axis = st.radio("Read the churn rate by", list(kpi["customer_axes"].keys())[:6], index=0)
    st.caption("Customer grain. Categories with fewer than 20 customers are not shown.")
axis_data = kpi["customer_axes"][axis]
mean = g["customer_churn_rate"]
with right:
    fig = go.Figure(go.Bar(
        x=[d["category"] for d in axis_data], y=[d["churn_rate"] for d in axis_data],
        marker_color=[theme.CHURN if d["churn_rate"] > mean else theme.RETENTION for d in axis_data],
        text=[theme.percent(d["churn_rate"], 0) for d in axis_data], textposition="outside",
        customdata=[theme.number(d["count"]) for d in axis_data],
        hovertemplate="%{x}<br>Churn rate: %{y:.1%}<br>Customers: %{customdata}<extra></extra>"))
    fig.add_hline(y=mean, line_dash="dash", line_color=theme.INK,
                  annotation_text=f"average {theme.percent(mean)}", annotation_position="top left")
    fig.update_yaxes(tickformat=".0%", range=[0, max(d["churn_rate"] for d in axis_data) * 1.22])
    fig.update_layout(title=f"Churn rate by {axis.lower()}")
    st.plotly_chart(theme.styled(fig), use_container_width=True)

st.markdown("### Closures over time")
h = forecast["history"]
mass_share = sum(h["raw"][h["weeks"].index(s)] for s in h["mass_weeks"]) / sum(h["raw"])
fig = go.Figure()
fig.add_trace(go.Scatter(x=h["weeks"], y=h["corrected"], mode="lines", name="Closures per week (corrected series)",
                         line=dict(color=theme.INK, width=1.6), fill="tozeroy", fillcolor="rgba(20,33,61,.07)"))
for s in h["mass_weeks"]:
    fig.add_vline(x=s, line_dash="dot", line_color=theme.CHURN, opacity=.6)
fig.add_trace(go.Scatter(x=forecast["future"]["weeks"], y=forecast["future"]["forecast"], mode="lines+markers",
                         name="LSTM forecast (8 weeks)", line=dict(color=theme.CHURN, width=2.4)))
fig.update_layout(title="Accounts closed per week — red dotted lines: mass operations removed from the series")
st.plotly_chart(theme.styled(fig, 340), use_container_width=True)
st.caption(f"{len(h['weeks'])} weeks. {len(h['mass_weeks'])} mass operations carry {theme.percent(mass_share, 0)} "
           "of the closures; they are replaced by an ordinary level. " + forecast["date_note"])

st.markdown("### Go further")
a, b, c = st.columns(3)
with a:
    st.page_link("pages/1_Churn_Prediction.py", label="**Score a profile's risk**", icon="🎯")
    st.caption("Enter a fictitious profile, get its score and the factors behind it.")
with b:
    st.page_link("pages/2_KPI_Forecast.py", label="**Forecast closures**", icon="📈")
    st.caption("The LSTM forecast, compared with simple rules.")
with c:
    st.page_link("pages/3_Segments.py", label="**Explore the segments**", icon="🧭")
    st.caption("Churn rate and value profile by segment.")

theme.footer()
