"""Pure draft transformations. Applying results remains an explicit transaction."""

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Mapping

from lending_simulator.types import Assumptions

D = Decimal
# Model field, widget key, user-facing label, unit scale.
FIELDS = (
    ('demand_growth', 'growth_percent', 'Monthly application growth', 100),
    ('default_stress', 'stress', 'Lifetime default stress', 1),
    ('funding_rate', 'funding_percent', 'Annual funding rate', 100),
    ('initial_cash', 'initial_cash', 'Starting equity cash', 1),
    ('loss_cap', 'loss_cap_percent', 'Net principal loss cap', 100),
    ('cash_floor', 'cash_floor', 'Minimum month-end cash', 1),
    ('borrower_rate', 'borrower_percent', 'Annual borrower rate', 100),
    ('merchant_fee', 'merchant_percent', 'Merchant fee', 100),
    ('pd_low', 'low_percent', 'Low-band lifetime PD', 100),
    ('pd_medium', 'medium_percent', 'Medium-band lifetime PD', 100),
    ('pd_high', 'high_percent', 'High-band lifetime PD', 100),
    ('recovery_rate', 'recovery_percent', 'Recovery of charged-off principal', 100),
    ('recovery_lag', 'lag', 'Recovery lag', 1),
    ('advance_rate', 'advance_percent', 'Collateral advance rate', 100),
    ('facility_limit', 'facility', 'Facility limit', 1),
    ('acquisition_cost', 'acquisition', 'Acquisition cost per funded loan', 1),
    ('servicing_cost', 'servicing', 'Monthly servicing cost per surviving loan', 1),
    ('monthly_opex', 'opex', 'Monthly platform expense', 1),
)


@dataclass(frozen=True)
class DraftChange:
    field: str
    label: str
    before: Decimal | int
    after: Decimal | int | None


def controls_for(assumptions: Assumptions) -> dict:
    return {key: int(getattr(assumptions, field)) if field == 'recovery_lag'
            else float(getattr(assumptions, field) * scale)
            for field, key, _, scale in FIELDS}


def _value(raw, field: str, scale: int):
    if raw is None:
        return None
    try:
        value = D(str(raw)) / scale
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not value.is_finite():
        return None
    return int(value) if field == 'recovery_lag' and value == int(value) else value


def parse_controls(controls: Mapping) -> Assumptions:
    values = {}
    for field, key, label, scale in FIELDS:
        value = _value(controls.get(key), field, scale)
        if value is None:
            raise ValueError(f'{label}: enter a finite number.')
        values[field] = value
    assumptions = Assumptions(**values)
    try:
        assumptions.validate()
    except ValueError as error:
        message = str(error)
        for field, _, label, _ in sorted(FIELDS, key=lambda item: len(item[0]), reverse=True):
            message = message.replace(field, label)
        raise ValueError(message) from error
    return assumptions


def draft_changes(controls: Mapping, applied: Assumptions) -> tuple[DraftChange, ...]:
    changes = []
    for field, key, label, scale in FIELDS:
        before = getattr(applied, field)
        after = _value(controls.get(key), field, scale)
        if before != after:
            changes.append(DraftChange(field, label, before, after))
    return tuple(changes)


def stage_case(applied: Assumptions, controls: Mapping, point: Mapping) -> dict:
    if draft_changes(controls, applied):
        raise ValueError('Apply or restore unapplied changes before staging a stress case.')
    staged = replace(applied, default_stress=D(point['default_stress']), funding_rate=D(point['funding_rate']))
    staged.validate()
    return controls_for(staged)
