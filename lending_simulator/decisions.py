"""Policy eligibility, honest recommendations, and scenario comparison."""

from dataclasses import dataclass, replace
from decimal import Decimal, localcontext

from lending_simulator.analytics import aggregate_for_model
from lending_simulator.data import Dataset
from lending_simulator.model import run_model
from lending_simulator.types import Assumptions, ModelResult, POLICIES


@dataclass(frozen=True)
class Eligibility:
    policy: str
    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Decision:
    status: str
    message: str
    recommended_policy: str | None
    diagnostic_policy: str | None
    eligibility: tuple[Eligibility, ...]


def compare_policies(dataset: Dataset, assumptions: Assumptions) -> tuple[ModelResult, ...]:
    assumptions.validate()
    results = []
    for policy in POLICIES:
        cohorts, denominator = aggregate_for_model(dataset, policy, assumptions.demand_growth)
        results.append(run_model(cohorts, assumptions, policy, denominator, dataset.dataset_hash))
    return tuple(results)


def evaluate_policy(result: ModelResult) -> Eligibility:
    s, a = result.summary, result.assumptions
    reasons = []
    if not result.checks.passed:
        reasons.append("Financial reconciliation failed")
    if s.funded_loans == 0 or s.loss_ratio is None:
        reasons.append("No funded loans")
    elif s.loss_ratio > a.loss_cap:
        reasons.append("Credit-loss limit exceeded")
    if s.minimum_cash < a.cash_floor:
        reasons.append("Minimum-cash floor breached")
    return Eligibility(result.policy, not reasons, tuple(reasons))


def select_strategy(results: tuple[ModelResult, ...]) -> Decision:
    if not results:
        raise ValueError("At least one policy result is required.")
    if len({r.policy for r in results}) != len(results):
        raise ValueError("A policy cannot occur twice.")
    basis = {(r.dataset_hash, tuple(r.assumptions.to_dict().items()), len(r.monthly), r.summary.expected_applications) for r in results}
    if len(basis) != 1:
        raise ValueError("Policy comparison requires the same population, assumptions, and horizon.")
    evaluations = tuple(evaluate_policy(r) for r in results)
    eligible_policies = {e.policy for e in evaluations if e.eligible}
    eligible = [r for r in results if r.policy in eligible_policies]
    if not eligible:
        return Decision("no_eligible_policy", "No policy meets the selected credit-loss and cash limits. Review the failure reasons and additional equity requirement.", None, None, evaluations)
    with localcontext() as ctx:
        ctx.prec = 34
        ordered = sorted(eligible, key=lambda r: (-r.summary.operating_result, r.summary.loss_ratio,
                                                 -r.summary.minimum_cash, list(POLICIES).index(r.policy)))
    best = ordered[0]
    if best.summary.operating_result < 0:
        return Decision("no_profitable_policy", f"No eligible strategy is profitable. {best.policy.title()} is the least loss-making eligible policy, shown only as a diagnostic.", None, best.policy, evaluations)
    if best.summary.operating_result == 0:
        return Decision("breakeven", f"{best.policy.title()} breaks even; no eligible strategy creates positive operating profit.", None, best.policy, evaluations)
    return Decision("profitable_policy", f"{best.policy.title()} has the highest expected full-runoff operating profit among policies meeting both limits.", best.policy, None, evaluations)


def sensitivity(dataset: Dataset, assumptions: Assumptions, policy: str,
                stresses=(Decimal(".5"), Decimal(1), Decimal("1.5"), Decimal(2), Decimal(3)),
                funding_rates=(Decimal(".04"), Decimal(".08"), Decimal(".12"), Decimal(".16"))) -> tuple[dict, ...]:
    cohorts, denominator = aggregate_for_model(dataset, policy, assumptions.demand_growth)
    points = []
    for stress in stresses:
        for funding_rate in funding_rates:
            inputs = replace(assumptions, default_stress=stress, funding_rate=funding_rate)
            result = run_model(cohorts, inputs, policy, denominator, dataset.dataset_hash)
            eligibility = evaluate_policy(result)
            points.append({
                "default_stress": str(stress), "funding_rate": str(funding_rate),
                "operating_result": str(result.summary.operating_result),
                "contribution": str(result.summary.contribution),
                "minimum_cash": str(result.summary.minimum_cash),
                "loss_ratio": str(result.summary.loss_ratio),
                "additional_equity_required": str(result.summary.additional_equity_required),
                "eligible": eligibility.eligible, "reasons": "; ".join(eligibility.reasons),
                "run_id": result.run_id,
            })
    return tuple(points)
