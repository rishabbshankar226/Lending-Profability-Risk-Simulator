"""Public-demo entrypoint. Every financial result comes from the pure engine."""

from dataclasses import asdict
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lending_simulator import MODEL_VERSION
from lending_simulator.analytics import policy_population, query_text
from lending_simulator.data import DEFAULT_SEED, load_dataset
from lending_simulator.decisions import compare_policies, evaluate_policy, select_strategy, sensitivity
from lending_simulator.exports import scenario_workbook
from lending_simulator.presentation import (
    assumption_register, band_curves, cohort_heatmap, comparison_frame,
    csv_package, evidence_register, month_label, monthly_frame,
)
from lending_simulator.types import Assumptions, POLICIES

ROOT = Path(__file__).resolve().parent
COLORS = {"Conservative": "#145b72", "Balanced": "#84734d", "Aggressive": "#8a477b"}
DEFAULTS = {
    "policy": "conservative", "growth_percent": 0.0, "stress": 1.0, "funding_percent": 8.0,
    "initial_cash": 500000.0, "borrower_percent": 18.0, "merchant_percent": 2.0,
    "low_percent": 2.0, "medium_percent": 6.0, "high_percent": 12.0,
    "recovery_percent": 25.0, "lag": 3, "advance_percent": 80.0,
    "facility": 2000000.0, "acquisition": 25.0, "servicing": 1.0,
    "opex": 7500.0, "loss_cap_percent": 5.0, "cash_floor": 50000.0,
    "cohort_cutoff": "First 24 months",
}


def money(value):
    return "n.a." if value is None else f"${value:,.0f}" if value >= 0 else f"(${abs(value):,.0f})"


def percent(value):
    return "n.a." if value is None else f"{value:.2%}"


@st.cache_data(max_entries=2, show_spinner=False)
def get_dataset(csv_hash, manifest_hash, dataset_version):
    dataset = load_dataset(ROOT / "data" / "applications.csv", DEFAULT_SEED)
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())
    if (dataset.version != dataset_version or not isinstance(manifest, dict)
            or any(manifest.get(key) != value for key, value in dataset.manifest().items())):
        raise ValueError("The base dataset does not match its versioned manifest.")
    return dataset


@st.cache_data(max_entries=8, show_spinner=False)
def cached_results(assumption_json, dataset_hash, dataset_version, model_version, _dataset):
    if _dataset.dataset_hash != dataset_hash or _dataset.version != dataset_version or model_version != MODEL_VERSION:
        raise ValueError("Scenario cache identity does not match its inputs.")
    return compare_policies(_dataset, Assumptions.from_dict(json.loads(assumption_json)))


@st.cache_data(max_entries=4, show_spinner=False)
def cached_downloads(run_id, model_version, _result, _results, _dataset):
    if run_id != _result.run_id or model_version != MODEL_VERSION:
        raise ValueError("Download identity does not match the selected result.")
    return csv_package(_result, _dataset), scenario_workbook(_result, _results, _dataset)


@st.cache_data(max_entries=3, show_spinner=False)
def cached_sensitivity(assumption_json, dataset_hash, policy, model_version, _dataset):
    if dataset_hash != _dataset.dataset_hash or model_version != MODEL_VERSION:
        raise ValueError("Stress cache identity does not match its inputs.")
    return sensitivity(_dataset, Assumptions.from_dict(json.loads(assumption_json)), policy)


def inputs_from_controls():
    s = st.session_state
    rates = {"borrower_rate": "borrower_percent", "merchant_fee": "merchant_percent", "pd_low": "low_percent",
             "pd_medium": "medium_percent", "pd_high": "high_percent", "recovery_rate": "recovery_percent",
             "funding_rate": "funding_percent", "advance_rate": "advance_percent", "demand_growth": "growth_percent",
             "loss_cap": "loss_cap_percent"}
    inputs = {name: D(str(s[control])) / 100 for name, control in rates.items()}
    inputs.update(default_stress=D(str(s.stress)), initial_cash=D(str(s.initial_cash)),
                  facility_limit=D(str(s.facility)), acquisition_cost=D(str(s.acquisition)),
                  servicing_cost=D(str(s.servicing)), monthly_opex=D(str(s.opex)),
                  cash_floor=D(str(s.cash_floor)), recovery_lag=s.lag)
    a = Assumptions(**inputs)
    a.validate()
    return a


