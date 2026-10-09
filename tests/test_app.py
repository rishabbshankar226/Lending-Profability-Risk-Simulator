from streamlit.testing.v1 import AppTest
from pathlib import Path
from dataclasses import replace
from decimal import Decimal
import json
import shutil

import pytest
import streamlit as st

from lending_simulator.types import Assumptions
from lending_simulator.data import Dataset, load_dataset, save_dataset
from lending_simulator.decisions import select_strategy


def app():
    return AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=20).run()


def test_preloaded_dashboard_has_five_views_results_and_no_exception():
    page = app()
    assert not page.exception
    assert [t.label for t in page.tabs] == ["Overview", "Strategy comparison", "Portfolio cohorts", "Funding & stress", "Methodology"]
    assert page.session_state["applied_policy"] == "conservative"
    assert len(page.session_state["results"]) == 3
    assert all(r.checks.passed for r in page.session_state["results"])
    assert page.metric[0].label == "Operating result · full runoff"


def test_decision_panel_shows_recommendation_viewed_policy_and_limit_margins():
    page = app()
    assert not page.exception
    assert page.header[0].value == "Recommended policy: Conservative"
    assert any("Viewing policy: Conservative" in item.value for item in page.markdown)
    assert [(metric.label, metric.value) for metric in page.metric[:3]] == [
        ("Operating result · full runoff", "$48,133"),
        ("Cash cushion above floor", "$97,450"),
        ("Loss headroom to cap", "4.16 pp"),
    ]
    captions = "\n".join(item.value for item in page.caption)
    assert "Minimum cash:" in captions and "147,450" in captions and "50,000" in captions
    assert "Net principal loss: 0.84% · Cap: 5.00%" in captions
    assert "pp = percentage points" in captions


def test_decision_sections_follow_the_page_title_without_skipping_a_heading_level():
    page = app()
    assert [item.value for item in page.title] == ["Lending Profitability & Risk Simulator"]
    assert [item.value for item in page.main.header[:2]] == [
        "Recommended policy: Conservative", "Explore a scenario",
    ]


def test_viewing_ineligible_policy_keeps_recommendation_and_identifies_cash_shortfall():
    page = app()
    page.selectbox(key="policy").set_value("balanced")
    page.button(key="run_scenario").click().run()
    assert not page.exception
    assert page.header[0].value == "Recommended policy: Conservative"
    assert any("Viewing policy: Balanced" in item.value for item in page.markdown)
    assert [(metric.label, metric.value) for metric in page.metric[:3]] == [
        ("Operating result · full runoff", "$294,468"),
        ("Cash shortfall to floor", "$746,143"),
        ("Loss headroom to cap", "3.42 pp"),
    ]
    assert any("Charts and downloads show Balanced" in item.value for item in page.caption)
    assert page.session_state["applied_policy"] == "balanced"
    assert page.session_state["results"][1].run_id == "a2feec5a72facbc3"


@pytest.mark.parametrize("overrides, explanation, diagnostic", [
    ({"stress": 2.0}, "No eligible strategy is profitable", "Conservative"),
    ({"initial_cash": 0.0}, "No policy meets", None),
])
def test_decision_panel_does_not_present_a_diagnostic_policy_as_a_recommendation(
        overrides, explanation, diagnostic):
    page = app()
    for key, value in overrides.items():
        control = page.slider if key == "stress" else page.number_input
        control(key=key).set_value(value)
    page.button(key="run_scenario").click().run()
    assert not page.exception
    assert page.header[0].value == "Recommended policy: None"
    assert any(explanation in item.value for item in page.warning)
    captions = "\n".join(item.value for item in page.caption)
    assert ("Diagnostic policy:" in captions) == (diagnostic is not None)
    if diagnostic:
        assert f"Diagnostic policy: {diagnostic}" in captions


def test_applied_input_summary_retains_last_successful_run_after_draft_or_invalid_edits():
    page = app()
    page.button(key="example_capital").click().run()

    def input_summary():
        return next(item.value for item in page.caption if item.value.startswith("Starting equity:"))

    applied = input_summary()
    assert "1,250,000" in applied and "Default stress: 1×" in applied
    assert "Annual funding: 8.00%" in applied and "Monthly growth: 0.00%" in applied
    assert "Facility: " in applied and "2,000,000" in applied
    page.slider(key="stress").set_value(3.0)
    page.radio(key="cohort_cutoff").set_value("Complete runoff").run()
    assert input_summary() == applied
    page.number_input(key="cash_floor").set_value(-1.0)
    page.button(key="run_scenario").click().run()
    assert not page.exception
    assert page.error
    assert input_summary() == applied
    assert page.header[0].value == "Recommended policy: Balanced"


