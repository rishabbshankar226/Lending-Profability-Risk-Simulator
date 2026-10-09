# Application and interview notes

Use these drafts after practicing the financial and technical explanations below. Choose the bullets that fit the role and describe the work you can demonstrate. The [reviewer guide](reviewer-guide.md) is the short project introduction; the [90-second script](walkthrough.md) is the live demonstration route.

## Project pitch

“I built a Python/SQL simulator to examine a lending growth decision: which approval policy produces the most operating profit while staying within credit-loss and cash limits? In the synthetic base case, broader approvals increase modeled profit, but the lender runs out of cash under the assumed facility. Additional equity makes a broader policy feasible; doubled defaults leave no profitable recommendation. I connected the loan, funding and cash schedules, added reconciliations and reproducible exports, and built a dashboard so someone can inspect the assumptions and tradeoffs. The inputs are illustrative, so I present this as scenario analysis rather than a validated credit forecast.”

## Resume bullet drafts

**Shared project bullet**

- Built a Python/SQL lending simulator comparing three approval policies across 10,000 synthetic applications, with a Streamlit dashboard, reconciled financial schedules and reproducible scenario exports.

**Finance emphasis**

- Modeled profitability and liquidity over a 39-month runoff horizon; showed how cash constraints change approval-policy feasibility despite higher projected operating profit, and documented capital requirements in downloadable decision briefs.

**Credit/risk emphasis**

- Analyzed illustrative default, recovery and funding assumptions through cohort views and a 20-case sensitivity grid; enforced loss and cash limits and reported scenarios with no profitable eligible policy.

The dollar outputs are scenario findings, not savings or revenue achieved for a real lender. The risk bands are synthetic inputs, not scores learned from borrower outcomes. Link the source code on `main` and the reviewer guide; merged PR #1 preserves the implementation review history.

## Questions and answer checkpoints

### Why does the highest-profit policy fail in the base case?

Aggressive produces $396,446 modeled full-runoff operating profit, but its minimum cash is −$1,485,855. It fails the $50,000 cash floor despite meeting the illustrative 5% net principal loss cap. Conservative is eligible with $48,133 profit and $147,450 minimum cash. Explain which constraint binds before proposing growth. Negative cash represents an unfunded requirement, not credit automatically supplied by the simulator.

**Demonstrate:** Base case → Strategy comparison. Trace the values to the [business memo](business-memo.md) and [saved base outputs](base-case.json).

### What changes when equity rises to $1.25m?

Starting cash rises by $750,000. Balanced's minimum cash moves from −$696,143 to $53,857, making it eligible and recommended. Its modeled operating profit remains $294,468 because the loan economics and debt rule stay the same and there is no equity financing cost. This establishes cash feasibility under the assumptions; it does not establish an attractive equity return or a financing commitment.

**Demonstrate:** More capital · $1.25m → Preview decision brief. Explain the [capital manifest](capital-decision-brief.md), including the selected portfolio versus calculated recommendation.

### Why are principal collections cash but not revenue?

A borrower repayment exchanges the loan asset for cash. Interest is revenue; returned principal is not. For a $1,200 zero-interest loan with costs/defaults disabled, twelve $100 principal payments restore the original cash without generating interest income. A charge-off removes outstanding principal and future collections; the original advance was already paid, so the charge-off is not another cash payment. A later recovery increases cash and offsets credit expense in this simplified management model.

**Evidence:** The zero-interest and $900-default/$225-recovery fixtures in [test_model.py](../tests/test_model.py). The recovery arrives in month four after a month-one default and three-month lag.

### How is lifetime PD translated into losses?

The constant conditional monthly hazard is `1 − (1 − lifetime_PD)^(1/12)`. Each month it applies to surviving loans before payment. Defaulted principal uses the remaining contractual balance, and recoveries depend on the charged-off exposure. Lifetime borrower PD and net loss divided by original funded principal have different denominators and timing; a 12% PD does not imply 12% net principal loss.

