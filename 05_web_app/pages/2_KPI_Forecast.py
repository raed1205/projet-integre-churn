"""KPI forecast: weekly closures, LSTM forecast and comparison with the references."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import theme
from utils.artifacts import ArtifactStore


@st.cache_data
def load() -> dict:
    return ArtifactStore().kpi_forecast()


f = load()
h, test, future, split = f["history"], f["test"], f["future"], f["split"]
comparison = pd.DataFrame(f["comparison"]).set_index("Model")
naive = comparison.loc["Naive (last value)"]
lstm = comparison.loc["LSTM"]
best = comparison["MAE"].idxmin()

theme.header("KPI forecast", "Number of accounts closed per week — forecast by an LSTM network.")
st.write("")

c1, c2, c3, c4 = st.columns(4)
with c1:
    theme.card("Next week's forecast", theme.number(future["forecast"][0]),
               f"10–90% interval: {theme.number(future['low'][0])} to {theme.number(future['high'][0])}", "accent")
with c2:
    theme.card("LSTM mean error", f"{theme.number(lstm['MAE'])} closures", f"MAE over {split['test']} test weeks")
with c3:
    theme.card("Gain over the naive forecast", theme.percent(lstm["MAE"] / naive["MAE"] - 1, 0),
               f"naive MAE: {theme.number(naive['MAE'])}", "green")
with c4:
    gap = lstm["MAE"] / comparison.loc[best, "MAE"] - 1
    theme.card("Gap to the best reference", ("+" if gap > 0 else "") + theme.percent(gap, 0),
               f"{best.lower()}: {theme.number(comparison.loc[best, 'MAE'])}")

st.write("")
left, right = st.columns([3, 1])
with right:
    which = st.radio("Series shown", ["Corrected", "Raw"], help="The corrected series removes the 5 mass operations.")
    span = st.select_slider("History shown", ["52 weeks", "104 weeks", "All"], "104 weeks")
    show_ref = st.checkbox("Show the moving median", value=True)
    show_naive = st.checkbox("Show the naive forecast", value=False)
values = h["corrected"] if which == "Corrected" else h["raw"]
k = {"52 weeks": 52, "104 weeks": 104, "All": len(values)}[span]

with left:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=future["weeks"] + future["weeks"][::-1], y=future["high"] + future["low"][::-1],
                             mode="lines", fill="toself", fillcolor="rgba(214,40,57,.12)", line=dict(width=0),
                             name="Empirical 10–90% interval", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=h["weeks"][-k:], y=values[-k:], mode="lines", name="Observed",
                             line=dict(color=theme.INK, width=1.8)))
    fig.add_trace(go.Scatter(x=test["weeks"], y=test["forecasts"]["LSTM"], mode="lines", name="LSTM — test (one step ahead)",
                             line=dict(color=theme.CHURN, width=1.6, dash="dot")))
    if show_ref:
        fig.add_trace(go.Scatter(x=test["weeks"], y=test["forecasts"]["8-week moving median"], mode="lines",
                                 name="8-week moving median", line=dict(color=theme.RETENTION, width=1.4, dash="dash")))
    if show_naive:
        fig.add_trace(go.Scatter(x=test["weeks"], y=test["forecasts"]["Naive (last value)"], mode="lines",
                                 name="Naive", line=dict(color=theme.GREY, width=1, dash="dash")))
    fig.add_trace(go.Scatter(x=future["weeks"], y=future["forecast"], mode="lines+markers", name="LSTM — next 8 weeks",
                             line=dict(color=theme.CHURN, width=2.6)))
    fig.add_vline(x=h["weeks"][-1], line_dash="dash", line_color=theme.GREY)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(title="Accounts closed per week: observed, test and forecast")
    st.plotly_chart(theme.styled(fig, 430), use_container_width=True)

st.caption(f["date_note"])

st.markdown("### The next 8 weeks")
table = pd.DataFrame({
    "Week starting": pd.to_datetime(future["weeks"]).strftime("%d/%m/%Y"),
    "LSTM forecast": [theme.number(v) for v in future["forecast"]],
    "Lower bound (10%)": [theme.number(v) for v in future["low"]],
    "Upper bound (90%)": [theme.number(v) for v in future["high"]],
})
st.dataframe(table, use_container_width=True, hide_index=True)
theme.note(
    "<b>How to read this forecast.</b> It is <i>recursive</i>: each forecast week is used as an input for the next one, "
    "so the curve gradually drifts back to the average level learnt. It is mostly reliable for the first one or two weeks "
    "and must be recomputed every week. The wide upper bound is a reminder that a spike is always possible: mass "
    "operations cannot be predicted from the past of the series.")

st.markdown("### Does the LSTM prove its worth?")
left, right = st.columns([1.15, 1])
with left:
    ranked = comparison.sort_values("MAE", ascending=False)
    fig = go.Figure(go.Bar(
        x=ranked["MAE"], y=ranked.index, orientation="h",
        marker_color=[theme.CHURN if t == "Deep Learning" else theme.SKY for t in ranked["Type"]],
        text=[theme.number(v) for v in ranked["MAE"]], textposition="outside"))
    fig.update_layout(title="Mean absolute error on the test set (lower is better)", xaxis_title="MAE (closures per week)")
    fig.update_xaxes(range=[0, ranked["MAE"].max() * 1.15])
    st.plotly_chart(theme.styled(fig, 330), use_container_width=True)
with right:
    shown = comparison.sort_values("MAE")[["MAE", "RMSE"]].copy()
    shown["MAE vs naive"] = [theme.percent(v / naive["MAE"] - 1, 0) for v in shown["MAE"]]
    shown["MAE"] = shown["MAE"].map(lambda v: theme.number(v, 1))
    shown["RMSE"] = shown["RMSE"].map(lambda v: theme.number(v, 1))
    st.dataframe(shown, use_container_width=True)
    st.caption(f"Test: {split['test']} weeks, one-step-ahead forecast. {split['window']}-week window. "
               "MAPE is not used: it is undefined on zero weeks.")

st.markdown(
    f"**Yes against the naive forecast** (MAE cut by {theme.percent(1 - lstm['MAE'] / naive['MAE'], 0)}), the simple RNN "
    "and ARIMA. **No against the best simple rule**: the 8-week moving median does slightly better. With about 200 weeks, "
    "three changes of rhythm and unpredictable spikes, this is an expected result, which we present as it is.")

with st.expander("Bonus — a second KPI: customers lost per week"):
    second = pd.DataFrame(f["second_kpi"]["comparison"]).set_index("Model").sort_values("MAE")
    naive2 = second.loc["Naive (last value)", "MAE"]
    second["MAE vs naive"] = [theme.percent(v / naive2 - 1, 0) for v in second["MAE"]]
    second["MAE"] = second["MAE"].map(lambda v: theme.number(v, 1))
    second["RMSE"] = second["RMSE"].map(lambda v: theme.number(v, 1))
    st.dataframe(second[["Type", "MAE", "RMSE", "MAE vs naive"]], use_container_width=True)
    st.caption("Same approach, applied to the number of customers whose last account closes during the week. "
               "On this KPI the LSTM has the best MAE.")

theme.footer()
