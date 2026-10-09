from dataclasses import replace
from decimal import Decimal as D

import pytest

from lending_simulator.model import run_model
from lending_simulator.types import Assumptions, CohortInput


def no_costs(**overrides):
    values = dict(
        borrower_rate=D(0), merchant_fee=D(0), funding_rate=D(0),
        advance_rate=D(0), acquisition_cost=D(0), servicing_cost=D(0),
        monthly_opex=D(0), pd_low=D(0), pd_medium=D(0), pd_high=D(0),
        initial_cash=D(2000), cash_floor=D(0),
    )
    values.update(overrides)
    return Assumptions(**values)


def loan(principal="1200", month=0, band="low", count="1"):
    return CohortInput(month, band, D(count), D(principal))


def test_zero_interest_loan_has_twelve_100_dollar_principal_payments():
    result = run_model((loan(),), no_costs(), "aggressive", D(1), "fixture")
    payments = [row.principal_collections for row in result.monthly if row.principal_collections]
    assert payments == [D(100)] * 12
    assert sum(row.interest_revenue for row in result.monthly) == 0
    assert result.monthly[0].ending_cash == D(800)
    assert result.monthly[12].ending_principal == 0
    assert result.monthly[-1].ending_cash == D(2000)
    assert result.checks.passed


def test_complete_default_removes_900_and_recovers_225_after_three_months():
    result = run_model((loan("900"),), no_costs(pd_low=D(1)), "aggressive", D(1), "fixture")
    assert result.monthly[1].gross_chargeoffs == D(900)
    assert result.monthly[1].ending_principal == 0
    assert result.monthly[1].principal_collections == 0
    assert result.monthly[1].interest_revenue == 0
    assert result.monthly[3].recoveries == 0
    assert result.monthly[4].recoveries == D(225)
    assert result.summary.net_credit_loss == D(675)
    # The charge-off is not another cash payment.
    assert result.monthly[1].ending_cash == D(1100)
    assert result.monthly[-1].ending_cash == D(1325)
    assert result.summary.operating_result == D(-675)
    assert result.checks.passed


def test_funding_interest_uses_opening_debt_and_new_draw_has_no_same_month_interest():
    a = no_costs(advance_rate=D(1), funding_rate=D(".12"))
    result = run_model((loan("1000"),), a, "aggressive", D(1), "fixture")
    assert result.monthly[0].ending_debt == D(1000)
    assert result.monthly[0].funding_expense == 0
    assert result.monthly[1].funding_expense == D(10)
    assert result.monthly[1].net_debt_draw < 0


def test_higher_funding_rate_changes_profit_by_exact_opening_balance_interest():
    a = no_costs(advance_rate=D(".8"), funding_rate=D(".08"))
    low = run_model((loan(),), a, "aggressive", D(1), "fixture")
    high = run_model((loan(),), replace(a, funding_rate=D(".20")), "aggressive", D(1), "fixture")
    expected_difference = sum(r.opening_debt for r in low.monthly) * D(".12") / 12
    assert abs(low.summary.operating_result - high.summary.operating_result - expected_difference) < D("1e-20")


@pytest.mark.parametrize("recovery,net_loss", [("0", "900"), ("1", "0")])
def test_no_and_full_recovery_endpoints(recovery, net_loss):
    a = no_costs(pd_low=D(1), recovery_rate=D(recovery))
    result = run_model((loan("900"),), a, "aggressive", D(1), "fixture")
    assert result.summary.net_credit_loss == D(net_loss)
    assert result.checks.passed


def test_lifetime_pd_is_applied_to_survivors_and_outstanding_exposure():
    result = run_model((loan(),), no_costs(pd_low=D(".12")), "aggressive", D(1), "fixture")
    assert abs(sum(r.expected_defaults for r in result.cohorts) - D(".12")) < D("1e-20")
    assert D(0) < result.summary.gross_chargeoffs < D(144)
    assert abs(result.summary.net_credit_loss - result.summary.gross_chargeoffs * D(".75")) < D("1e-20")
    assert result.checks.passed


def test_full_runoff_includes_late_loans_recoveries_and_equal_horizon_overhead():
    a = no_costs(pd_low=D(".12"), monthly_opex=D(10))
    result = run_model((loan(month=23),), a, "aggressive", D(1), "fixture")
    assert len(result.monthly) == 39
    assert result.monthly[38].recoveries > 0
    assert result.summary.platform_opex == D(390)
    assert result.summary.operating_result_24m != result.summary.operating_result
    assert result.monthly[-1].ending_principal == 0
    assert result.monthly[-1].ending_debt == 0
    assert result.checks.passed


def test_empty_policy_has_no_fees_or_variable_costs_and_ratios_are_unavailable():
    result = run_model((), Assumptions(), "conservative", D(0), "fixture")
    assert result.summary.funded_loans == 0
    assert result.summary.approval_rate is None
    assert result.summary.loss_ratio is None
    assert result.summary.unit_contribution is None
    assert result.summary.merchant_fees == 0
    assert result.summary.acquisition_expense == 0
    assert result.summary.servicing_expense == 0
    assert result.summary.platform_opex == D(7500) * 39
    assert result.checks.passed


def test_facility_cap_and_default_collateral_repayment_do_not_create_equity():
    a = no_costs(advance_rate=D(".8"), facility_limit=D(500), pd_low=D(1))
    result = run_model((loan("900"),), a, "aggressive", D(1), "fixture")
    assert result.monthly[0].ending_debt == D(500)
    assert result.monthly[1].net_debt_draw == D(-500)
    assert result.monthly[1].ending_cash == D(1100)
    assert result.checks.passed


def test_positive_interest_loan_matches_independent_payment_and_has_no_residual():
    result = run_model((loan(),), no_costs(borrower_rate=D(".12")), "aggressive", D(1), "fixture")
    # Independently calculated 12-month payment at 1% monthly.
    first = result.monthly[1]
    assert abs(first.interest_revenue + first.principal_collections - D("106.61854641401008")) < D("1e-12")
    assert first.interest_revenue == D(12)
    assert result.monthly[12].ending_principal == 0
    assert result.checks.passed


@pytest.mark.parametrize("changes", [
    {"pd_low": D("1.01")}, {"initial_cash": D(-1)},
    {"recovery_lag": -1}, {"funding_rate": D("NaN")},
    {"term": 36}, {"demand_growth": D(-1)},
])
def test_invalid_assumptions_are_rejected_before_modeling(changes):
    with pytest.raises(ValueError):
        run_model((loan(),), replace(Assumptions(), **changes), "aggressive", D(1), "fixture")


def test_duplicate_cohort_and_nonpositive_funded_principal_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        run_model((loan(), loan()), no_costs(), "aggressive", D(2), "fixture")
    with pytest.raises(ValueError):
        run_model((loan("-1"),), no_costs(), "aggressive", D(1), "fixture")
