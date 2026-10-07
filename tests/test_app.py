from streamlit.testing.v1 import AppTest
from pathlib import Path

from lending_simulator.types import Assumptions


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


def test_bad_input_is_reported_and_last_successful_results_remain_visible():
    page = app()
    page.number_input(key="cash_floor").set_value(-1.0)
    page.button(key="run_scenario").click().run()
    assert not page.exception
    assert any("cannot be negative" in e.value for e in page.error)
    assert page.session_state["applied_assumptions"] == Assumptions()


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