def test_decision_panel_identifies_a_credit_loss_breach_in_percentage_points():
    page = app()
    page.number_input(key="loss_cap_percent").set_value(0.5)
    page.button(key="run_scenario").click().run()
    assert not page.exception
    assert page.header[0].value == "Recommended policy: None"
    assert page.metric[2].label == "Loss cap exceeded by"
    assert page.metric[2].value == "0.34 pp"
    assert any("Net principal loss: 0.84% · Cap: 0.50%" in item.value for item in page.caption)


def test_apply_and_complete_reset_restore_assumptions_and_download_scenario():
    page = app()
    base_run = page.session_state["results"][0].run_id
    page.slider(key="funding_percent").set_value(12.0)
    page.number_input(key="opex").set_value(10000.0)
    page.radio(key="cohort_cutoff").set_value("Complete runoff")
    page.selectbox(key="policy").set_value("balanced")
    page.button(key="run_scenario").click().run()
    assert not page.exception
    assert page.session_state["applied_policy"] == "balanced"
    assert str(page.session_state["applied_assumptions"].funding_rate) == "0.12"
    assert page.session_state["applied_assumptions"].monthly_opex == 10000
    assert page.session_state["results"][0].run_id != base_run
    page.button(key="reset").click().run()
    assert not page.exception
    assert page.session_state["applied_assumptions"] == Assumptions()
    assert page.session_state["applied_policy"] == "conservative"
    assert page.session_state["results"][0].run_id == base_run
    assert page.number_input(key="opex").value == 7500.0
    assert page.radio(key="cohort_cutoff").value == "First 24 months"


def test_running_unchanged_base_controls_preserves_the_run_identity():
    page = app()
    base = page.session_state["results"][0].run_id
    page.button(key="run_scenario").click().run()
    assert not page.exception
    assert page.session_state["results"][0].run_id == base


def test_decision_brief_follows_applied_examples_and_retains_last_valid_run():
    page = app()

    def preview():
        return next(e for e in page.expander if e.label == "Preview decision brief").markdown[0].value

    base = preview()
    assert "Recommended policy: Conservative" in base
    assert '"run_id": "5a88f7bef3fa93d4"' in base
    page.button(key="example_capital").click().run()
    capital = preview()
    assert "Recommended policy: Balanced" in capital
    assert '"run_id": "690e9fa563e2d475"' in capital
    page.number_input(key="cash_floor").set_value(-1.0)
    assert preview() == capital
    page.button(key="run_scenario").click().run()
    assert not page.exception
    assert page.error
    assert preview() == capital
    page.button(key="example_defaults").click().run()
    assert "Recommended policy: None" in preview()
    assert '"default_stress": "2"' in preview()
    page.button(key="reset").click().run()
    assert not page.exception
    assert preview() == base
    downloads = page.get("download_button")
    assert any(d.proto.label == "Decision brief" for d in downloads)


def test_unsaved_controls_do_not_replace_results_until_run_and_visitors_are_isolated():
    one = app()
    two = app()
    old = one.session_state["results"][0].run_id
    one.slider(key="stress").set_value(2.0)
    assert one.session_state["results"][0].run_id == old
    one.button(key="run_scenario").click().run()
    assert not one.exception
    assert one.session_state["applied_assumptions"].default_stress == 2
    assert one.session_state["results"][0].run_id != old
    assert two.session_state["results"][0].run_id == old


def test_cash_floor_breach_is_explained_without_fabricating_a_winner():
    page = app()
    page.number_input(key="initial_cash").set_value(0.0)
    page.button(key="run_scenario").click().run()
    assert not page.exception
    assert any("No policy meets" in w.value for w in page.warning)


