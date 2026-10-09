"""Financial presentation and draft-state contracts, independent of Streamlit."""

from dataclasses import replace
from decimal import Decimal as D

import pytest


@pytest.mark.parametrize('missing', [float('nan'), D('NaN'), None])
def test_undefined_chart_values_use_unavailable_without_numeric_fabrication(missing):
    assert money(missing) == 'Unavailable'
    assert percent(missing) == 'Unavailable'
    assert points(missing) == 'Unavailable'

from lending_simulator.data import generate_dataset, Dataset
from lending_simulator.decisions import compare_policies, sensitivity
from lending_simulator.types import Assumptions
from lending_simulator.ui.state import controls_for, parse_controls, draft_changes, stage_case
from lending_simulator.ui.data import ScenarioSnapshot, compare_snapshots, profit_bridge, stress_frame
from lending_simulator.ui.formatting import money, percent, points


@pytest.fixture(scope="module")
def result_bundle():
    return compare_policies(generate_dataset(count=100), Assumptions())


def test_draft_round_trip_and_normalized_reversion_preserve_every_assumption():
    applied = replace(Assumptions(), recovery_lag=7, initial_cash=D('1250000'),
                      funding_rate=D('.125'), cash_floor=D(0))
    controls = controls_for(applied)
    assert parse_controls(controls) == applied
    assert draft_changes(controls, applied) == ()
    controls['funding_percent'] = 12.50
    assert draft_changes(controls, applied) == ()
    controls['funding_percent'] = 13
    changes = draft_changes(controls, applied)
    assert len(changes) == 1
    assert changes[0].field == 'funding_rate'
    assert changes[0].before == D('.125') and changes[0].after == D('.13')


def test_invalid_draft_remains_identifiable_without_changing_applied_inputs():
    applied = Assumptions()
    controls = controls_for(applied)
    controls['cash_floor'] = None
    assert draft_changes(controls, applied)[0].field == 'cash_floor'
    with pytest.raises(ValueError, match='Minimum month-end cash'):
        parse_controls(controls)
    assert applied.cash_floor == D(50000)


def test_staging_stress_uses_its_applied_basis_and_guards_existing_drafts():
    applied = replace(Assumptions(), acquisition_cost=D(70), recovery_lag=8)
    point = {'default_stress': '1.5', 'funding_rate': '.12'}
    staged = stage_case(applied, controls_for(applied), point)
    assert parse_controls(staged) == replace(applied, default_stress=D('1.5'), funding_rate=D('.12'))
    dirty = controls_for(applied) | {'initial_cash': 900000}
    with pytest.raises(ValueError, match='unapplied'):
        stage_case(applied, dirty, point)


@pytest.mark.parametrize('value, expected', [
    (D('-.001'), '(<$1)'), (D('.001'), '<$1'), (D(0), '$0'),
    (None, 'Unavailable'), (D('-1250'), '($1,250)'),
    (D('-0'), '$0'), (-0.0, '$0'),
])
def test_money_preserves_small_nonzero_signs_and_missing_values(value, expected):
    assert money(value) == expected


def test_rates_and_percentage_point_changes_have_distinct_units():
    assert percent(D('.051')) == '5.10%'
    assert points(D('-.001')) == '−<0.01 pp'
    assert points(D('.001')) == '<0.01 pp'
    assert points(None) == 'Unavailable'


def test_profit_bridge_reconciles_without_principal_or_double_counted_recoveries(result_bundle):
    result = result_bundle[1]
    bridge = profit_bridge(result)
    assert abs(sum(value for _, value in bridge[:-1]) - result.summary.operating_result) <= result.checks.tolerance
    assert bridge[-1] == ('Operating profit', result.summary.operating_result)
    assert sum(value for name, value in bridge if name == 'Net credit loss') == -result.summary.net_credit_loss
    assert not any('principal' in name.lower() or 'recoveries' in name.lower() for name, _ in bridge)


def test_empty_stress_grid_keeps_unavailable_loss_and_actual_costs():
    cases = sensitivity(Dataset((), 2262026), Assumptions(), 'conservative')
    frame = stress_frame(cases)
    assert len(frame) == 20
    assert frame.loss_ratio.isna().all()
    assert frame.operating_result.eq(-292500).all()
    assert frame.profitability.eq('Loss-making').all()
    assert not frame.eligible.any()
    assert frame.reasons.str.contains('No funded loans').all()


