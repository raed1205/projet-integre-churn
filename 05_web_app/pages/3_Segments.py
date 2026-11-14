"""Segmentation: churn rate by axis and value profile by segment (aggregates only)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import theme
from utils.artifacts import ArtifactStore


@st.cache_data
def load() -> dict:
    return ArtifactStore().kpi_summary()


kpi = load()
g = kpi["overall"]

theme.header("Segments and profiles", "Where churn concentrates, and what the customer segments look like.")
st.write("")

tab_customer, tab_account, tab_value = st.tabs(["By customer profile", "By account type", "Segment value"])


def chart(rows: list[dict], title: str, mean: float, unit: str):
    table = pd.DataFrame(rows)
    fig = go.Figure(go.Bar(
        x=table["category"], y=table["churn_rate"], name="Churn rate",
        marker_color=[theme.CHURN if v > mean else theme.RETENTION for v in table["churn_rate"]],
        text=[theme.percent(v, 0) for v in table["churn_rate"]], textposition="outside",
        customdata=[theme.number(v) for v in table["count"]],
        hovertemplate="%{x}<br>Churn rate: %{y:.1%}<br>" + unit + ": %{customdata}<extra></extra>"))
    fig.add_hline(y=mean, line_dash="dash", line_color=theme.INK,
                  annotation_text=f"average {theme.percent(mean)}", annotation_position="top left")
    fig.update_yaxes(tickformat=".0%", range=[0, min(1.12, table["churn_rate"].max() * 1.22)])
    fig.update_layout(title=title)
    return theme.styled(fig, 400), table


with tab_customer:
    axis = st.selectbox("Analysis axis", list(kpi["customer_axes"].keys()))
    fig, table = chart(kpi["customer_axes"][axis], f"Churn rate by {axis.lower()} — customer grain",
                       g["customer_churn_rate"], "Customers")
    st.plotly_chart(fig, use_container_width=True)
    hi, lo = table.loc[table["churn_rate"].idxmax()], table.loc[table["churn_rate"].idxmin()]
    st.markdown(f"The churn rate ranges from **{theme.percent(lo['churn_rate'])}** ({lo['category']}) to "
                f"**{theme.percent(hi['churn_rate'])}** ({hi['category']}).")
    table["Share of customers"] = (table["count"] / table["count"].sum()).map(theme.percent)
    table["count"] = table["count"].map(theme.number)
    table["churn_rate"] = table["churn_rate"].map(theme.percent)
    st.dataframe(table.rename(columns={"category": axis, "count": "Customers", "churn_rate": "Churn rate"}),
                 use_container_width=True, hide_index=True)

with tab_account:
    axis = st.selectbox("Analysis axis", list(kpi["account_axes"].keys()))
    fig, table = chart(kpi["account_axes"][axis], f"Churn rate by {axis.lower()} — account grain",
                       g["account_churn_rate"], "Accounts")
    st.plotly_chart(fig, use_container_width=True)
    theme.note(
        "<b>Watch the \"Not provided\" category.</b> For about two closed accounts in three, the family, currency and "
        "product are no longer filled in: these accounts form a category with 100% churn. The rate of the other "
        "categories is therefore <b>understated</b>. These axes describe the portfolio; they are not used to predict "
        "churn (that would be target leakage).")
    table["count"] = table["count"].map(theme.number)
    table["churn_rate"] = table["churn_rate"].map(theme.percent)
    st.dataframe(table.rename(columns={"category": axis, "count": "Accounts", "churn_rate": "Churn rate"}),
                 use_container_width=True, hide_index=True)

    st.markdown("##### Declared closure reasons")
    reasons = pd.DataFrame(kpi["closure_reasons"])
    reasons["Share"] = (reasons["accounts"] / reasons["accounts"].sum()).map(theme.percent)
    reasons["accounts"] = reasons["accounts"].map(theme.number)
    st.dataframe(reasons.rename(columns={"reason": "Reason", "accounts": "Closed accounts"}), use_container_width=True, hide_index=True)
    st.caption("The \"Other\" reason dominates: the declared reason does not explain churn, hence the value of a "
               "profile-based model.")

with tab_value:
    seg = pd.DataFrame(kpi["segments"])
    fig = go.Figure(go.Scatter(
        x=seg["accounts_per_customer"], y=seg["churn_rate"], mode="markers+text", text=seg["segment"],
        textposition="top center",
        marker=dict(size=(seg["customers"] ** 0.5) / 6 + 14, color=theme.INK, opacity=.85, line=dict(color="white", width=2)),
        customdata=[theme.number(v) for v in seg["customers"]],
        hovertemplate="%{text}<br>Accounts per customer: %{x:.2f}<br>Churn rate: %{y:.1%}<br>Customers: %{customdata}<extra></extra>"))
    fig.update_yaxes(tickformat=".0%", title="Churn rate", range=[0.28, 0.42])
    fig.update_xaxes(title="Average number of accounts per customer (product holding)")
    fig.update_layout(title="Segments: product holding and churn (bubble size = number of customers)")
    st.plotly_chart(theme.styled(fig, 400), use_container_width=True)

    shown = pd.DataFrame({
        "Segment": seg["segment"],
        "Customers": seg["customers"].map(theme.number),
        "Churn rate": seg["churn_rate"].map(theme.percent),
        "Average tenure": seg["average_tenure"].map(lambda v: f"{theme.number(v, 1)} years"),
        "Accounts per customer": seg["accounts_per_customer"].map(lambda v: theme.number(v, 2)),
        "Multi-account": seg["multi_account_share"].map(theme.percent),
        "Complete files": seg["complete_file_share"].map(theme.percent),
        "Median balance (active customers)": seg["median_balance_active_customers"].map(theme.number),
    })
    st.dataframe(shown, use_container_width=True, hide_index=True)
    st.caption("Median balance: sum of the balances of a customer's active accounts, median per segment. Amounts are "
               "rounded and capped by the anonymisation: they serve to compare segments, not to measure a real balance.")

theme.footer()
