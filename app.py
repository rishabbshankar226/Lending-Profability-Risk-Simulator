"""Lending workbench. Applied financial results are immutable until an explicit run."""

from dataclasses import replace
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
import json

import pandas as pd
import streamlit as st

from lending_simulator import MODEL_VERSION
from lending_simulator.data import DEFAULT_SEED, load_dataset
from lending_simulator.decisions import compare_policies, select_strategy, sensitivity
from lending_simulator.presentation import assumption_register
from lending_simulator.types import Assumptions, POLICIES
from lending_simulator.ui.components import caption, decision_summary, readable_table
from lending_simulator.ui.data import ScenarioSnapshot
from lending_simulator.ui.downloads import download_factory
from lending_simulator.ui.formatting import money, percent, multiple, assumption_value
from lending_simulator.ui.state import FIELDS, controls_for, parse_controls, draft_changes, stage_case
from lending_simulator.ui.theme import apply_styles
from lending_simulator.ui.views import ViewContext, render

ROOT = Path(__file__).resolve().parent
VIEWS = ("Overview", "Policies", "Cohorts", "Funding & stress", "Methodology")


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


@st.cache_data(max_entries=3, show_spinner=False)
def cached_sensitivity(assumption_json, dataset_hash, policy, model_version, _dataset):
    if _dataset.dataset_hash != dataset_hash or model_version != MODEL_VERSION:
        raise ValueError("Stress cache identity does not match its inputs.")
    return sensitivity(_dataset, Assumptions.from_dict(json.loads(assumption_json)), policy)


def clear_stress():
    for key in ("stress_points", "stress_case", "stress_case_view", "stress_metric", "stress_metric_view"):
        st.session_state.pop(key, None)


def apply_scenario(a, policy, dataset, *, replace_draft=True):
    results = cached_results(json.dumps(a.to_dict(), sort_keys=True), dataset.dataset_hash,
                             dataset.version, MODEL_VERSION, dataset)
    # Check the complete bundle before publishing the transaction.
    select_strategy(results)
    previous = st.session_state.get("results")
    if previous is None or tuple(r.run_id for r in previous) != tuple(r.run_id for r in results):
        clear_stress()
    st.session_state.update(applied_assumptions=a, applied_policy=policy, results=results)
    if replace_draft:
        st.session_state.draft_controls = controls_for(a)
    st.session_state.pop("scenario_error", None)


def set_controls(controls):
    st.session_state.draft_controls = dict(controls)
    for key, value in controls.items():
        st.session_state[key] = value


def sync_draft():
    old = st.session_state.draft_controls
    st.session_state.draft_controls = {key: st.session_state.get(key, old[key]) for _, key, _, _ in FIELDS}
    st.session_state.pop("scenario_error", None)


def restore_applied():
    set_controls(controls_for(st.session_state.applied_assumptions))
    st.session_state.pop("scenario_error", None)


def load_example(overrides, policy="conservative", reset=False):
    set_controls(controls_for(replace(Assumptions(), **overrides)))
    st.session_state.update(policy=policy, requested_policy=policy, apply_requested=True,
                            cohort_view="First 24 months", cohort_cutoff="First 24 months")
    clear_stress()
    st.session_state.pop("scenario_error", None)
    if reset:
        st.session_state.update(active_view="Overview", analysis_view="Overview")
        st.session_state.pop("baseline", None)


def reset_scenario():
    load_example({}, reset=True)


def view_policy(policy):
    if policy not in POLICIES:
        raise ValueError("Unknown viewed policy.")
    if st.session_state.applied_policy != policy:
        clear_stress()
    st.session_state.update(policy=policy, applied_policy=policy)


def sync_policy():
    view_policy(st.session_state.policy)


def navigate(view):
    st.session_state.update(active_view=view, analysis_view=view)


def sync_navigation():
    st.session_state.active_view = st.session_state.analysis_view


def inspect_credit():
    st.session_state.credit_editor = True


def sync_cohort():
    st.session_state.cohort_view = st.session_state.cohort_cutoff


def pin_baseline():
    st.session_state.baseline = ScenarioSnapshot.capture(st.session_state.results)


def clear_baseline():
    st.session_state.pop("baseline", None)


def current_result():
    return next(r for r in st.session_state.results if r.policy == st.session_state.applied_policy)


def run_stress():
    r = current_result()
    with st.spinner("Calculating 20 selected-policy stress cases…"):
        points = cached_sensitivity(json.dumps(r.assumptions.to_dict(), sort_keys=True),
                                    r.dataset_hash, r.policy, MODEL_VERSION, dataset)
    st.session_state.stress_points = {"run_id": r.run_id, "points": points}
    for key in ("stress_case", "stress_case_view", "stress_metric", "stress_metric_view"):
        st.session_state.pop(key, None)


def sync_stress_case():
    st.session_state.stress_case_view = st.session_state.stress_case


def sync_stress_metric():
    st.session_state.stress_metric_view = st.session_state.stress_metric


