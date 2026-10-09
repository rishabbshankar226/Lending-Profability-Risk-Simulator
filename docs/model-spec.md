# Model specification

Implementation follows the reviewed v1.2 plan, authorized on October 7, 2026 when the standalone GitHub repository was supplied. One fixed 12-month product, 24 origination months, retained loans, and illustrative risk inputs remain in scope. The historical evidence gate concluded context only. No historical calibration, term change, borrower classifier, or paid service was introduced.

## Inputs and conventions

| Input | Base | Timing / interpretation |
| --- | ---: | --- |
| Nominal annual borrower rate | 18% | Annual / 12; not statutory APR |
| Merchant fee | 2% | Collected and recognized at origination in this management model |
| Lifetime PD, low / medium / high | 2% / 6% / 12% | Entire contractual term; illustrative |
| Recovery | 25% | Outstanding principal charged off, received 3 months later |
| Annual funding rate | 8% | Opening debt × rate / 12 |
| Collateral advance | 80% | Eligible ending performing principal |
| Facility cap | $2,000,000 | No unlimited borrowing |
| Starting equity cash | $500,000 | No automatic new equity |
| Acquisition | $25 | Per funded loan, once at origination |
| Servicing | $1 | Per surviving expected loan in each scheduled payment month |
| Platform expense | $7,500/month | Continues throughout the common runoff horizon |
| Net principal loss cap | 5% | Full-runoff net loss / original funded principal |
| Cash floor | $50,000 | Minimum month-end cash in the entire path |
| Base growth | 0% monthly | Weight = (1 + growth)^application month |

All inputs above are illustrative project settings. The loss cap and cash floor are demonstration management limits, not measured industry targets. Model start: October 2026 (month 0).

## Monthly event order

1. Carry opening cash, performing principal, surviving expected counts, and debt.
2. Apply defaults to existing loans before the scheduled payment.
3. Collect principal and interest from survivors.
4. Receive recoveries due from past defaults.
5. Originate approved loans at month-end; collect merchant fees and incur acquisition costs.
6. Adjust debt to ending eligible collateral and the facility cap.
7. Pay funding interest, servicing, and platform expense; reconcile cash and simplified equity.

Originated loans receive no same-month scheduled payment or default. The first of 12 scheduled payments is one month later. Funding interest uses opening debt, so a new end-month draw accrues from the following month. Servicing is charged for survivors before their last repayment; repaid loans have zero ending active count.

## Loan and loss math

For principal P, monthly rate r, and N=12:

`payment = P*r / (1 - (1+r)^(-N))`, or `P/N` when r=0.

The conditional monthly hazard is `h = 1 - (1 - lifetime_PD)^(1/N)`. Let S be the surviving share and B the no-default contractual balance. Defaulted principal is `B*S*h`; defaults are `original_count*S*h`. Update S by multiplying by `(1-h)`, then collect the contractual interest/principal split times S. This keeps borrower survival separate from amortizing exposure. Stress multiplies lifetime PD and caps it at 100%.

The final contractual installment clears any tiny arithmetic residual. Expected counts and application weights can be fractional. No fresh random outcomes are sampled when controls change.

Net credit expense equals gross charged-off principal less received recoveries. A default removes outstanding principal and future collections. The original loan advance was already a cash outflow; a charge-off creates no second cash payment. Recovery claims are scheduled future flows, not booked assets before receipt.

## Funding, profit, and cash

`ending_debt = min(facility_cap, advance_rate * ending_performing_principal)`.

Debt increases are cash draws; decreases are cash repayments. A charge-off can reduce collateral and force debt repayment.

`contribution = interest + merchant_fees - funding - servicing - acquisition - net_credit_expense`.

`management_operating_result = contribution - platform_opex`.

`closing_cash = opening_cash + principal_collections + interest + merchant_fees + recoveries + net_debt_draw - originations - funding - servicing - acquisition - platform_opex`.

Principal repayments are not revenue. Negative cash stays visible as an unfunded diagnostic path. Additional initial equity needed is `max(0, cash_floor - minimum_cash)`; it is a modeled requirement, not committed financing.

This simplified management accounting excludes GAAP/CECL allowance/provision timing, taxes, prepayments, delinquencies, loan sales, changing prices/demand elasticity, daily settlement timing, and investor discounting.

## Horizons and decisions

The comparison endpoint is `24 + 12 + recovery_lag` monthly rows, including month 0: 39 rows for lag 3, ending December 2029. Last origination is month 23, last contractual repayment month 35, and last possible recovery month 38. Every policy bears costs to that same endpoint, including policies that default sooner or fund no loans.

The first 24-month operating result and the full-runoff result are separate. Cohort ages beyond a selected cutoff are unavailable, not zero. Every curve is projected.

An eligible policy funds loans, reconciles, has full-runoff net loss at or below the cap, and minimum month-end cash at or above the floor. Rank eligible policies by unrounded operating profit. Exact ties use lower loss ratio, then higher minimum cash, then conservative/balanced/aggressive order. None eligible produces failure reasons; all losses produce a least loss-making diagnostic without a profitable recommendation; zero profit is breakeven.

## Numerical checks

Use 34-digit Decimal arithmetic and a $1e−16 internal absolute tolerance. Input principal is integer cents; no intermediate currency rounding is applied. Each month checks:

- Opening loans + originations − principal repayments − gross charge-offs = ending loans.
- Opening debt + net draws = ending debt.
- Cash inflows/outflows = change in cash.
- Cohort flows and opening/ending principal reconcile to the portfolio.
- Cash + performing loans − debt = initial equity + cumulative management operating result.

At runoff, performing loans and debt reach zero, and received recoveries equal the recovery fraction of gross charge-offs. Exposure limits prevent repayment/default exceeding outstanding principal and debt exceeding collateral or the facility cap.

The immutable result bundle carries inputs, summary, monthly/cohort rows, checks, dataset hash and run ID. Canonical Decimal text gives numerically equal inputs the same identity. Dataset, model version, and all assumptions participate in cache/run identity. Session selections are isolated; there is no shared mutable SQLite connection.