@pytest.mark.parametrize("equity, minimum_cash, equity_gaps, eligible_count", [
    (500000.0, ["$147,450", "($696,143)", "($1,485,855)"],
     ["$0", "$746,143", "$1,535,855"], 1),
    (1250000.0, ["$897,450", "$53,857", "($735,855)"],
     ["$0", "$0", "$785,855"], 2),
])
def test_comparison_exposes_each_policy_cash_limit_and_equity_gap(equity, minimum_cash, equity_gaps, eligible_count):
    page = app()
    if equity != 500000.0:
        page.number_input(key="initial_cash").set_value(equity)
        page.button(key="run_scenario").click().run()
    assert not page.exception
    comparison = page.tabs[1]
    assert [metric.value for metric in comparison.metric] == ["$48,133", "$294,468", "$396,446"]
    captions = [caption.value for caption in comparison.caption]
    assert [value.split(" · ")[0] for value in captions if value.startswith("Minimum cash:")] == [
        f"Minimum cash: {amount}" for amount in minimum_cash
    ]
    assert [value for value in captions if value.startswith("Additional equity for cash floor:")] == [
        f"Additional equity for cash floor: {amount}." for amount in equity_gaps
    ]
    assert len(comparison.success) == eligible_count
    assert len(comparison.warning) == 3 - eligible_count
    assert all("Minimum-cash floor breached" in message.value for message in comparison.warning)


def test_bad_input_is_reported_and_last_successful_results_remain_visible():
    page = app()
    page.number_input(key="cash_floor").set_value(-1.0)
    page.button(key="run_scenario").click().run()
    assert not page.exception
    assert any("cannot be negative" in e.value for e in page.error)
    assert page.session_state["applied_assumptions"] == Assumptions()


@pytest.mark.parametrize("example, assumptions, policy, run_id, profit, recommendation", [
    ("base", Assumptions(), "conservative", "5a88f7bef3fa93d4", "$48,133", "conservative"),
    ("capital", replace(Assumptions(), initial_cash=1250000), "balanced",
     "690e9fa563e2d475", "$294,468", "balanced"),
    ("defaults", replace(Assumptions(), default_stress=2), "conservative",
     "a2d0056e84a3ceb8", "($11,563)", None),
])
def test_guided_example_replaces_custom_and_draft_inputs_and_clears_stress(
        example, assumptions, policy, run_id, profit, recommendation):
    page = app()
    page.slider(key="funding_percent").set_value(12.0)
    page.number_input(key="opex").set_value(10000.0)
    page.selectbox(key="policy").set_value("aggressive")
    page.radio(key="cohort_cutoff").set_value("Complete runoff")
    page.button(key="run_scenario").click().run()
    page.button(key="run_stress").click().run()
    assert "stress_points" in page.session_state
    page.number_input(key="cash_floor").set_value(-1.0)
    page.slider(key="growth_percent").set_value(5.0)
    page.button(key=f"example_{example}").click().run()
    assert not page.exception
    assert not page.error
    assert page.session_state["applied_assumptions"] == assumptions
    assert page.session_state["applied_policy"] == policy
    selected = next(r for r in page.session_state["results"] if r.policy == policy)
    assert selected.run_id == run_id
    assert page.metric[0].value == profit
    assert select_strategy(page.session_state["results"]).recommended_policy == recommendation
    assert all(r.checks.passed for r in page.session_state["results"])
    assert page.selectbox(key="policy").value == policy
    assert page.slider(key="funding_percent").value == 8.0
    assert page.slider(key="growth_percent").value == 0.0
    assert page.number_input(key="opex").value == 7500.0
    assert page.number_input(key="cash_floor").value == 50000.0
    assert page.radio(key="cohort_cutoff").value == "First 24 months"
    assert "stress_points" not in page.session_state


def test_custom_run_after_example_keeps_edits_and_other_visitors_independent():
    page, other = app(), app()
    page.button(key="example_capital").click().run()
    applied = page.session_state["results"][1].run_id
    page.slider(key="funding_percent").set_value(12.0)
    assert page.session_state["results"][1].run_id == applied
    page.button(key="run_scenario").click().run()
    assert not page.exception
    assert page.session_state["applied_assumptions"] == replace(
        Assumptions(), initial_cash=1250000, funding_rate=Decimal("0.12"))
    assert page.session_state["applied_policy"] == "balanced"
    assert page.session_state["results"][1].run_id != applied
    custom_run = page.session_state["results"][1].run_id
    page.radio(key="cohort_cutoff").set_value("Complete runoff").run()
    assert page.session_state["results"][1].run_id == custom_run
    assert other.session_state["applied_assumptions"] == Assumptions()
    assert other.session_state["applied_policy"] == "conservative"
    page.button(key="reset").click().run()
    assert page.session_state["applied_assumptions"] == Assumptions()
    assert page.session_state["results"][0].run_id == "5a88f7bef3fa93d4"