def stage_stress():
    saved = st.session_state.get("stress_points")
    try:
        if not saved or saved["run_id"] != current_result().run_id:
            raise ValueError("Run a stress grid for this applied policy before staging a case.")
        point = saved["points"][st.session_state.stress_case]
        set_controls(stage_case(st.session_state.applied_assumptions, st.session_state.draft_controls, point))
    except (ValueError, ArithmeticError) as error:
        st.session_state.scenario_error = str(error)


st.set_page_config(page_title="Lending Profitability & Risk Simulator", page_icon="📊", layout="wide")
apply_styles()
st.title("Lending workbench")
caption("Compare lending policies under cash and credit limits. Synthetic, illustrative, uncalibrated projections · USD.")
try:
    dataset = get_dataset(sha256((ROOT / "data" / "applications.csv").read_bytes()).hexdigest(),
                          sha256((ROOT / "data" / "manifest.json").read_bytes()).hexdigest(),
                          "synthetic-applications-v1")
except (ValueError, OSError) as error:
    st.error(f"Base dataset could not be loaded: {error}")
    st.stop()

s = st.session_state
s.setdefault("draft_controls", controls_for(Assumptions()))
s.setdefault("policy", "conservative")
s.setdefault("active_view", "Overview")
s.setdefault("analysis_view", s.active_view)
s.setdefault("cohort_view", "First 24 months")
for _, key, _, _ in FIELDS:
    s.setdefault(key, s.draft_controls[key])
apply_requested = s.pop("apply_requested", False)
if "results" not in s or apply_requested:
    try:
        apply_scenario(parse_controls(s.draft_controls), s.pop("requested_policy", s.policy), dataset)
    except (ValueError, ArithmeticError) as error:
        s.scenario_error = str(error)
        if "results" not in s:
            st.error(s.scenario_error)
            st.stop()
elif any(r.dataset_hash != dataset.dataset_hash for r in s.results):
    apply_scenario(s.applied_assumptions, s.applied_policy, dataset, replace_draft=False)

with st.sidebar:
    st.header("Scenario")
    caption("Edit inputs, then Run scenario. Results stay on applied assumptions.")
    with st.expander("One-click examples"):
        caption("Replace all financial inputs and run immediately. A pinned baseline is retained.")
        st.button("Base case", key="example_base", on_click=load_example, args=({},), width="stretch")
        st.button("More capital · $1.25m", key="example_capital", on_click=load_example,
                  args=({"initial_cash": D(1250000)}, "balanced"), width="stretch")
        st.button("Higher defaults · 2×", key="example_defaults", on_click=load_example,
                  args=({"default_stress": D(2)},), width="stretch")
    st.slider("Monthly application growth (%)", -10.0, 10.0, step=.5, key="growth_percent",
              on_change=sync_draft, help="Weights the fixed population, without changing risk mix or prices.")
    st.slider("Lifetime default stress (×)", 0.0, 5.0, step=.25, key="stress", on_change=sync_draft)
    st.slider("Annual funding rate (%)", 0.0, 30.0, step=.5, key="funding_percent", on_change=sync_draft)
    st.number_input("Starting equity cash ($)", step=50000.0, key="initial_cash", on_change=sync_draft)
    with st.expander("Capital & funding"):
        st.number_input("Facility limit ($)", step=250000.0, key="facility", on_change=sync_draft)
        st.number_input("Collateral advance rate (%)", step=5.0, key="advance_percent", on_change=sync_draft)
    credit_editor = st.expander("Credit assumptions", expanded=s.get("credit_editor", False),
                                key="credit_editor")
    with credit_editor:
        st.number_input("Low-band lifetime PD (%)", step=1.0, key="low_percent", on_change=sync_draft)
        st.number_input("Medium-band lifetime PD (%)", step=1.0, key="medium_percent", on_change=sync_draft)
        st.number_input("High-band lifetime PD (%)", step=1.0, key="high_percent", on_change=sync_draft)
        st.number_input("Recovery of charged-off principal (%)", step=5.0, key="recovery_percent", on_change=sync_draft)
        st.number_input("Recovery lag (months)", step=1, key="lag", on_change=sync_draft)
        try:
            risk = replace(Assumptions(), default_stress=D(str(s.stress)),
                           pd_low=D(str(s.low_percent))/100, pd_medium=D(str(s.medium_percent))/100,
                           pd_high=D(str(s.high_percent))/100)
            risk.validate()
            caption("Draft effective lifetime PD: "+", ".join(
                f"{band.title()} {percent(risk.lifetime_pd(band))}" for band in ("low","medium","high"))+".")
            if any(risk.lifetime_pd(band) == 1 for band in ("low","medium","high")):
                st.info("A risk band reaches the 100% effective lifetime-PD cap.")
        except (ValueError, ArithmeticError):
            caption("Draft PD preview unavailable. Correct the credit inputs to see it.")
    with st.expander("Credit and cash limits"):
        st.number_input("Net principal loss cap (%)", step=.5, key="loss_cap_percent", on_change=sync_draft)
        st.number_input("Minimum month-end cash ($)", step=10000.0, key="cash_floor", on_change=sync_draft)
        caption("Illustrative limits apply through complete runoff, using unrounded values.")
    with st.expander("Advanced economics"):
        st.number_input("Annual nominal borrower rate (%)", step=1.0, key="borrower_percent", on_change=sync_draft)
        st.number_input("Merchant fee (%)", step=.5, key="merchant_percent", on_change=sync_draft)
        st.number_input("Acquisition cost / funded loan ($)", step=5.0, key="acquisition", on_change=sync_draft)
        st.number_input("Servicing cost / surviving loan / month ($)", step=.5, key="servicing", on_change=sync_draft)
        st.number_input("Platform operating expense / month ($)", step=500.0, key="opex", on_change=sync_draft)
    draft_notice = st.container()
    if st.button("Run scenario", key="run_scenario", type="primary", width="stretch"):
        try:
            with st.spinner("Comparing three policies…"):
                apply_scenario(parse_controls(s.draft_controls), s.applied_policy, dataset)
            st.success("Scenario applied. Results compare all three policies.")
        except (ValueError, ArithmeticError) as error:
            s.scenario_error = str(error)
    changes = draft_changes(s.draft_controls, s.applied_assumptions)
    if changes:
        with draft_notice:
            st.info("Unapplied changes · Results use the last successful scenario.")
            with st.expander(f"Review {len(changes)} changed inputs"):
                readable_table(pd.DataFrame([{"Input":c.label,
                    "Applied":assumption_value(c.field,c.before),
                    "Draft":assumption_value(c.field,c.after)} for c in changes]))
    if s.get("scenario_error"):
        st.error(f"Scenario could not run: {s.scenario_error} Showing the last successful result.")
    if changes:
        st.button("Restore applied inputs", key="restore_applied", on_click=restore_applied, width="stretch")
    st.button("Reset to base", key="reset", on_click=reset_scenario, width="stretch",
              help="Restore base inputs, Conservative, Overview, and cohort cutoff; clear stress and baseline.")

