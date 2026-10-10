"""Exact comparison adapters and safe numeric data for the visual layer."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext

import pandas as pd

from lending_simulator import MODEL_VERSION
from lending_simulator.decisions import select_strategy
from lending_simulator.types import ModelResult

D = Decimal


@dataclass(frozen=True)
class ScenarioSnapshot:
    results: tuple[ModelResult, ...]
    model_version: str
    currency: str
    start_month: str
    origination_months: int

    @classmethod
    def capture(cls, results: tuple[ModelResult, ...]):
        select_strategy(results)  # Reject mixed or duplicated comparison inputs.
        manifest = results[0].manifest()
        return cls(results, MODEL_VERSION, manifest['currency'], manifest['start_month'],
                   manifest['operating_horizon_months'])


@dataclass(frozen=True)
class PolicyDelta:
    policy: str
    profit: Decimal | None
    profit_24m: Decimal
    cash: Decimal
    equity_gap: Decimal
    loss_pp: Decimal | None
    approval_pp: Decimal | None


@dataclass(frozen=True)
class ScenarioComparison:
    compatible: bool
    reason: str | None
    same_horizon: bool
    baseline_months: int
    current_months: int
    deltas: tuple[PolicyDelta, ...]


def compare_snapshots(baseline: ScenarioSnapshot, current: ScenarioSnapshot) -> ScenarioComparison:
    old, new = baseline.results[0], current.results[0]
    old_basis = (baseline.model_version, old.dataset_hash, baseline.currency, baseline.start_month,
                 baseline.origination_months, old.assumptions.term)
    new_basis = (current.model_version, new.dataset_hash, current.currency, current.start_month,
                 current.origination_months, new.assumptions.term)
    same_horizon = len(old.monthly) == len(new.monthly)
    incompatible = old_basis != new_basis or {r.policy for r in baseline.results} != {r.policy for r in current.results}
    if incompatible:
        return ScenarioComparison(False, 'Dataset, model, currency, or origination basis differs. Replace the baseline.',
                                  same_horizon, len(old.monthly), len(new.monthly), ())
    old_by_policy = {r.policy: r for r in baseline.results}
    deltas = []
    with localcontext() as ctx:
        ctx.prec = 34
        for result in current.results:
            before, after = old_by_policy[result.policy].summary, result.summary
            ratio_diff = lambda a, b: None if a is None or b is None else (b - a) * 100
            deltas.append(PolicyDelta(result.policy,
                after.operating_result - before.operating_result if same_horizon else None,
                after.operating_result_24m - before.operating_result_24m,
                after.minimum_cash - before.minimum_cash,
                after.additional_equity_required - before.additional_equity_required,
                ratio_diff(before.loss_ratio, after.loss_ratio),
                ratio_diff(before.approval_rate, after.approval_rate)))
    return ScenarioComparison(True, None, same_horizon, len(old.monthly), len(new.monthly), tuple(deltas))


def profit_bridge(result: ModelResult) -> tuple[tuple[str, Decimal], ...]:
    s = result.summary
    rows = (('Interest', s.interest_revenue), ('Merchant fees', s.merchant_fees),
            ('Funding', -s.funding_expense), ('Servicing', -s.servicing_expense),
            ('Acquisition', -s.acquisition_expense), ('Net credit loss', -s.net_credit_loss),
            ('Platform expense', -s.platform_opex))
    with localcontext() as ctx:
        ctx.prec = 34
        if abs(sum((value for _, value in rows), D(0)) - s.operating_result) > result.checks.tolerance:
            raise ValueError('Profit components do not reconcile to operating profit.')
    return rows + (('Operating profit', s.operating_result),)


def stress_frame(points: tuple[dict, ...]) -> pd.DataFrame:
    rows = []
    numeric = ('default_stress', 'funding_rate', 'operating_result', 'contribution',
               'minimum_cash', 'loss_ratio', 'additional_equity_required')
    for point in points:
        row = dict(point)
        profit = None
        for field in numeric:
            raw = row[field]
            if field == 'loss_ratio' and (raw is None or raw == 'None'):
                row[field] = None
                continue
            try:
                value = D(str(raw))
                if not value.is_finite():
                    raise ValueError
            except (InvalidOperation, TypeError, ValueError) as error:
                raise ValueError(f'Invalid stress value: {field}.') from error
            row[field] = float(value)
            if field == 'operating_result':
                profit = value
        row['profitability'] = 'Profitable' if profit > 0 else 'Loss-making' if profit < 0 else 'Breakeven'
        rows.append(row)
    return pd.DataFrame(rows)


def applied_case_index(points: tuple[dict, ...], assumptions) -> int | None:
    """Match the captured Decimal pair before any chart float conversion."""
    return next((index for index, point in enumerate(points)
        if D(point['default_stress']) == assumptions.default_stress
        and D(point['funding_rate']) == assumptions.funding_rate), None)
