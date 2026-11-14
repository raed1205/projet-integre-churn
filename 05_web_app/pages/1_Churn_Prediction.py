"""Individual prediction: a fictitious profile → an explained churn score."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from utils import preprocessing, theme
from utils.model import ChurnModel, FictitiousGenerator, risk_level


@st.cache_resource
def load_model() -> ChurnModel:
    return ChurnModel()


model = load_model()
meta = model.meta
L = preprocessing.LABELS
CL = preprocessing.CATEGORY_LABELS

# Advice tied to the main risk factor (suggestions, to be validated by the business).
ACTIONS = {
    "MONTHS_TO_NEXT_REVIEW": "Schedule the file review now: it is the first risk signal.",
    "MONTHS_SINCE_REVIEW": "Review the file: the age of the last review weighs on the score.",
    "N_ACCOUNTS": "Look at the customer's product holding: on average, customers with two or three accounts leave less.",
    "CUSTOMER_TENURE": "Customer in the fragile zone of the relationship: plan a follow-up meeting.",
    "AGE": "Most mobile age group: check that the offer still fits.",
    "FILE_COMPLETE": "Complete the customer file.",
    "KYC_SCORE": "Check the follow-up level attached to the KYC score.",
}

theme.header("Churn prediction", "Enter a fictitious profile: the model estimates its probability of leaving and explains it.")
st.write("")

tab_profile, tab_portfolio = st.tabs(["One profile", "A fictitious portfolio"])

with tab_profile:
    default = preprocessing.default_profile()
    with st.form("profile"):
        st.markdown("##### Profile")
        a, b, c = st.columns(3)
        age = a.slider(L["AGE"], 18, 90, int(default["AGE"]))
        marital = b.selectbox(L["MARITAL_STATUS"], preprocessing.CATEGORICAL["MARITAL_STATUS"], index=1,
                              format_func=lambda v: CL["MARITAL_STATUS"][v])
        zone = c.selectbox(L["RESIDENCE_ZONE"], preprocessing.CATEGORICAL["RESIDENCE_ZONE"],
                           format_func=lambda v: CL["RESIDENCE_ZONE"][v])

        st.markdown("##### Commercial relationship")
        a, b, c = st.columns(3)
        tenure = a.slider(L["CUSTOMER_TENURE"], 0.0, 25.0, float(default["CUSTOMER_TENURE"]), 0.5)
        n_accounts = b.number_input(L["N_ACCOUNTS"], 1, 20, int(default["N_ACCOUNTS"]))
        ctype = c.selectbox(L["CUSTOMER_TYPE"], preprocessing.CATEGORICAL["CUSTOMER_TYPE"],
                            format_func=lambda v: CL["CUSTOMER_TYPE"][v])
        a, b, c = st.columns(3)
        segment = a.selectbox(L["SEGMENT"], preprocessing.CATEGORICAL["SEGMENT"])
        income_known = b.checkbox("The customer declared an income", value=False)
        salary = c.select_slider(L["SALARY"], [400, 500, 600, 700, 800, 900, 1000, 2000, 3000, 4000, 5000], 1000,
                                 help="Only used when the box \"The customer declared an income\" is ticked.")

        st.markdown("##### File compliance")
        a, b, c = st.columns(3)
        kyc = a.selectbox(L["KYC_SCORE"], preprocessing.CATEGORICAL["KYC_SCORE"][:-1], format_func=lambda v: CL["KYC_SCORE"][v])
        complete = b.radio(L["FILE_COMPLETE"], ["Yes", "No"], horizontal=True)
        since_review = c.slider(L["MONTHS_SINCE_REVIEW"], 0, 150, int(default["MONTHS_SINCE_REVIEW"]))
        st.caption("The next review date is derived automatically: the review cycle lasts 48 months for a KYC score "
                   "\"LR\", 36 months for \"MR\" and 24 months for \"H1\" to \"H3\".")
        st.form_submit_button("Compute the score", type="primary")

    to_review = preprocessing.months_to_next_review(kyc, since_review)
    profile = {
        "AGE": age, "CUSTOMER_TENURE": tenure, "N_ACCOUNTS": n_accounts,
        "SALARY": float(salary) if income_known else np.nan, "FILE_COMPLETE": 1 if complete == "Yes" else 0,
        "MONTHS_SINCE_REVIEW": since_review, "MONTHS_TO_NEXT_REVIEW": to_review,
        "MARITAL_STATUS": marital, "CUSTOMER_TYPE": ctype, "SEGMENT": segment, "KYC_SCORE": kyc,
        "RESIDENCE_ZONE": zone,
    }
    p = model.predict(profile)

    st.markdown("### Result")
    cycle = preprocessing.REVIEW_CYCLE_MONTHS[kyc]
    review_state = (f"next review in **{to_review:.0f} months**" if to_review >= 0
                    else f"review **overdue by {-to_review:.0f} months**")
    st.caption(f"Profile entered: review cycle of {cycle} months (KYC score {kyc}) → {review_state}.")
    gauge, reading = st.columns([1, 1.25])
    with gauge:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=100 * p.score, number={"suffix": "%", "font": {"size": 46, "color": theme.INK}},
            gauge={"axis": {"range": [0, 100], "ticksuffix": "%"}, "bar": {"color": p.colour, "thickness": .32},
                   "steps": [{"range": [0, 25], "color": "#E3F3F1"}, {"range": [25, 50], "color": "#FCEBDD"},
                             {"range": [50, 100], "color": "#F9DFE2"}],
                   "threshold": {"line": {"color": theme.INK, "width": 3}, "value": 100 * model.alert_threshold}}))
        st.plotly_chart(theme.styled(fig, 260), use_container_width=True)
        st.caption(f"Black line: the model's alert threshold ({theme.percent(model.alert_threshold, 0)}).")
    with reading:
        st.markdown(f'Risk level: <span class="vigie-pill" style="background:{p.colour}">{p.level}</span>',
                    unsafe_allow_html=True)
        st.write("")
        st.markdown(f"**Estimated probability of leaving: {theme.percent(p.score)}** "
                    f"(customer base average: {theme.percent(meta['base_rate'])}).")
        if p.observed_rate is not None:
            st.markdown(f"Among the test-set customers with a comparable score, "
                        f"**{theme.percent(p.observed_rate, 0)} actually left**.")
        st.markdown("Above the alert threshold: " + ("**yes** — profile to include in a retention action."
                                                     if p.above_threshold else "**no**."))
        main = p.drivers(12)
        main = main[main["effect"] > 0]
        if p.above_threshold and len(main) and main.iloc[0]["feature"] in ACTIONS:
            theme.note("<b>Suggested action:</b> " + ACTIONS[main.iloc[0]["feature"]])

    st.markdown("### Why this score?")
    d = p.drivers(8).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=d["effect"], y=d["label"], orientation="h",
        marker_color=[theme.CHURN if e > 0 else theme.RETENTION for e in d["effect"]],
        hovertemplate="%{y}: %{x:+.2f}<extra></extra>"))
    fig.add_vline(x=0, line_color=theme.INK, line_width=1)
    fig.update_layout(title="Red: the factor raises the risk · Green: it lowers it", xaxis_title="Effect on the score (SHAP value)")
    st.plotly_chart(theme.styled(fig, 360), use_container_width=True)
    st.caption("Each bar is the exact contribution of the feature to this score (SHAP values, in log-odds). "
               "The score helps prioritise; it is not an automatic decision.")

with tab_portfolio:
    st.markdown("Generate a portfolio of **fictitious profiles** and spot those to contact first. "
                "Each characteristic is drawn at random, independently of the others, from aggregated distributions: "
                "no profile matches a real customer.")
    a, b = st.columns([1, 3])
    size = a.select_slider("Portfolio size", [50, 100, 200, 500], 200)
    seed = a.number_input("Draw no.", 1, 999, 1, help="Change the number to draw another portfolio.")
    profiles = FictitiousGenerator(meta["marginals"], seed=int(seed)).generate(int(size))
    scores = model.scores(profiles)
    table = profiles.assign(Score=scores, Level=[risk_level(s)[0] for s in scores]).sort_values("Score", ascending=False)

    with b:
        fig = go.Figure(go.Histogram(x=scores, xbins=dict(start=0, end=1, size=0.05), marker_color=theme.INK))
        fig.add_vline(x=model.alert_threshold, line_dash="dash", line_color=theme.CHURN,
                      annotation_text="alert threshold", annotation_position="top right")
        fig.update_xaxes(tickformat=".0%", range=[0, 1])
        fig.update_layout(title="Distribution of the scores of the fictitious portfolio", bargap=.05)
        st.plotly_chart(theme.styled(fig, 280), use_container_width=True)

    n_alert = int((scores >= model.alert_threshold).sum())
    c1, c2, c3 = st.columns(3)
    with c1:
        theme.card("Profiles above the threshold", f"{n_alert} / {len(scores)}", theme.percent(n_alert / len(scores), 0), "accent")
    with c2:
        theme.card("Average score", theme.percent(float(scores.mean())), "fictitious portfolio")
    with c3:
        theme.card("High risk (≥ 50%)", str(int((scores >= .5).sum())), "profiles to handle first", "accent")

    st.markdown("##### The 15 riskiest fictitious profiles")
    shown = table.head(15)[["Score", "Level", "AGE", "CUSTOMER_TENURE", "N_ACCOUNTS", "FILE_COMPLETE",
                            "MONTHS_TO_NEXT_REVIEW", "SEGMENT", "KYC_SCORE"]].copy()
    shown["Score"] = shown["Score"].map(theme.percent)
    shown["AGE"] = shown["AGE"].map(lambda v: "n/a" if v != v else f"{v:.0f}")
    shown["N_ACCOUNTS"] = shown["N_ACCOUNTS"].astype(int)
    shown["FILE_COMPLETE"] = shown["FILE_COMPLETE"].map({1.0: "Yes", 0.0: "No"})
    shown["CUSTOMER_TENURE"] = shown["CUSTOMER_TENURE"].round(1)
    shown["MONTHS_TO_NEXT_REVIEW"] = shown["MONTHS_TO_NEXT_REVIEW"].round(0)
    shown = shown.rename(columns={c: L[c] for c in shown.columns if c in L})
    st.dataframe(shown, use_container_width=True, height=38 + 35 * len(shown))

theme.footer()
