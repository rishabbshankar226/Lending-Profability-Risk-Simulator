"""Pure deterministic financial engine. No SQL, UI, network, or shared state."""

from dataclasses import asdict
from decimal import Decimal, localcontext

from lending_simulator import MODEL_VERSION
from lending_simulator.types import (
    BANDS, ORIGINATION_MONTHS, POLICIES, Assumptions, Checks, CohortInput,
    CohortMonth, ModelResult, MonthlyResult, Summary, stable_hash, decimal_text,
)

D = Decimal
ZERO = D(0)
TOLERANCE = D("1e-16")  # Dollars; far tighter than the one-cent reporting requirement.


def contractual_payment(principal: Decimal, annual_rate: Decimal, term: int) -> Decimal:
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return principal / term
    # Present value of equal payments avoids subtracting nearly equal numbers
    # when the nominal rate is close to zero.
    discount_sum = sum(((1 + monthly_rate) ** (-age) for age in range(1, term + 1)), ZERO)
    return principal / discount_sum


def monthly_hazard(lifetime_pd: Decimal, term: int) -> Decimal:
    if lifetime_pd == 0:
        return ZERO
    if lifetime_pd == 1:
        return D(1)
    # Preserve significant digits through both subtractions for tiny PDs.
    with localcontext() as ctx:
        ctx.prec = max(ctx.prec, len(lifetime_pd.as_tuple().digits)) + max(0, -lifetime_pd.adjusted()) + 4
        hazard = 1 - (1 - lifetime_pd) ** (D(1) / term)
    return +hazard


def _validate_inputs(cohorts, assumptions, policy, expected_applications):
    assumptions.validate()
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy: {policy}")
    if not isinstance(expected_applications, Decimal) or not expected_applications.is_finite() or expected_applications < 0:
        raise ValueError("Expected applications must be a finite, nonnegative Decimal.")
    seen = set()
    for c in cohorts:
        key = (c.origination_month, c.risk_band)
        if key in seen:
            raise ValueError(f"duplicate cohort key: {key}")
        seen.add(key)
        if type(c.origination_month) is not int or not 0 <= c.origination_month < ORIGINATION_MONTHS:
            raise ValueError("Origination month must be an integer from 0 to 23.")
        if c.risk_band not in BANDS or c.risk_band not in POLICIES[policy]:
            raise ValueError("A funded cohort must belong to the selected policy's risk bands.")
        for name in ("principal", "expected_count"):
            v = getattr(c, name)
            if not isinstance(v, Decimal) or not v.is_finite() or v <= 0:
                raise ValueError(f"Cohort {name} must be a finite, positive Decimal.")
    if sum((c.expected_count for c in cohorts), ZERO) > expected_applications + TOLERANCE:
        raise ValueError("Funded loan count cannot exceed the application denominator.")


def _cohort_schedule(c: CohortInput, a: Assumptions) -> tuple[CohortMonth, ...]:
    rate = a.borrower_rate / 12
    payment = contractual_payment(c.principal, a.borrower_rate, a.term)
    hazard = monthly_hazard(a.lifetime_pd(c.risk_band), a.term)
    survival = D(1)
    # Contractual balance of the entire original cohort in the absence of default.
    contractual_balance = c.principal
    recoveries_due = {}
    rows = [CohortMonth(
        c.origination_month, c.risk_band, c.origination_month, 0,
        originations=c.principal, ending_principal=c.principal,
        expected_active=c.expected_count, funded_loans=c.expected_count,
        merchant_fees=c.principal * a.merchant_fee,
        acquisition_expense=c.expected_count * a.acquisition_cost,
    )]
    for age in range(1, a.term + a.recovery_lag + 1):
        opening = contractual_balance * survival if age <= a.term else ZERO
        chargeoff = principal = interest = defaults = servicing = ZERO
        if age <= a.term:
            chargeoff = opening * hazard
            defaults = c.expected_count * survival * hazard
            survival *= 1 - hazard
            interest_contractual = contractual_balance * rate
            principal_contractual = payment - interest_contractual
            # The last contractual payment clears the tiny arithmetic residual.
            if age == a.term:
                principal_contractual = contractual_balance
            principal_contractual = min(contractual_balance, principal_contractual)
            interest = interest_contractual * survival
            principal = principal_contractual * survival
            servicing = c.expected_count * survival * a.servicing_cost
            contractual_balance -= principal_contractual
            due_age = age + a.recovery_lag
            recoveries_due[due_age] = recoveries_due.get(due_age, ZERO) + chargeoff * a.recovery_rate
        ending = contractual_balance * survival if age <= a.term else ZERO
        active = c.expected_count * survival if age < a.term else ZERO
        rows.append(CohortMonth(
            c.origination_month, c.risk_band, c.origination_month + age, age,
            opening_principal=opening, principal_collections=principal,
            interest_revenue=interest, gross_chargeoffs=chargeoff,
            recoveries=recoveries_due.get(age, ZERO), ending_principal=ending,
            expected_active=active, expected_defaults=defaults, servicing_expense=servicing,
        ))
    return tuple(rows)