selected = current_result()
a = s.applied_assumptions
decision = select_strategy(s.results)
with st.container(horizontal=True, wrap=True, vertical_alignment="center", key="workbench_toolbar"):
    st.selectbox("Viewed policy", list(POLICIES), format_func=str.title, key="policy",
                 on_change=sync_policy, width=240)
    with st.popover("Applied inputs"):
        caption(f"Starting equity: {money(a.initial_cash)} · Default stress: {multiple(a.default_stress)} · "
                f"Annual funding: {percent(a.funding_rate)} · Monthly growth: {percent(a.demand_growth)} · "
                f"Facility: {money(a.facility_limit)}.")
        st.dataframe(pd.DataFrame(assumption_register(a)), hide_index=True, width="stretch")
        caption(f"Applied run: {selected.run_id} · Model {MODEL_VERSION} · Dataset {dataset.version}.")
    with st.popover("Export", key="exports_panel", help="Download the viewed applied scenario"):
        caption(f"{selected.policy.title()} · Applied run {selected.run_id}. Draft edits are not exported.")
        formats = (
            ("brief","Decision brief",f"lending-decision-{selected.run_id}.md","text/markdown","brief_download"),
            ("workbook","Audit workbook",f"lending-{selected.run_id}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","workbook_download"),
            ("csv","CSV results + manifest",f"lending-{selected.run_id}.zip","application/zip","csv_download"),
        )
        for kind,label,filename,mime,key in formats:
            st.download_button(label, download_factory(kind,selected,s.results,dataset),filename,mime,
                               key=f"{key}_{selected.run_id}",on_click="ignore",width="stretch")
        caption("Brief: decision and exact inputs. Workbook: saved portfolio outputs plus editable benchmarks. CSV: exact schedules and reproducibility.")
        preview = st.expander("Preview decision brief", key="brief_preview", on_change="rerun")
        with preview:
            if preview.open:
                brief = download_factory("brief",selected,s.results,dataset)()
                st.markdown(brief.replace("# Lending decision brief\n","### Lending decision brief\n",1)
                            .replace("\n## ","\n#### ").replace("$",r"\$"))

st.segmented_control("Analysis", VIEWS, required=True, key="analysis_view",
                     on_change=sync_navigation, wrap=True, width="stretch", label_visibility="collapsed")
decision_summary(selected, decision, view_policy)
actions = {"view":view_policy,"navigate":navigate,"credit":inspect_credit,"cohort":sync_cohort,
           "pin":pin_baseline,"clear_baseline":clear_baseline,"stress":run_stress,
           "stress_case":sync_stress_case,"stress_metric":sync_stress_metric,"stage":stage_stress}
render(s.active_view, ViewContext(selected, s.results, dataset, decision, actions))