def apply_scenario(a, policy, dataset):
    assumption_json = json.dumps(a.to_dict(), sort_keys=True)
    results = cached_results(assumption_json, dataset.dataset_hash, dataset.version, MODEL_VERSION, dataset)
    st.session_state.update(applied_assumptions=a, applied_policy=policy, results=results)


def reset_scenario():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    st.session_state["reset_requested"] = True
    st.session_state.pop("stress_points", None)


def chart(fig, height=330):
    fig.update_layout(height=height, margin=dict(l=15, r=15, t=20, b=35),
                      font=dict(family="Arial", size=12, color="#182c3e"),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=1.08, x=0), hovermode="x unified")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#e3e9ef", zerolinecolor="#8293a4")
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "responsive": True})


def line_plot(frame, fields, ytitle="USD"):
    fig = go.Figure()
    palette = ["#145b72", "#8a477b", "#84734d"]
    for i, (field, label) in enumerate(fields):
        fig.add_scatter(x=frame["period"], y=frame[field], name=label, mode="lines",
                        line=dict(color=palette[i % len(palette)], width=2.5,
                                  dash="solid" if i == 0 else "dash"),
                        hovertemplate="%{x}: $%{y:,.0f}<extra>%{fullData.name}</extra>")
    fig.update_yaxes(title=ytitle, tickprefix="$", tickformat=",.0f")
    return fig


st.set_page_config(page_title="Lending Profitability & Risk Simulator", page_icon="📊", layout="wide")
st.title("Lending Profitability & Risk Simulator")
st.caption("Synthetic expected-value projections · 12-month retained loans · USD · historical calibration unavailable")
try:
    csv_digest = sha256((ROOT / "data" / "applications.csv").read_bytes()).hexdigest()
    manifest_digest = sha256((ROOT / "data" / "manifest.json").read_bytes()).hexdigest()
    dataset = get_dataset(csv_digest, manifest_digest, "synthetic-applications-v1")
except (ValueError, OSError) as error:
    st.error(f"Base dataset could not be loaded: {error}")
    st.stop()
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)
if "results" not in st.session_state or st.session_state.pop("reset_requested", False):
    apply_scenario(Assumptions(), "conservative", dataset)
elif any(result.dataset_hash != dataset.dataset_hash for result in st.session_state.results):
    apply_scenario(st.session_state.applied_assumptions, st.session_state.applied_policy, dataset)
    st.session_state.pop("stress_points", None)

with st.sidebar:
    st.subheader("Scenario")
    st.button("Reset to base", key="reset", on_click=reset_scenario, width="stretch")
    with st.form("scenario_form"):
        st.selectbox("Approval policy", list(POLICIES), format_func=str.title, key="policy")
        st.slider("Monthly application growth (%)", -10.0, 10.0, step=.5, key="growth_percent",
                  help="Weights the fixed applicant population. Changes neither risk mix nor pricing.")
        st.slider("Lifetime default stress (×)", 0.0, 5.0, step=.25, key="stress")
        st.slider("Annual funding rate (%)", 0.0, 30.0, step=.5, key="funding_percent")
        st.number_input("Starting equity cash ($)", step=50000.0, key="initial_cash")
        with st.expander("Credit and cash limits"):
            st.number_input("Net principal loss cap (%)", step=.5, key="loss_cap_percent")
            st.number_input("Minimum month-end cash ($)", step=10000.0, key="cash_floor")
            st.caption("Illustrative management limits. Both apply to the full-runoff horizon.")
        with st.expander("Advanced assumptions"):
            st.number_input("Annual nominal borrower rate (%)", step=1.0, key="borrower_percent")
            st.number_input("Merchant fee (%)", step=.5, key="merchant_percent")
            st.number_input("Low-band lifetime PD (%)", step=1.0, key="low_percent")
            st.number_input("Medium-band lifetime PD (%)", step=1.0, key="medium_percent")
            st.number_input("High-band lifetime PD (%)", step=1.0, key="high_percent")
            st.number_input("Recovery of charged-off principal (%)", step=5.0, key="recovery_percent")
            st.number_input("Recovery lag (months)", step=1, key="lag")
            st.number_input("Collateral advance rate (%)", step=5.0, key="advance_percent")
            st.number_input("Facility limit ($)", step=250000.0, key="facility")
            st.number_input("Acquisition cost / funded loan ($)", step=5.0, key="acquisition")
            st.number_input("Servicing cost / surviving loan / month ($)", step=.5, key="servicing")
            st.number_input("Platform operating expense / month ($)", step=500.0, key="opex")
        run = st.form_submit_button("Run scenario", key="run_scenario", type="primary", width="stretch")
    if run:
        try:
            with st.spinner("Comparing three policies…"):
                apply_scenario(inputs_from_controls(), st.session_state.policy, dataset)
        except (ValueError, ArithmeticError) as error:
            st.error(f"Scenario could not run: {error}. Showing the last successful result.")

