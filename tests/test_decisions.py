from dataclasses import replace
from decimal import Decimal as D

from lending_simulator.decisions import compare_policies, evaluate_policy, select_strategy
from lending_simulator.data import generate_dataset
from lending_simulator.types import Assumptions, CohortInput
from lending_simulator.model import run_model


def example(policy="aggressive"):
    a = Assumptions(pd_low=D(0), pd_medium=D(0), pd_high=D(0), monthly_opex=D(0))
    return run_model((CohortInput(0, "low", D(1), D(1200)),), a, policy, D(1), "fixture")


def with_outcomes(result, profit, loss=".01", cash="100000"):
    return replace(result, summary=replace(result.summary, operating_result=D(profit), loss_ratio=D(loss), minimum_cash=D(cash)))


def test_highest_profit_policy_cannot_win_when_loss_or_cash_constraint_fails():
    strict = with_outcomes(example("conservative"), "10")
    broad = with_outcomes(example(), "100", loss=".06")
    decision = select_strategy((strict, broad))
    assert decision.recommended_policy == "conservative"
    assert "Credit-loss limit exceeded" in evaluate_policy(broad).reasons
    illiquid = with_outcomes(example(), "100", cash="49999.99")
    assert select_strategy((strict, illiquid)).recommended_policy == "conservative"


def test_eligibility_uses_unrounded_values_and_includes_exact_boundary():
    boundary = with_outcomes(example(), "100", loss=".05", cash="50000")
    assert evaluate_policy(boundary).eligible
    assert not evaluate_policy(with_outcomes(example(), "100", loss=".0500000000000000000000001")).eligible
    assert not evaluate_policy(with_outcomes(example(), "100", cash="49999.99999999999999999999")).eligible


def test_no_eligible_policy_returns_failures_without_a_winner():
    bad = with_outcomes(example(), "100", cash="-1")
    decision = select_strategy((bad,))
    assert decision.recommended_policy is None
    assert decision.status == "no_eligible_policy"


def test_all_losses_are_diagnostic_and_breakeven_is_not_profitable():
    strict = with_outcomes(example("conservative"), "-10")
    broad = with_outcomes(example(), "-1")
    decision = select_strategy((strict, broad))
    assert decision.recommended_policy is None
    assert decision.diagnostic_policy == "aggressive"
    assert decision.status == "no_profitable_policy"
    zero = select_strategy((with_outcomes(example(), "0"),))
    assert zero.recommended_policy is None
    assert zero.status == "breakeven"


def test_ties_resolve_by_loss_then_cash_then_stable_policy_order():
    strict = with_outcomes(example("conservative"), "10", loss=".02")
    balanced = with_outcomes(example("balanced"), "10", loss=".01")
    broad = with_outcomes(example(), "10", loss=".01", cash="100001")
    assert select_strategy((strict, balanced, broad)).recommended_policy == "aggressive"
    equal = with_outcomes(example(), "10", loss=".01")
    assert select_strategy((equal, balanced)).recommended_policy == "balanced"


def test_reconciliation_failure_and_empty_funding_are_ineligible():
    result = example()
    broken = replace(result, checks=replace(result.checks, passed=False))
    assert not evaluate_policy(broken).eligible
    empty = run_model((), result.assumptions, "aggressive", D(1), "fixture")
    assert "No funded loans" in evaluate_policy(empty).reasons


def test_comparison_uses_same_population_inputs_and_repeatable_run_ids():
    dataset = generate_dataset(count=1000)
    first = compare_policies(dataset, Assumptions())
    second = compare_policies(dataset, Assumptions())
    assert first == second
    assert len({r.dataset_hash for r in first}) == 1
    assert len({r.summary.expected_applications for r in first}) == 1
    assert len({len(r.monthly) for r in first}) == 1
    assert all(r.checks.passed for r in first)
    assert first[0].summary.funded_loans < first[1].summary.funded_loans < first[2].summary.funded_loans
    changed = compare_policies(dataset, replace(Assumptions(), funding_rate=D(".12")))
    assert first[1].run_id != changed[1].run_id
