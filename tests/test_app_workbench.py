"""Public workbench behavior: applied results, drafts, and requested analysis."""

from decimal import Decimal as D
from pathlib import Path

from streamlit.testing.v1 import AppTest
import streamlit as st

from lending_simulator import decisions
from lending_simulator.ui import downloads


def page():
    return AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=20).run()


def navigate(app, view):
    app.button_group(key='analysis_view').set_value(view).run()
    assert not app.exception
    return app


def test_policy_viewing_is_immediate_and_does_not_apply_a_draft():
    app = page()
    original = tuple(result.run_id for result in app.session_state['results'])
    app.slider(key='funding_percent').set_value(12).run()
    app.selectbox(key='policy').set_value('balanced').run()
    assert not app.exception
    assert app.session_state['applied_policy'] == 'balanced'
    assert app.session_state['applied_assumptions'].funding_rate == D('.08')
    assert tuple(result.run_id for result in app.session_state['results']) == original
    assert app.metric[0].value == '$294,468'
    assert any('Unapplied' in item.value for item in app.info)


def test_restore_draft_preserves_view_and_result_then_reversion_is_clean():
    app = page()
    app.selectbox(key='policy').set_value('balanced').run()
    navigate(app, 'Policies')
    identity = app.session_state['results'][1].run_id
    app.slider(key='stress').set_value(2).run()
    app.button(key='restore_applied').click().run()
    assert not app.exception
    assert app.slider(key='stress').value == 1
    assert app.session_state['active_view'] == 'Policies'
    assert app.session_state['applied_policy'] == 'balanced'
    assert app.session_state['results'][1].run_id == identity
    assert not any('Unapplied' in item.value for item in app.info)


def test_lazy_views_keep_cohort_cutoff_and_draft_values():
    app = navigate(page(), 'Cohorts')
    app.radio(key='cohort_cutoff').set_value('Complete runoff').run()
    app.number_input(key='opex').set_value(10000).run()
    identity = app.session_state['results'][0].run_id
    navigate(app, 'Overview')
    assert not app.radio
    navigate(app, 'Cohorts')
    assert app.radio(key='cohort_cutoff').value == 'Complete runoff'
    assert app.number_input(key='opex').value == 10000
    assert app.session_state['results'][0].run_id == identity


def test_pinned_applied_baseline_survives_examples_and_reset_clears_it():
    app = navigate(page(), 'Policies')
    app.slider(key='stress').set_value(2).run()
    app.button(key='pin_baseline').click().run()
    assert app.session_state['baseline'].results[0].assumptions.default_stress == 1
    app.button(key='example_capital').click().run()
    assert not app.exception
    assert app.session_state['active_view'] == 'Policies'
    assert app.session_state['baseline'].results[0].run_id == '5a88f7bef3fa93d4'
    assert app.session_state['applied_policy'] == 'balanced'
    app.button(key='reset').click().run()
    assert app.session_state['active_view'] == 'Overview'
    assert 'baseline' not in app.session_state


def test_stress_case_stages_without_changing_results_or_recommendation():
    app = navigate(page(), 'Funding & stress')
    app.button(key='run_stress').click().run()
    identity = app.session_state['results'][0].run_id
    app.selectbox(key='stress_case').set_value(2).run()
    selected = app.session_state['stress_points']['points'][2]
    app.button(key='stage_stress').click().run()
    assert not app.exception
    assert app.session_state['results'][0].run_id == identity
    assert app.session_state['applied_assumptions'].funding_rate == D('.08')
    assert D(str(app.slider(key='funding_percent').value))/100 == D(selected['funding_rate'])
    app.button(key='run_scenario').click().run()
    assert app.session_state['applied_assumptions'].funding_rate == D(selected['funding_rate'])
    assert app.session_state['active_view'] == 'Funding & stress'
    assert 'stress_points' not in app.session_state


def test_successful_apply_clears_dirty_notice_in_the_same_response():
    app = page()
    app.slider(key='funding_percent').set_value(12).run()
    assert any('Unapplied' in item.value for item in app.info)
    app.button(key='run_scenario').click().run()
    assert not app.exception
    assert app.session_state['applied_assumptions'].funding_rate == D('.12')
    assert not any('Unapplied' in item.value for item in app.info)
    assert not any(button.key == 'restore_applied' for button in app.button)


def test_drafts_navigation_and_restore_do_not_run_financial_projections(monkeypatch):
    st.cache_data.clear()
    original = decisions.compare_policies
    calls = []
    def counted(*args, **kwargs):
        calls.append(args[1])
        return original(*args, **kwargs)
    monkeypatch.setattr(decisions, 'compare_policies', counted)
    app = page()
    assert len(calls) == 1
    identity = tuple(result.run_id for result in app.session_state['results'])
    app.slider(key='stress').set_value(2).run()
    for view in ('Policies', 'Cohorts', 'Funding & stress', 'Methodology', 'Overview'):
        navigate(app, view)
    app.selectbox(key='policy').set_value('balanced').run()
    app.button(key='restore_applied').click().run()
    assert len(calls) == 1
    assert tuple(result.run_id for result in app.session_state['results']) == identity
    app.slider(key='stress').set_value(2).run()
    app.button(key='run_scenario').click().run()
    assert not app.exception
    assert len(calls) == 2
    st.cache_data.clear()


def test_initial_render_and_brief_preview_only_prepare_the_requested_format(monkeypatch):
    downloads.cached_export.clear()
    original = downloads.decision_brief
    calls = []
    def brief(*args, **kwargs):
        calls.append('brief')
        return original(*args, **kwargs)
    def unrequested(*args, **kwargs):
        raise AssertionError('An unrequested CSV or workbook was generated')
    monkeypatch.setattr(downloads, 'decision_brief', brief)
    monkeypatch.setattr(downloads, 'scenario_workbook', unrequested)
    monkeypatch.setattr(downloads, 'csv_package', unrequested)
    app = page()
    assert not app.exception and calls == []
    app.session_state['exports_panel'] = True
    app.run()
    assert not app.exception and calls == []
    app.session_state['brief_preview'] = True
    app.run()
    assert not app.exception and calls == ['brief']
    app.slider(key='stress').set_value(2).run()
    assert calls == ['brief']
    assert app.session_state['applied_assumptions'].default_stress == 1
    downloads.cached_export.clear()