results = st.session_state.results
a = st.session_state.applied_assumptions
selected = next(r for r in results if r.policy == st.session_state.applied_policy)
s = selected.summary
frame = monthly_frame(selected)
comparison = comparison_frame(results)
decision = select_strategy(results)
st.caption(f"Applied scenario: {selected.policy.title()} · {len(selected.monthly)} months through {month_label(len(selected.monthly) - 1)} · run {selected.run_id}")
if decision.recommended_policy:
    st.success(decision.message)
else:
    st.warning(decision.message)
st.caption(f"Eligibility: net principal loss ≤ {percent(a.loss_cap)} and month-end cash ≥ {money(a.cash_floor)}. Rank by unrounded full-runoff operating profit.")
tabs = st.tabs(["Overview", "Strategy comparison", "Portfolio cohorts", "Funding & stress", "Methodology"])

with tabs[0]:
    st.subheader(f"{selected.policy.title()} economics")
    left, middle, right = st.columns(3)
    left.metric("Operating result · full runoff", money(s.operating_result),
                help="Interest + merchant fees − funding, servicing, acquisition, net principal loss and all platform costs.")
    middle.metric("Net principal loss ratio", percent(s.loss_ratio), help="Full-runoff net charged-off principal / original funded principal.")
    right.metric("Lowest month-end cash", money(s.minimum_cash), help=f"Occurs in {month_label(s.minimum_cash_month)}; includes runoff.")
    eligibility = evaluate_policy(selected)
    if not eligibility.eligible:
        st.warning(f"{selected.policy.title()} is ineligible: {'; '.join(eligibility.reasons)}.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Funded principal", money(s.funded_principal))
    c2.metric("Approval rate", percent(s.approval_rate), help="Expected funded loans / expected applications, using the same demand weights.")
    c3.metric("Contribution / funded loan", money(s.unit_contribution), help="Full-runoff contribution before platform operating expense / expected funded loans.")
    st.caption(f"First 24 months operating result: {money(s.operating_result_24m)}. Full-runoff contribution: {money(s.contribution)}. Expected funded loans: {s.funded_loans:,.1f}.")
    st.subheader("Profit and liquidity over time")
    chart(line_plot(frame, [("cumulative_operating_result", "Cumulative operating result"), ("ending_cash", "Month-end cash")]))
    st.caption("Profit includes noncash charge-offs. Cash reflects the original loan advance, actual expected collections and debt draws/repayments.")

with tabs[1]:
    st.subheader("Shared demand, pricing, and comparison horizon")
    fig = px.bar(comparison, x="Policy", y="Operating result (full runoff)", color="Policy", color_discrete_map=COLORS,
                 custom_data=["Minimum cash", "Net principal loss ratio", "Reason"])
    fig.update_traces(hovertemplate="%{x}<br>Operating result: $%{y:,.0f}<br>Minimum cash: $%{customdata[0]:,.0f}<br>Net loss: %{customdata[1]:.2%}<br>%{customdata[2]}<extra></extra>")
    fig.update_layout(showlegend=False)
    fig.update_yaxes(title="Full-runoff operating result (USD)", tickprefix="$", rangemode="tozero")
    chart(fig)
    display = comparison.drop(columns=["Run ID", "Expected funded loans"]).copy()
    for column in display:
        if column in ("Approval rate", "Net principal loss ratio"):
            display[column] = display[column].map(lambda v: "n.a." if pd.isna(v) else f"{v:.2%}")
        elif column not in ("Policy", "Eligible", "Reason"):
            display[column] = display[column].map(lambda v: "n.a." if pd.isna(v) else money(v))
    st.dataframe(display, hide_index=True, width="stretch")
    st.caption("Conservative approves low risk; balanced approves low + medium; aggressive approves all bands. Additional equity changes cash eligibility, not modeled profit.")

