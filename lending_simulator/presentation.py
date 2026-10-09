"""Convert one result bundle into chart data and reproducible exports."""

import csv
from dataclasses import asdict, fields
from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO
from importlib.resources import files
import json
import zipfile

import pandas as pd

from lending_simulator.data import Dataset
from lending_simulator.decisions import evaluate_policy, select_strategy
from lending_simulator.types import Assumptions, ModelResult, MonthlyResult, CohortMonth, Summary

COUNT_FIELDS = {"expected_active", "expected_defaults", "funded_loans", "expected_applications"}
RATIO_FIELDS = {"approval_rate", "loss_ratio"}
INDEX_FIELDS = {"month", "age", "origination_month", "minimum_cash_month"}
RATE_INPUTS = {"borrower_rate", "merchant_fee", "pd_low", "pd_medium", "pd_high", "recovery_rate",
               "funding_rate", "advance_rate", "demand_growth", "loss_cap"}


def month_label(month: int) -> str:
    ordinal = 2026 * 12 + 9 + month
    return date(ordinal // 12, ordinal % 12 + 1, 1).strftime("%b %Y")


def monthly_frame(result: ModelResult) -> pd.DataFrame:
    rows = [{k: float(v) if isinstance(v, Decimal) else v for k, v in asdict(row).items()} for row in result.monthly]
    frame = pd.DataFrame(rows)
    frame["period"] = [month_label(m) for m in frame["month"]]
    frame["cumulative_operating_result"] = frame["operating_result"].cumsum()
    return frame


def comparison_frame(results: tuple[ModelResult, ...]) -> pd.DataFrame:
    rows = []
    for r in results:
        s, eligibility = r.summary, evaluate_policy(r)
        rows.append({
            "Policy": r.policy.title(), "Approval rate": float(s.approval_rate) if s.approval_rate is not None else None,
            "Expected funded loans": float(s.funded_loans), "Funded principal": float(s.funded_principal),
            "Operating result (24 months)": float(s.operating_result_24m),
            "Operating result (full runoff)": float(s.operating_result),
            "Contribution per funded loan": float(s.unit_contribution) if s.unit_contribution is not None else None,
            "Net principal loss ratio": float(s.loss_ratio) if s.loss_ratio is not None else None,
            "Minimum cash": float(s.minimum_cash), "Additional equity to meet floor": float(s.additional_equity_required),
            "Eligible": eligibility.eligible, "Reason": "; ".join(eligibility.reasons) or "Both limits met",
            "Run ID": r.run_id,
        })
    return pd.DataFrame(rows)


def decision_brief(result: ModelResult, results: tuple[ModelResult, ...]) -> str:
    """A shareable decision and its reproducible inputs from one applied bundle."""
    if result not in results:
        raise ValueError("Decision brief must contain the selected scenario's results.")
    decision = select_strategy(results)
    a, manifest = result.assumptions, result.manifest()

    def amount(value):
        return f"({abs(value):,.0f})" if value < 0 else f"{value:,.0f}"

    recommendation = decision.recommended_policy.title() if decision.recommended_policy else "None"
    lines = [
        "# Lending decision brief", "",
        "Illustrative synthetic expected-value projections; uncalibrated. Historical sources provide context only.", "",
        "## Decision", "",
        f"**Recommended policy: {recommendation}.** {decision.message}", "",
        f"Selected portfolio: **{result.policy.title()}**. This is the displayed portfolio; the recommendation compares all policies below.", "",
        f"Horizon: **{len(result.monthly)} months**, {month_label(0)} through {month_label(len(result.monthly) - 1)}, "
        f"including {manifest['operating_horizon_months']} months of originations and complete repayment/recovery runoff.", "",
        "## Applied assumptions", "",
        f"Starting equity: **USD {amount(a.initial_cash)}**. Facility limit: **USD {amount(a.facility_limit)}**. "
        f"Funding rate: **{a.funding_rate:.2%}** annually. Lifetime default stress: **{a.default_stress.normalize():f}×**.", "",
        f"Net principal loss cap: **{a.loss_cap:.2%}**. Month-end cash floor: **USD {amount(a.cash_floor)}**.", "",
        "## Policy tradeoffs", "",
        "Amounts are USD, rounded to whole dollars; parentheses denote negative values. Operating profit and net loss cover complete runoff.", "",
        "| Policy | Funded principal | Operating profit | Net principal loss | Minimum cash | Extra equity for cash floor | Limits |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in results:
        s, limits = r.summary, evaluate_policy(r)
        loss = "n.a." if s.loss_ratio is None else f"{s.loss_ratio:.2%}"
        reason = "; ".join(limits.reasons) or "Both limits met"
        lines.append(f"| {r.policy.title()} | {amount(s.funded_principal)} | {amount(s.operating_result)} | "
                     f"{loss} | {amount(s.minimum_cash)} | {amount(s.additional_equity_required)} | {reason} |")
    lines.extend([
        "", "Eligibility tests the credit-loss cap, cash floor and financial reconciliations. A recommendation also requires positive operating profit.", "",
        "Negative cash is an unfunded diagnostic path. Extra equity is the additional starting cash needed to meet the floor, "
        "not committed funding; the model does not charge a cost of equity.", "",
        "## Scope and reproducibility", "",
        "This simplified management forecast excludes taxes, prepayment, delinquency stages, price response and intramonth liquidity. "
        "It does not establish actual lender performance or borrower prediction accuracy.", "",
        f"Selected run: `{result.run_id}`. Model version: `{manifest['model_version']}`.", "",
        "All applied inputs, checks, dataset identity and policy run IDs are recorded below. Exact financial schedules are in the CSV package. "
        "Save this JSON as `manifest.json` and run `python -m lending_simulator.cli --assumptions manifest.json` with the matching dataset to reproduce the calculations.", "",
        "```json", json.dumps(manifest | {"decision": asdict(decision),
                                         "comparison_run_ids": {r.policy: r.run_id for r in results}}, indent=2),
        "```", "",
    ])
    return "\n".join(lines)


def cohort_heatmap(result: ModelResult, as_of_month: int | None = None) -> pd.DataFrame:
    """Cumulative net principal loss / original principal, at matching loan ages.

    After a chosen observation cutoff, cells remain NaN. Values are projections,
    even in the first 24 months; the cutoff does not turn them into actuals.
    """
    if as_of_month is None:
        as_of_month = len(result.monthly) - 1
    term = result.assumptions.term + result.assumptions.recovery_lag
    frame = pd.DataFrame(float("nan"), index=range(24), columns=range(term + 1))
    cohorts = {}
    for row in result.cohorts:
        key = row.origination_month
        cohorts.setdefault(key, []).append(row)
    for origin, rows in cohorts.items():
        denominator = sum((r.originations for r in rows), Decimal(0))
        loss = Decimal(0)
        for age in range(term + 1):
            if origin + age > as_of_month:
                break
            loss += sum((r.gross_chargeoffs - r.recoveries for r in rows if r.age == age), Decimal(0))
            if denominator:
                frame.loc[origin, age] = float(loss / denominator)
    return frame


def band_curves(result: ModelResult) -> pd.DataFrame:
    rows = []
    for band in ("low", "medium", "high"):
        matching = [r for r in result.cohorts if r.risk_band == band]
        denominator = sum((r.originations for r in matching), Decimal(0))
        if not denominator:
            continue
        net_loss = collected = Decimal(0)
        for age in range(result.assumptions.term + result.assumptions.recovery_lag + 1):
            aged = [r for r in matching if r.age == age]
            net_loss += sum((r.gross_chargeoffs - r.recoveries for r in aged), Decimal(0))
            collected += sum((r.principal_collections for r in aged), Decimal(0))
            rows.append({"age": age, "risk_band": band.title(), "net_loss_ratio": float(net_loss / denominator),
                         "principal_repaid_ratio": float(collected / denominator)})
    return pd.DataFrame(rows, columns=["age", "risk_band", "net_loss_ratio", "principal_repaid_ratio"])


def units_for(name: str) -> str:
    if name in INDEX_FIELDS:
        return "month index, zero-based"
    if name in COUNT_FIELDS:
        return "expected loan/application count; may be fractional"
    if name in RATIO_FIELDS:
        return "ratio, 0-1; full-runoff denominator unless specified"
    if name.startswith("opening_") or name.startswith("ending_") or name in ("minimum_cash", "peak_debt", "minimum_facility_headroom"):
        return "USD, month-end balance" if not name.startswith("opening_") else "USD, opening balance"
    if name == "risk_band":
        return "illustrative risk category"
    if name == "unit_contribution":
        return "USD / funded expected loan, full runoff"
    return "USD, monthly flow" if name not in ("additional_equity_required",) else "USD, additional starting equity to meet cash floor"


def _record(obj):
    return {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(obj).items()}


def _csv(records: list[dict], fieldnames: list[str]) -> str:
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue()


def csv_package(result: ModelResult, dataset: Dataset) -> bytes:
    """Exact Decimal strings plus metadata; no spreadsheet rounding in the CSV."""
    if result.dataset_hash != dataset.dataset_hash:
        raise ValueError("Export dataset does not match the selected result.")
    buffer = BytesIO()
    schema = {"monthly": {f.name: units_for(f.name) for f in fields(MonthlyResult)},
              "cohorts": {f.name: units_for(f.name) for f in fields(CohortMonth)}}
    schema["summary"] = {
        f.name: units_for(f.name) if f.name in COUNT_FIELDS | RATIO_FIELDS | INDEX_FIELDS
            or f.name in ("unit_contribution", "minimum_cash", "peak_debt", "minimum_facility_headroom", "additional_equity_required")
            else "USD, first 24 months total" if f.name == "operating_result_24m"
            else "USD, full-runoff total"
        for f in fields(Summary)
    }
    manifest = result.manifest() | {"dataset": dataset.manifest()}
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("monthly.csv", _csv([_record(r) for r in result.monthly], [f.name for f in fields(MonthlyResult)]))
        archive.writestr("cohorts.csv", _csv([_record(r) for r in result.cohorts], [f.name for f in fields(CohortMonth)]))
        archive.writestr("summary.csv", _csv([_record(result.summary)], [f.name for f in fields(Summary)]))
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        archive.writestr("units.json", json.dumps(schema, indent=2) + "\n")
    return buffer.getvalue()


def evidence_register() -> dict:
    return json.loads(files("lending_simulator").joinpath("evidence", "sources.json").read_text())


def assumption_register(assumptions: Assumptions) -> list[dict]:
    rows = []
    timing = {
        "borrower_rate": "monthly nominal rate = annual / 12; payments start after origination",
        "merchant_fee": "cash and simplified management revenue at month-end origination",
        "funding_rate": "annual / 12 times opening debt",
        "acquisition_cost": "once per funded loan at origination",
        "servicing_cost": "each scheduled payment month, for surviving loans before repayment",
        "monthly_opex": "every month, including the common runoff horizon",
        "recovery_rate": "fraction of outstanding principal charged off, received after lag",
        "demand_growth": "monthly weight applied to fixed demand rows; no resampling",
        "default_stress": "multiplies lifetime PD; effective PD capped at 100%",
        "loss_cap": "full-runoff net loss / original funded principal",
        "cash_floor": "lowest month-end cash across all modeled months",
    }
    for name, value in assumptions.to_dict().items():
        unit = "ratio" if name in RATE_INPUTS else "months" if name in ("term", "recovery_lag") else "multiple" if name == "default_stress" else "USD"
        if name in ("acquisition_cost", "servicing_cost"):
            unit = "USD / funded loan" if name == "acquisition_cost" else "USD / surviving loan / payment month"
        rows.append({"Assumption": name, "Value": str(value), "Unit": unit, "Classification": "illustrative",
                     "Timing / definition": timing.get(name, "fixed illustrative model input"),
                     "Source": "Project specification v1.2", "Source date": "2026-10-07"})
    return rows


def workbook_payload(result: ModelResult, results: tuple[ModelResult, ...], dataset: Dataset) -> dict:
    if result.dataset_hash != dataset.dataset_hash or result not in results:
        raise ValueError("Workbook must contain the selected scenario's results and dataset.")
    return {"selected_run_id": result.run_id, "manifest": result.manifest() | {"dataset": dataset.manifest()},
            "summary": _record(result.summary), "monthly": [_record(r) for r in result.monthly],
            "cohorts": [_record(r) for r in result.cohorts], "assumptions": assumption_register(result.assumptions),
            "comparison": comparison_frame(results).to_dict(orient="records"), "sources": evidence_register()}
