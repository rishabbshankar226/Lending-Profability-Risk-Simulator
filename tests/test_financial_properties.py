"""Seeded cross-scenario checks independent of policy/example snapshots."""

from dataclasses import replace
from decimal import Decimal as D, localcontext
from random import Random

from lending_simulator.data import generate_dataset
from lending_simulator.decisions import compare_policies
from lending_simulator.types import Assumptions


def test_seeded_boundary_scenarios_preserve_lifetime_financial_identities():
    rng = Random(2262026)
    with localcontext() as context:
        context.prec = 80
        for case in range(160):
            dataset = generate_dataset(seed=case, count=rng.choice([0, 1, 3, 24, 80]))
            assumptions = replace(
                Assumptions(), recovery_lag=rng.choice([0, 1, 3, 12]),
                borrower_rate=D(rng.choice(["0", ".000001", ".18", "1"])),
                merchant_fee=D(rng.choice(["0", ".02", "1"])),
                pd_low=D(rng.choice(["0", ".02", ".5", "1"])),
                pd_medium=D(rng.choice(["0", ".06", ".5", "1"])),
                pd_high=D(rng.choice(["0", ".12", ".5", "1"])),
                default_stress=D(rng.choice(["0", ".5", "1", "3", "10"])),
                recovery_rate=D(rng.choice(["0", ".25", "1"])),
                funding_rate=D(rng.choice(["0", ".08", "1"])),
                advance_rate=D(rng.choice(["0", ".8", "1"])),
                demand_growth=D(rng.choice(["-.99", "-.1", "0", ".1", "1"])),
                initial_cash=D(rng.choice([0, 500000, 1000000000])),
                facility_limit=D(rng.choice([0, 100, 2000000])),
            )
            for result in compare_policies(dataset, assumptions):
                evidence = (case, result.policy, assumptions.to_dict())
                summary = result.summary
                assert result.checks.passed, evidence
                lifetime_principal = sum(
                    (row.principal_collections + row.gross_chargeoffs for row in result.monthly), D(0))
                assert abs(lifetime_principal - summary.funded_principal) < D("1e-16"), evidence
                assert abs(result.monthly[-1].ending_cash - assumptions.initial_cash
                           - summary.operating_result) < D("1e-16"), evidence
                monthly_credit_expense = sum((row.net_credit_loss for row in result.monthly), D(0))
                assert abs(monthly_credit_expense - summary.net_credit_loss) < D("1e-16"), evidence
                if summary.loss_ratio is not None:
                    assert D(0) <= summary.loss_ratio <= D(1), evidence
                    if assumptions.recovery_rate == 1:
                        assert summary.loss_ratio == 0, evidence
                if summary.approval_rate is not None:
                    assert D(0) <= summary.approval_rate <= D(1), evidence