with tabs[2]:
    st.subheader("Projected cohort loss by loan age")
    view = st.radio("Cohort cutoff", ["First 24 months", "Complete runoff"], horizontal=True, key="cohort_cutoff")
    heatmap = cohort_heatmap(selected, 23 if view == "First 24 months" else None)
    fig = go.Figure(go.Heatmap(z=heatmap.values * 100, x=list(heatmap.columns),
                              y=[month_label(m) for m in heatmap.index], colorscale="Blues", zmin=0,
                              colorbar=dict(title="Net loss %"), hoverongaps=False,
                              hovertemplate="Origination: %{y}<br>Age: %{x} months<br>Projected net loss: %{z:.2f}%<extra></extra>"))
    fig.update_xaxes(title="Months since origination")
    fig.update_yaxes(autorange="reversed")
    chart(fig, height=480)
    st.caption("Net charged-off principal after received recoveries / each cohort's original funded principal. Future ages are blank at the selected cutoff. Every value is projected.")
    curves = band_curves(selected)
    if curves.empty:
        st.info("No funded cohorts under this policy; risk-band ratios are unavailable.")
    else:
        st.subheader("Risk-band repayment and net loss")
        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(curves, x="age", y="principal_repaid_ratio", color="risk_band", markers=True,
                          labels={"age": "Loan age (months)", "principal_repaid_ratio": "Principal repaid / originated", "risk_band": "Risk band"})
            fig.update_yaxes(tickformat=".0%", range=[0, 1])
            chart(fig, 300)
        with c2:
            fig = px.line(curves, x="age", y="net_loss_ratio", color="risk_band", markers=True,
                          labels={"age": "Loan age (months)", "net_loss_ratio": "Net loss / originated", "risk_band": "Risk band"})
            fig.update_yaxes(tickformat=".1%", rangemode="tozero")
            chart(fig, 300)

with tabs[3]:
    st.subheader("Cash and debt facility")
    fig = line_plot(frame, [("ending_cash", "Month-end cash"), ("ending_debt", "Drawn debt")])
    fig.add_hline(y=float(a.cash_floor), line_dash="dot", line_color="#b24a3a", annotation_text="Cash floor")
    chart(fig)
    c1, c2, c3 = st.columns(3)
    c1.metric("Additional equity to meet floor", money(s.additional_equity_required))
    c2.metric("Peak drawn debt", money(s.peak_debt))
    c3.metric("Minimum facility headroom", money(s.minimum_facility_headroom))
    st.caption("Negative cash is an unfunded diagnostic path. No extra equity appears automatically. Debt is capped at the lesser of the facility limit and collateral advance; defaults can require repayments.")
    st.subheader("Default and funding stress")
    st.caption("Absolute lifetime-PD multipliers (0.5× to 3×) and annual funding rates (4% to 16%). Other applied inputs stay fixed.")
    if st.button("Run stress grid", key="run_stress"):
        with st.spinner("Calculating stress cases…"):
            points = cached_sensitivity(json.dumps(a.to_dict(), sort_keys=True), dataset.dataset_hash, selected.policy, MODEL_VERSION, dataset)
            st.session_state.stress_points = {"run_id": selected.run_id, "points": points}
    saved = st.session_state.get("stress_points")
    if saved and saved["run_id"] == selected.run_id:
        stress_frame = pd.DataFrame(saved["points"])
        for field in ("default_stress", "funding_rate", "operating_result", "contribution", "minimum_cash", "loss_ratio", "additional_equity_required"):
            stress_frame[field] = stress_frame[field].astype(float)
        grid = stress_frame.pivot(index="default_stress", columns="funding_rate", values="operating_result")
        status = stress_frame.pivot(index="default_stress", columns="funding_rate", values="eligible")
        text = [[f"{money(grid.loc[i, j])}<br>{'Eligible' if status.loc[i, j] else 'Ineligible'}" for j in grid.columns] for i in grid.index]
        fig = go.Figure(go.Heatmap(z=grid.values, x=[f"{x:.0%}" for x in grid.columns], y=[f"{x:g}×" for x in grid.index],
                                  text=text, texttemplate="%{text}", colorscale="RdBu", zmid=0,
                                  colorbar=dict(title="Profit ($)"), hovertemplate="Funding: %{x}<br>Default stress: %{y}<br>%{text}<extra></extra>"))
        fig.update_xaxes(title="Annual funding rate")
        fig.update_yaxes(title="Lifetime default multiplier")
        chart(fig, 380)
        with st.expander("Stress contribution, cash gaps, and failure reasons"):
            st.dataframe(stress_frame.drop(columns="run_id"), hide_index=True, width="stretch")
    else:
        st.info("Run the grid to compare profit, cash eligibility, and credit limits across stress cases.")
    with st.expander("Monthly funding and cash detail"):
        st.dataframe(frame[["period", "ending_principal", "ending_debt", "net_debt_draw", "funding_expense", "ending_cash"]], hide_index=True, width="stretch")

