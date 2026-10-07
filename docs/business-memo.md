# Approval growth requires capital

**October 7, 2026 — hypothetical lender, synthetic expected-value base case**

Under the illustrative inputs, conservative lending is the only policy meeting the 5% net principal loss cap and $50,000 month-end cash floor. It produces **$48,133 expected operating profit** over the complete 39-month horizon. Broader approvals produce more modeled profit but require additional capital to fund their cash paths.

| Policy | Funded principal | Full-runoff operating profit | Net principal loss ratio | Minimum cash | Extra equity to meet floor |
| --- | ---: | ---: | ---: | ---: | ---: |
| Conservative | $6,699,873 | $48,133 | 0.84% | $147,450 | $0 |
| Balanced | $11,996,972 | $294,468 | 1.58% | −$696,143 | $746,143 |
| Aggressive | $14,998,287 | $396,446 | 2.29% | −$1,485,855 | $1,535,855 |

All three meet the selected loss cap in this base case. Balanced and aggressive fail the cash floor because their larger retained loan books outgrow the assumed $2m debt facility and $500,000 equity cash. Negative cash is a financing gap, not borrowing automatically supplied by the model.

Within this simulation, prioritize conservative lending until additional capital or revised economics are available. That recommendation is conditional on the inputs. Raising starting equity to **$1.25m** makes balanced eligible, with minimum cash of $53,857 and unchanged profit of $294,468. At **$2.1m**, aggressive becomes eligible, with minimum cash of $114,145 and unchanged profit of $396,446. Capital changes feasibility; the model does not charge an equity return or assign a valuation to that capital.

The base economics are sensitive. Doubling lifetime default assumptions changes conservative operating profit to **−$11,563**. Increasing annual funding cost from 8% to 12% changes it to **−$70,421**. In both cases, no eligible policy is profitable. Applying 5% monthly application growth produces cash-floor breaches for every policy despite larger projected profit. Growth alone is insufficient.

Conservative's first 24 months show $98,960 operating profit, versus $48,133 through full runoff. Continuing overhead and the remaining repayment/recovery path materially change the result. A short observation window should not determine approval strategy for unfinished cohorts.

Before a real lending decision, obtain matched historical outcomes, validate risk and recovery assumptions, model price response and prepayment, evaluate equity/funding economics, and inspect daily settlement liquidity. This project verifies accounting mechanics and scenario trade-offs. It does not predict actual borrower performance or demonstrate a causal improvement in a lender's business.

**Traceability:** values come from the committed dataset and `docs/base-case.json`. Use the CLI to reproduce them; the dashboard and downloads use the same engine.