def test_stress_grid_matches_current_applied_policy_and_resets_with_scenario():
    page = app()
    page.button(key="run_stress").click().run()
    assert not page.exception
    grid = page.session_state["stress_points"]
    assert grid["run_id"] == page.session_state["results"][0].run_id
    assert len(grid["points"]) == 20
    assert any(float(p["operating_result"]) < 0 for p in grid["points"])
    page.button(key="reset").click().run()
    assert "stress_points" not in page.session_state


@pytest.fixture
def isolated_project(tmp_path):
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / "app.py", tmp_path / "app.py")
    shutil.copytree(root / "data", tmp_path / "data")
    st.cache_data.clear()
    yield tmp_path / "app.py"
    st.cache_data.clear()


def test_empty_portfolio_keeps_operating_costs_and_marks_loss_margin_undefined(isolated_project):
    path = isolated_project.parent / "data" / "applications.csv"
    original = load_dataset(path)
    empty = Dataset((), original.seed)
    save_dataset(empty, path)
    (path.parent / "manifest.json").write_text(json.dumps(empty.manifest()))
    page = AppTest.from_file(isolated_project, default_timeout=20).run()
    assert not page.exception
    assert page.header[0].value == "Recommended policy: None"
    assert page.metric[0].value == "($292,500)"
    assert page.metric[2].value == "n.a."
    assert any("No funded loans" in item.value for item in page.caption)


def test_missing_dataset_reports_startup_error_without_an_exception(isolated_project):
    (isolated_project.parent / "data" / "applications.csv").unlink()
    page = AppTest.from_file(isolated_project, default_timeout=20).run()
    assert not page.exception
    assert any("Base dataset could not be loaded" in e.value for e in page.error)
    assert not page.metric


@pytest.mark.parametrize("content", ["{}", "[]"])
def test_invalid_manifest_reports_startup_error_without_an_exception(isolated_project, content):
    (isolated_project.parent / "data" / "manifest.json").write_text(content)
    page = AppTest.from_file(isolated_project, default_timeout=20).run()
    assert not page.exception
    assert any("versioned manifest" in e.value for e in page.error)
    assert not page.metric


@pytest.mark.parametrize("field, value", [
    ("dataset_hash", "0" * 64),
    ("dataset_version", "wrong-version"),
])
def test_manifest_changes_are_revalidated_after_a_warm_run(isolated_project, field, value):
    page = AppTest.from_file(isolated_project, default_timeout=20).run()
    assert not page.exception
    path = isolated_project.parent / "data" / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest[field] = value
    path.write_text(json.dumps(manifest))
    page.run()
    assert not page.exception
    assert any("versioned manifest" in e.value for e in page.error)
    assert not page.metric


def test_valid_dataset_replacement_refreshes_results_with_applied_inputs(isolated_project):
    page = AppTest.from_file(isolated_project, default_timeout=20).run()
    page.selectbox(key="policy").set_value("balanced")
    page.number_input(key="initial_cash").set_value(1250000.0)
    page.button(key="run_scenario").click().run()
    old_run = page.session_state["results"][1].run_id
    path = isolated_project.parent / "data" / "applications.csv"
    original = load_dataset(path)
    rows = list(original.applications)
    rows[0] = replace(rows[0], principal_cents=rows[0].principal_cents + 10000)
    changed = Dataset(tuple(rows), original.seed)
    save_dataset(changed, path)
    (path.parent / "manifest.json").write_text(json.dumps(changed.manifest()))
    page.run()
    assert not page.exception
    assert page.session_state["applied_policy"] == "balanced"
    assert page.session_state["applied_assumptions"].initial_cash == 1250000
    assert all(r.dataset_hash == changed.dataset_hash for r in page.session_state["results"])
    assert page.session_state["results"][1].run_id != old_run