def run_model(
    cohorts: tuple[CohortInput, ...], assumptions: Assumptions, policy: str,
    expected_applications: Decimal, dataset_hash: str,
) -> ModelResult:
    """Run 24 origination months plus the same contractual runoff for every policy.

    Inputs are already approved, demand-weighted cohorts. Negative cash remains
    visible; the model never invents extra financing or stops costs early.
    """
    cohorts = tuple(cohorts)
    with localcontext() as ctx:
        ctx.prec = 34
        _validate_inputs(cohorts, assumptions, policy, expected_applications)
        a = assumptions
        horizon = ORIGINATION_MONTHS + a.term + a.recovery_lag
        cohort_rows = tuple(row for c in sorted(cohorts, key=lambda c: (c.origination_month, BANDS.index(c.risk_band)))
                            for row in _cohort_schedule(c, a))
        by_month = [[] for _ in range(horizon)]
        for row in cohort_rows:
            by_month[row.month].append(row)
        carry_principal = carry_debt = cumulative_result = ZERO
        cash = a.initial_cash
        monthly = []
        residuals = {name: ZERO for name in ("loan", "debt", "cash", "equity", "cohort")}
        exposure_limits_ok = True
        aggregate_fields = (
            "originations", "principal_collections", "interest_revenue", "gross_chargeoffs",
            "recoveries", "ending_principal", "expected_active", "expected_defaults",
            "funded_loans", "merchant_fees", "acquisition_expense", "servicing_expense",
        )
        for month, rows in enumerate(by_month):
            sums = {name: sum((getattr(r, name) for r in rows), ZERO) for name in aggregate_fields}
            debt = min(a.facility_limit, a.advance_rate * sums["ending_principal"])
            debt_draw = debt - carry_debt
            funding = carry_debt * a.funding_rate / 12
            net_loss = sums["gross_chargeoffs"] - sums["recoveries"]
            contribution = (sums["interest_revenue"] + sums["merchant_fees"] - funding
                            - sums["servicing_expense"] - sums["acquisition_expense"] - net_loss)
            operating = contribution - a.monthly_opex
            inflows = (sums["principal_collections"] + sums["interest_revenue"]
                       + sums["merchant_fees"] + sums["recoveries"] + debt_draw)
            outflows = (sums["originations"] + funding + sums["servicing_expense"]
                        + sums["acquisition_expense"] + a.monthly_opex)
            closing_cash = cash + inflows - outflows
            cumulative_result += operating
            row = MonthlyResult(
                month=month, opening_principal=carry_principal, **sums,
                opening_debt=carry_debt, ending_debt=debt, net_debt_draw=debt_draw,
                funding_expense=funding, platform_opex=a.monthly_opex,
                net_credit_loss=net_loss, contribution=contribution, operating_result=operating,
                opening_cash=cash, ending_cash=closing_cash,
            )
            monthly.append(row)
            equations = {
                "loan": carry_principal + row.originations - row.principal_collections - row.gross_chargeoffs - row.ending_principal,
                "debt": carry_debt + debt_draw - debt,
                "cash": cash + inflows - outflows - closing_cash,
                "equity": closing_cash + row.ending_principal - debt - a.initial_cash - cumulative_result,
                "cohort": carry_principal - sum((r.opening_principal for r in rows), ZERO),
            }
            for name, residual in equations.items():
                residuals[name] = max(residuals[name], abs(residual))
            for c in rows:
                residuals["cohort"] = max(residuals["cohort"], abs(
                    c.opening_principal + c.originations - c.principal_collections - c.gross_chargeoffs - c.ending_principal))
                exposure_limits_ok &= (c.gross_chargeoffs >= 0 and c.principal_collections >= 0
                    and c.gross_chargeoffs + c.principal_collections <= c.opening_principal + TOLERANCE
                    and c.ending_principal >= 0 and c.recoveries >= 0)
            exposure_limits_ok &= 0 <= debt <= a.facility_limit and debt <= a.advance_rate * row.ending_principal + TOLERANCE
            cash, carry_principal, carry_debt = closing_cash, row.ending_principal, debt

        def total(name):
            return sum((getattr(row, name) for row in monthly), ZERO)

        funded = total("funded_loans")
        principal = total("originations")
        contribution = total("contribution")
        lowest = min(monthly, key=lambda r: r.ending_cash)
        # Every recovery is received at full runoff. The lifetime loss fraction
        # avoids a signed rounding residue from summing delayed monthly credits,
        # which could falsely breach an exact zero-loss cap at 100% recovery.
        net_loss = total("gross_chargeoffs") * (1 - a.recovery_rate)
        runoff_residual = max(abs(carry_principal), abs(carry_debt),
                              abs(total("recoveries") - total("gross_chargeoffs") * a.recovery_rate))
        maximum = max(*residuals.values(), runoff_residual)
        checks = Checks(
            passed=maximum <= TOLERANCE and exposure_limits_ok, tolerance=TOLERANCE,
            maximum_residual=maximum, loan_residual=residuals["loan"],
            debt_residual=residuals["debt"], cash_residual=residuals["cash"],
            equity_residual=residuals["equity"], cohort_residual=residuals["cohort"],
            runoff_residual=runoff_residual, exposure_limits_ok=exposure_limits_ok,
        )
        summary = Summary(
            expected_applications=expected_applications, funded_loans=funded,
            approval_rate=funded / expected_applications if expected_applications else None,
            funded_principal=principal, interest_revenue=total("interest_revenue"),
            merchant_fees=total("merchant_fees"), gross_chargeoffs=total("gross_chargeoffs"),
            recoveries=total("recoveries"), net_credit_loss=net_loss,
            loss_ratio=net_loss / principal if principal else None,
            funding_expense=total("funding_expense"), servicing_expense=total("servicing_expense"),
            acquisition_expense=total("acquisition_expense"), platform_opex=total("platform_opex"),
            contribution=contribution, unit_contribution=contribution / funded if funded else None,
            operating_result=total("operating_result"),
            operating_result_24m=sum((r.operating_result for r in monthly[:ORIGINATION_MONTHS]), ZERO),
            minimum_cash=lowest.ending_cash, minimum_cash_month=lowest.month,
            additional_equity_required=max(ZERO, a.cash_floor - lowest.ending_cash),
            peak_debt=max(r.ending_debt for r in monthly),
            minimum_facility_headroom=a.facility_limit - max(r.ending_debt for r in monthly),
        )
        identity = {
            "model_version": MODEL_VERSION, "dataset_hash": dataset_hash,
            "policy": policy, "assumptions": a.to_dict(),
            "expected_applications": decimal_text(expected_applications),
            "cohorts": [{k: decimal_text(v) if isinstance(v, Decimal) else v for k, v in asdict(c).items()}
                        for c in sorted(cohorts, key=lambda c: (c.origination_month, BANDS.index(c.risk_band)))],
        }
        return ModelResult(policy, a, dataset_hash, tuple(monthly), cohort_rows, summary, checks, stable_hash(identity)[:16])
