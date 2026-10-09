"""Human-readable units without changing exact financial classifications."""

from decimal import Decimal, localcontext
from math import isnan

from lending_simulator.ui.state import FIELDS


def _missing(value) -> bool:
    return value is None or (value.is_nan() if isinstance(value, Decimal) else isnan(value))


def money(value: Decimal | float | None) -> str:
    if _missing(value):
        return 'Unavailable'
    if value == 0:
        return '$0'
    if 0 < abs(value) < 1:
        return '(<$1)' if value < 0 else '<$1'
    return f'(${abs(value):,.0f})' if value < 0 else f'${value:,.0f}'


def percent(value: Decimal | float | None) -> str:
    return 'Unavailable' if _missing(value) else f'{0 if value == 0 else value:.2%}'


def points(value: Decimal | None) -> str:
    if _missing(value):
        return 'Unavailable'
    amount = '<0.01' if 0 < abs(value) < Decimal('.01') else f'{abs(value):.2f}'
    return f'{"−" if value < 0 else ""}{amount} pp'


def multiple(value: Decimal) -> str:
    return f'{value.normalize():f}×'


def assumption_value(field: str, value) -> str:
    """Review committed inputs with their units and original decimal precision."""
    if _missing(value):
        return 'Enter a value'
    if field == 'default_stress':
        return multiple(value)
    if field == 'recovery_lag':
        return f'{value} months'
    with localcontext() as ctx:
        ctx.prec = 34
        if next(scale for name, _, _, scale in FIELDS if name == field) == 100:
            return f'{(value * 100).normalize():f}%'
        amount = f'{abs(value).normalize():,f}'
        return f'(${amount})' if value < 0 else f'${amount}'