def test_stress_adapter_rejects_malformed_numbers_instead_of_inventing_zero():
    point = sensitivity(Dataset((), 2262026), Assumptions(), 'conservative')[0]
    with pytest.raises(ValueError, match='loss_ratio'):
        stress_frame((point | {'loss_ratio': 'broken'},))


def test_scenario_deltas_compare_same_policy_and_keep_horizons_explicit(result_bundle):
    baseline = ScenarioSnapshot.capture(result_bundle)
    dataset = generate_dataset(count=100)
    capital = compare_policies(dataset, replace(Assumptions(), initial_cash=D(1250000)))
    comparison = compare_snapshots(baseline, ScenarioSnapshot.capture(capital))
    assert comparison.compatible and comparison.same_horizon
    assert [row.policy for row in comparison.deltas] == ['conservative', 'balanced', 'aggressive']
    assert all(row.profit == 0 and row.loss_pp == 0 for row in comparison.deltas)
    assert all(abs(row.cash - D(750000)) < D('1e-16') for row in comparison.deltas)
    longer = compare_policies(dataset, replace(Assumptions(), recovery_lag=12))
    changed = compare_snapshots(baseline, ScenarioSnapshot.capture(longer))
    assert changed.compatible and not changed.same_horizon
    assert changed.baseline_months == 39 and changed.current_months == 48
    assert all(row.profit is None for row in changed.deltas)
    assert all(row.profit_24m is not None for row in changed.deltas)


def test_scenario_comparison_rejects_other_dataset_and_model_versions(result_bundle):
    baseline = ScenarioSnapshot.capture(result_bundle)
    other = compare_policies(generate_dataset(seed=3, count=100), Assumptions())
    assert not compare_snapshots(baseline, ScenarioSnapshot.capture(other)).compatible
    assert not compare_snapshots(baseline, replace(baseline, model_version='different')).compatible


def test_cash_timeline_retains_monthly_points_dates_and_exact_floor_reference(result_bundle):
    from lending_simulator.ui.charts import cash_chart
    result = result_bundle[1]
    fig = cash_chart(result)
    assert len(fig.data[0].x) == len(result.monthly) == 39
    assert str(fig.data[0].x[0]).startswith('2026-10-01')
    assert fig.data[0].y[result.summary.minimum_cash_month] == float(result.summary.minimum_cash)
    assert any(shape.y0 == shape.y1 == float(result.assumptions.cash_floor) for shape in fig.layout.shapes)


def test_applied_stress_case_requires_exact_decimal_identity():
    from lending_simulator.ui.data import applied_case_index
    points = ({'default_stress': '1', 'funding_rate': '.08'},)
    assert applied_case_index(points, Assumptions()) == 0
    # Both values collapse to the same float. This is not the same applied pair.
    nearly_equal = replace(Assumptions(), funding_rate=D('.0800000000000000001'))
    assert applied_case_index(points, nearly_equal) is None


def test_shared_cohort_scale_ignores_an_unfunded_policy_without_hiding_other_losses():
    from lending_simulator.presentation import cohort_heatmap
    from lending_simulator.ui.views import cohort_scale
    source = generate_dataset(count=100)
    dataset = Dataset(tuple(a for a in source.applications if a.risk_band != 'low'), source.seed)
    results = compare_policies(dataset, Assumptions())
    assert results[0].summary.funded_principal == 0
    expected = max(cohort_heatmap(result).max().max() for result in results[1:])
    assert expected > .001
    assert cohort_scale(tuple(result.run_id for result in results), results) == expected


def test_assumption_review_shows_units_and_small_committed_changes():
    from lending_simulator.ui.formatting import assumption_value
    assert assumption_value('funding_rate', D('.080001')) == '8.0001%'
    assert assumption_value('monthly_opex', D('7500.01')) == '$7,500.01'
    assert assumption_value('recovery_lag', 12) == '12 months'
    assert assumption_value('default_stress', D('1.50')) == '1.5×'
    assert assumption_value('cash_floor', None) == 'Enter a value'
