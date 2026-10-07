from streamlit.testing.v1 import AppTest
from pathlib import Path
from dataclasses import replace
import json
import shutil

import pytest
import streamlit as st

from lending_simulator.types import Assumptions
from lending_simulator.data import Dataset, load_dataset, save_dataset


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
    for amount in minimum_cash:
        assert any(f"Minimum cash: {amount}" in value for value in captions)
    for amount in equity_gaps:
        assert any(value == f"Additional equity for cash floor: {amount}." for value in captions)
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
