# Lending simulator: two-minute review

**Question:** How far can a hypothetical lender expand approvals while meeting its credit-loss and cash limits?

This Python/SQL project compares three approval policies over 10,000 seeded fictional applications. A Streamlit dashboard connects loan repayments, defaults, recoveries, funding and operating costs over 24 origination months and a common 39-month runoff horizon. Data and risk inputs are synthetic and uncalibrated.

[Open the dashboard](https://rishabb-lending-simulator.streamlit.app/) · [Review the source on main](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/tree/main) · [Read the business memo](business-memo.md)

For a quick visual introduction, [watch the 90-second captioned screenshot tour](tour/lending-simulator-tour.mp4) or [read its transcript](tour/transcript.md). It uses six actual dashboard captures and has no audio or continuous interaction recording.

## Try three decisions

| Action | Look for | What it demonstrates |
| --- | --- | --- |
| Click **Base case**, then **Strategy comparison** | Conservative earns $48,133 and retains $147,450 minimum cash. Aggressive earns $396,446 but reaches −$1,485,855 cash. | Profit ranking alone cannot determine feasible growth. |
| Click **More capital · $1.25m** | Balanced becomes recommended: $294,468 profit and $53,857 minimum cash. | Equity changes liquidity feasibility; this model does not charge a cost of equity. |
| Click **Higher defaults · 2×** | No profitable eligible policy; Conservative earns −$11,563. | The recommendation can be empty when the economics do not support lending. |

These are rounded, conditional modeled outcomes. The examples replace all inputs and run immediately. Custom sidebar edits apply after **Run scenario**. The displayed portfolio is a separate selection from the recommendation across all three policies.

## Choose a review path

| Interest | Inspect | Evidence |
| --- | --- | --- |
| FP&A / strategic finance | Policy comparison, minimum cash and capital requirements; 24-month result versus full runoff | [Business memo](business-memo.md), [capital decision brief](capital-decision-brief.md) |
| Credit / risk analysis | Default and funding stress, cohort ages, exposure at default, recovery lag and loss limits | [Model specification](model-spec.md), [default-stress brief](default-stress-decision-brief.md), [source fitness](source-fitness.md) |
| Technical implementation | SQL population grain, pure financial engine, reconciliation and reproducible exports | [SQL walkthrough](data-and-sql.md), [model tests](../tests/test_model.py), [validation](validation.md) |

Download **Decision brief** for the current recommendation, all policy tradeoffs and exact inputs. The audit workbook adds financial schedules and independent loan/recovery benchmarks. Saved [base](base-decision-brief.md), [capital](capital-decision-brief.md) and [default-stress](default-stress-decision-brief.md) briefs support review without opening the app.

## Scope of the evidence

The implementation passes 83 automated checks. The new decision panel has automated coverage; its browser rendering remains unverified because the local preview was unreachable from the cloud browser. Earlier hosted desktop scenarios and downloaded briefs were verified; the [browser record](browser-validation.md) identifies tested commits, run IDs and file hashes. PR #1 is merged into `main`, and the merge passed GitHub checks. The hosted app retains `feature/lending-simulator` and does not yet include the decision-panel upgrade. Isolated anonymous access, mobile layout, full accessibility, hosting load measurements and a continuous interactive walkthrough remain pending.

This is a management scenario simulator. It does not demonstrate borrower prediction accuracy, causal approval benefits, production underwriting, or real business savings.