**Evidence:** [Model specification](model-spec.md#loan-and-loss-math) and the survivor/exposure fixture in [test_model.py](../tests/test_model.py). Expected counts may be fractional; the model does not sample fresh random defaults on each scenario change.

### Why run beyond the origination plan?

At month 24, late loans still have repayments and recoveries ahead. Compare all policies through the same complete runoff, including continuing overhead. Conservative's first 24 months show $98,960 operating profit, versus $48,133 through the 39-month horizon. Cohort cells beyond a chosen observation cutoff stay unavailable rather than being shown as zero loss. Every cohort view is projected.

**Evidence:** [Business memo](business-memo.md), [horizon specification](model-spec.md#horizons-and-decisions), and the late-cohort runoff fixture in [test_model.py](../tests/test_model.py).

### What happens if no policy should be recommended?

Eligibility requires funded loans, successful reconciliation, acceptable net loss and sufficient minimum cash. The model ranks eligible policies using unrounded profit, then requires positive profit. No eligible policy, all eligible policies losing money, and breakeven are distinct states. At 2× defaults, Conservative remains within the limits but loses $11,563; the tool provides no profitable recommendation and can show the least loss-making eligible policy only as a diagnostic.

**Evidence:** [Default-stress brief](default-stress-decision-brief.md), [decision implementation](../lending_simulator/decisions.py) and [boundary/tie/empty-state tests](../tests/test_decisions.py).

### How do the SQL joins avoid misleading approval rates?

Each policy uses the full application population as its denominator. Approval is a conditional count; average approved ticket uses approved count. Counting application keys handles an empty left-joined population, and `NULLIF` keeps an undefined rate unavailable. Application and policy-band keys are unique before aggregation. A future one-to-many outcome join would require checking its grain to avoid multiplying principal. Scenario growth weights are applied after integer-cent aggregation to the same fixed population.

**Evidence:** [Population query](../lending_simulator/queries/policy_population.sql), [cohort query](../lending_simulator/queries/cohort_inputs.sql) and [data/SQL tests](../tests/test_data_and_sql.py).

### What does reconciliation prove, and what would real use require?

The engine checks loan, debt, cash, cohort and simplified-equity identities each month using Decimal arithmetic. Run identities include the dataset, model version and assumptions; exported inputs can reproduce a result. These controls establish calculation consistency under the inputs. They do not establish that the PD, recoveries, demand or costs are realistic.

For an empirical version, first obtain matched, appropriately licensed installment-loan outcomes. Define the outcome and exposure denominator; account for immature cohorts, lock a chronological evaluation split, avoid future-information leakage and report uncertainty. Funded-only records cannot establish the outcomes of rejected applicants. Product use would also require work on equity/funding economics, prepayments, pricing response and intramonth liquidity.

**Evidence:** [Validation](validation.md), [source-fitness decision](source-fitness.md) and [scope exclusions](model-spec.md#funding-profit-and-cash). Those empirical steps have not been completed in this project.

## Rehearse with inspectable evidence

From an activated Python 3.12 environment installed using the README:

```bash
python -m pytest tests/test_model.py::test_zero_interest_loan_has_twelve_100_dollar_principal_payments tests/test_model.py::test_complete_default_removes_900_and_recovers_225_after_three_months tests/test_decisions.py tests/test_data_and_sql.py
python -m lending_simulator.cli --output artifacts/interview-base
```

For a downloaded brief, save its embedded JSON as `manifest.json`, then reproduce the inputs:

```bash
python -m lending_simulator.cli --assumptions path/to/manifest.json --output artifacts/interview-reproduced
```

Before presenting, explain one loan by hand, identify the binding limit in each guided example, trace one SQL denominator, and reproduce one exported scenario. Use the live demo for interaction and keep a saved brief/workbook available as the review takeaway.