with tabs[4]:
    st.subheader("Financial timing and checks")
    st.markdown("Loans originate at month-end. From the following month, defaults occur before scheduled payments. Survivors pay interest and principal; recoveries arrive after the chosen lag. Debt adjusts to ending collateral, and interest uses opening debt.")
    st.markdown("Principal collections reduce the loan asset. A charge-off removes principal and future collections; it creates no second cash outflow. Net credit expense equals gross charge-offs minus received recoveries. Platform costs continue throughout the common runoff horizon.")
    st.caption("Simplified management accounting. No GAAP allowance/provision, taxes, prepayment, delinquency stages, price response, intramonth liquidity, or rejected-applicant outcome model.")
    check_values = {k.replace("_", " ").title(): str(v) for k, v in asdict(selected.checks).items()}
    st.dataframe(pd.DataFrame(check_values.items(), columns=["Check", "Result"]), hide_index=True, width="stretch")
    st.subheader("Assumptions register")
    st.dataframe(pd.DataFrame(assumption_register(a)), hide_index=True, width="stretch")
    st.caption(f"Effective lifetime PD after stress: low {percent(a.lifetime_pd('low'))}, medium {percent(a.lifetime_pd('medium'))}, high {percent(a.lifetime_pd('high'))}. Values above 100% are capped.")
    st.subheader("Historical evidence and data fitness")
    evidence = evidence_register()
    st.warning(evidence["decision"])
    for source in evidence["sources"]:
        st.markdown(f"[{source['publisher']}]({source['url']}) — {source['suitability']}")
    st.caption("No historical default forecast, held-out evaluation, or borrower-level calibration was performed. Longer-term cumulative loss and annualized loss cannot be treated as 12-month PD.")
    with st.expander("Dataset and SQL"):
        st.json(dataset.manifest())
        st.dataframe(pd.DataFrame(policy_population(dataset)), hide_index=True, width="stretch")
        st.caption("These SQL counts describe the unweighted base dataset; scenario counts use explicit growth weights.")
        st.code(query_text("policy_population"), language="sql")
        st.code(query_text("cohort_inputs"), language="sql")
    with st.expander("Selected run manifest"):
        st.json(selected.manifest())

st.divider()
st.subheader("Download applied scenario")
st.caption("Downloads match the displayed applied scenario. Portfolio workbook cells are saved outputs; its two independent benchmark sheets recalculate from their blue inputs.")
csv_bytes, workbook_bytes = cached_downloads(selected.run_id, MODEL_VERSION, selected, results, dataset)
c1, c2 = st.columns(2)
with c1:
    st.download_button("CSV results + manifest", csv_bytes, f"lending-{selected.run_id}.zip", "application/zip", key="csv_download", width="stretch")
with c2:
    st.download_button("Audit workbook", workbook_bytes, f"lending-{selected.run_id}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="workbook_download", width="stretch")
