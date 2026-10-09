# Lending decision brief

Illustrative synthetic expected-value projections; uncalibrated. Historical sources provide context only.

## Decision

**Recommended policy: None.** No eligible strategy is profitable. Conservative is the least loss-making eligible policy, shown only as a diagnostic.

Selected portfolio: **Conservative**. This is the displayed portfolio; the recommendation compares all policies below.

Horizon: **39 months**, Oct 2026 through Dec 2029, including 24 months of originations and complete repayment/recovery runoff.

## Applied assumptions

Starting equity: **USD 500,000**. Facility limit: **USD 2,000,000**. Funding rate: **8.00%** annually. Lifetime default stress: **2×**.

Net principal loss cap: **5.00%**. Month-end cash floor: **USD 50,000**.

## Policy tradeoffs

Amounts are USD, rounded to whole dollars; parentheses denote negative values. Operating profit and net loss cover complete runoff.

| Policy | Funded principal | Operating profit | Net principal loss | Minimum cash | Extra equity for cash floor | Limits |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Conservative | 6,699,873 | (11,563) | 1.68% | 129,605 | 0 | Both limits met |
| Balanced | 11,996,972 | 86,472 | 3.19% | (735,564) | 785,564 | Minimum-cash floor breached |
| Aggressive | 14,989,287 | 15,804 | 4.63% | (1,542,333) | 1,592,333 | Minimum-cash floor breached |

Eligibility tests the credit-loss cap, cash floor and financial reconciliations. A recommendation also requires positive operating profit.

Negative cash is an unfunded diagnostic path. Extra equity is the additional starting cash needed to meet the floor, not committed funding; the model does not charge a cost of equity.

## Scope and reproducibility

This simplified management forecast excludes taxes, prepayment, delinquency stages, price response and intramonth liquidity. It does not establish actual lender performance or borrower prediction accuracy.

Selected run: `153c7d2b57999d98`. Model version: `0.1.1`.

All applied inputs, checks, dataset identity and policy run IDs are recorded below. Exact financial schedules are in the CSV package. Save this JSON as `manifest.json` and run `python -m lending_simulator.cli --assumptions manifest.json` with the matching dataset to reproduce the calculations.

```json
{
  "run_id": "153c7d2b57999d98",
  "model_version": "0.1.1",
  "dataset_hash": "ae93b99dafe7655cc435e73a892a3a34e0a24378de890580f06dfb57fc60a67f",
  "policy": "conservative",
  "assumptions": {
    "term": 12,
    "recovery_lag": 3,
    "borrower_rate": "0.18",
    "merchant_fee": "0.02",
    "pd_low": "0.02",
    "pd_medium": "0.06",
    "pd_high": "0.12",
    "default_stress": "2",
    "recovery_rate": "0.25",
    "funding_rate": "0.08",
    "advance_rate": "0.8",
    "initial_cash": "500000",
    "facility_limit": "2000000",
    "acquisition_cost": "25",
    "servicing_cost": "1",
    "monthly_opex": "7500",
    "demand_growth": "0",
    "loss_cap": "0.05",
    "cash_floor": "50000"
  },
  "expected_applications": "10000",
  "currency": "USD",
  "start_month": "2026-10",
  "month_index_base": 0,
  "operating_horizon_months": 24,
  "full_runoff_months": 39,
  "data_classification": "synthetic projection",
  "historical_evidence_level": "contextual comparison only; uncalibrated",
  "checks": {
    "passed": true,
    "tolerance": "1E-16",
    "maximum_residual": "1.35E-27",
    "loan_residual": "1E-27",
    "debt_residual": "0",
    "cash_residual": "0",
    "equity_residual": "1.35E-27",
    "cohort_residual": "2E-28",
    "runoff_residual": "3E-29",
    "exposure_limits_ok": true
  },
  "decision": {
    "status": "no_profitable_policy",
    "message": "No eligible strategy is profitable. Conservative is the least loss-making eligible policy, shown only as a diagnostic.",
    "recommended_policy": null,
    "diagnostic_policy": "conservative",
    "eligibility": [
      {
        "policy": "conservative",
        "eligible": true,
        "reasons": []
      },
      {
        "policy": "balanced",
        "eligible": false,
        "reasons": [
          "Minimum-cash floor breached"
        ]
      },
      {
        "policy": "aggressive",
        "eligible": false,
        "reasons": [
          "Minimum-cash floor breached"
        ]
      }
    ]
  },
  "comparison_run_ids": {
    "conservative": "153c7d2b57999d98",
    "balanced": "e16b5d7157b72a14",
    "aggressive": "de2a75f45c1d1b01"
  }
}
```
