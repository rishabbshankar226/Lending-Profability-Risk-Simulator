"""Small immutable interfaces shared by data, model, and presentation."""

from dataclasses import asdict, dataclass, fields
from decimal import Decimal
from hashlib import sha256
import json

from lending_simulator import MODEL_VERSION

D = Decimal
ZERO = D(0)
POLICIES = {
    "conservative": ("low",),
    "balanced": ("low", "medium"),
    "aggressive": ("low", "medium", "high"),
}
BANDS = ("low", "medium", "high")
ORIGINATION_MONTHS = 24


def decimal_text(value: Decimal) -> str:
    """Canonical exact decimal text: 1, 1.0, and 1.00 have one identity."""
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


@dataclass(frozen=True)
class Assumptions:
    term: int = 12
    recovery_lag: int = 3
    borrower_rate: Decimal = D(".18")
    merchant_fee: Decimal = D(".02")
    pd_low: Decimal = D(".02")
    pd_medium: Decimal = D(".06")
    pd_high: Decimal = D(".12")
    default_stress: Decimal = D(1)
    recovery_rate: Decimal = D(".25")
    funding_rate: Decimal = D(".08")
    advance_rate: Decimal = D(".80")
    initial_cash: Decimal = D(500000)
    facility_limit: Decimal = D(2000000)
    acquisition_cost: Decimal = D(25)
    servicing_cost: Decimal = D(1)
    monthly_opex: Decimal = D(7500)
    demand_growth: Decimal = D(0)
    loss_cap: Decimal = D(".05")
    cash_floor: Decimal = D(50000)

    def validate(self) -> None:
        if type(self.term) is not int or self.term != 12:
            raise ValueError("This release supports the approved 12-month product only.")
        if type(self.recovery_lag) is not int or not 0 <= self.recovery_lag <= 12:
            raise ValueError("Recovery lag must be an integer from 0 to 12 months.")
        for field in fields(self):
            if field.name in ("term", "recovery_lag"):
                continue
            value = getattr(self, field.name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ValueError(f"{field.name} must be a finite Decimal.")
            if field.name == "demand_growth":
                if not D(-1) < value <= D(1):
                    raise ValueError("Demand growth must be greater than -100% and at most 100% monthly.")
            elif value < 0:
                raise ValueError(f"{field.name} cannot be negative.")
        for name in ("borrower_rate", "merchant_fee", "pd_low", "pd_medium", "pd_high",
                     "recovery_rate", "funding_rate", "advance_rate", "loss_cap"):
            if getattr(self, name) > 1:
                raise ValueError(f"{name} must be between 0 and 1.")
        if self.default_stress > 10:
            raise ValueError("Default stress must be at most 10 times base PD.")

    def lifetime_pd(self, band: str) -> Decimal:
        # A stress above 100% is capped; the dashboard reports the effective PD.
        return min(D(1), getattr(self, f"pd_{band}") * self.default_stress)

    def to_dict(self) -> dict:
        return {k: decimal_text(v) if isinstance(v, Decimal) else v for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, values: dict) -> "Assumptions":
        allowed = {field.name for field in fields(cls)}
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"Unknown assumptions: {sorted(unknown)}")
        converted = {k: v if k in ("term", "recovery_lag") else D(str(v)) for k, v in values.items()}
        obj = cls(**converted)
        obj.validate()
        return obj


@dataclass(frozen=True)
class CohortInput:
    origination_month: int
    risk_band: str
    expected_count: Decimal
    principal: Decimal


@dataclass(frozen=True)
class CohortMonth:
    origination_month: int
    risk_band: str
    month: int
    age: int
    opening_principal: Decimal = ZERO
    originations: Decimal = ZERO
    principal_collections: Decimal = ZERO
    interest_revenue: Decimal = ZERO
    gross_chargeoffs: Decimal = ZERO
    recoveries: Decimal = ZERO
    ending_principal: Decimal = ZERO
    expected_active: Decimal = ZERO
    expected_defaults: Decimal = ZERO
    funded_loans: Decimal = ZERO
    merchant_fees: Decimal = ZERO
    acquisition_expense: Decimal = ZERO
    servicing_expense: Decimal = ZERO


@dataclass(frozen=True)
class MonthlyResult:
    month: int
    opening_principal: Decimal
    originations: Decimal
    principal_collections: Decimal
    interest_revenue: Decimal
    gross_chargeoffs: Decimal
    recoveries: Decimal
    ending_principal: Decimal
    expected_active: Decimal
    expected_defaults: Decimal
    funded_loans: Decimal
    merchant_fees: Decimal
    acquisition_expense: Decimal
    servicing_expense: Decimal
    opening_debt: Decimal
    ending_debt: Decimal
    net_debt_draw: Decimal
    funding_expense: Decimal
    platform_opex: Decimal
    net_credit_loss: Decimal
    contribution: Decimal
    operating_result: Decimal
    opening_cash: Decimal
    ending_cash: Decimal


@dataclass(frozen=True)
class Summary:
    expected_applications: Decimal
    funded_loans: Decimal
    approval_rate: Decimal | None
    funded_principal: Decimal
    interest_revenue: Decimal
    merchant_fees: Decimal
    gross_chargeoffs: Decimal
    recoveries: Decimal
    net_credit_loss: Decimal
    loss_ratio: Decimal | None
    funding_expense: Decimal
    servicing_expense: Decimal
    acquisition_expense: Decimal
    platform_opex: Decimal
    contribution: Decimal
    unit_contribution: Decimal | None
    operating_result: Decimal
    operating_result_24m: Decimal
    minimum_cash: Decimal
    minimum_cash_month: int
    additional_equity_required: Decimal
    peak_debt: Decimal
    minimum_facility_headroom: Decimal


@dataclass(frozen=True)
class Checks:
    passed: bool
    tolerance: Decimal
    maximum_residual: Decimal
    loan_residual: Decimal
    debt_residual: Decimal
    cash_residual: Decimal
    equity_residual: Decimal
    cohort_residual: Decimal
    runoff_residual: Decimal
    exposure_limits_ok: bool


@dataclass(frozen=True)
class ModelResult:
    policy: str
    assumptions: Assumptions
    dataset_hash: str
    monthly: tuple[MonthlyResult, ...]
    cohorts: tuple[CohortMonth, ...]
    summary: Summary
    checks: Checks
    run_id: str

    def manifest(self) -> dict:
        return {
            "run_id": self.run_id, "model_version": MODEL_VERSION,
            "dataset_hash": self.dataset_hash, "policy": self.policy,
            "assumptions": self.assumptions.to_dict(),
            "expected_applications": str(self.summary.expected_applications),
            "currency": "USD", "start_month": "2026-10", "month_index_base": 0,
            "operating_horizon_months": ORIGINATION_MONTHS,
            "full_runoff_months": len(self.monthly), "data_classification": "synthetic projection",
            "historical_evidence_level": "contextual comparison only; uncalibrated",
            "checks": {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(self.checks).items()},
        }


def stable_hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
