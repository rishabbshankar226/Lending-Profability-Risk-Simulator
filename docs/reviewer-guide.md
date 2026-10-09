# Lending simulator: two-minute review

**Question:** How far can a hypothetical lender expand approvals while meeting its credit-loss and cash limits?

This Python/SQL project compares three approval policies over 10,000 seeded fictional applications. A Streamlit dashboard connects loan repayments, defaults, recoveries, funding and operating costs over 24 origination months and a common 39-month runoff horizon. Data and risk inputs are synthetic and uncalibrated.

[Open the earlier hosted dashboard](https://rishabb-lending-simulator.streamlit.app/) · [Review this candidate's source](../app.py) · [Read the business memo](business-memo.md)

The workbench redesign is a review candidate with 118 passing automated checks. Nine real-browser journeys pass in isolated CI Chromium, with [actual before/after captures](workbench-browser-validation.md). The hosted app and tour below show the earlier build. See [candidate scope and acceptance gates](ui-workbench-review.md) before evaluating visual readiness.

For a quick visual introduction, [watch the 90-second captioned screenshot tour](tour/lending-simulator-tour.mp4) or [read its transcript](tour/transcript.md). It uses six actual dashboard captures and has no audio or continuous interaction recording.

## Try three decisions

| Action | Look for | What it demonstrates |
| --- | --- | --- |
| Click **Base case**, then **Policies** (earlier host: **Strategy comparison**) | Conservative earns $48,133 and retains $147,450 minimum cash. Aggressive earns $396,446 but reaches −$1,485,855 cash. | Profit ranking alone cannot determine feasible growth. |
| Click **More capital · $1.25m** | Balanced becomes recommended: $294,468 profit and $53,857 minimum cash. | Equity changes liquidity feasibility; this model does not charge a cost of equity. |
| Click **Higher defaults · 2×** | No profitable eligible policy; Conservative earns −$11,563. | The recommendation can be empty when the economics do not support lending. |

These are rounded, conditional modeled outcomes. The examples replace all inputs and run immediately. Custom sidebar edits apply after **Run scenario**. The displayed portfolio is a separate selection from the recommendation across all three policies.

In the candidate, use **Restore applied inputs** to discard a draft, **Pin applied scenario** under Policies to compare a subsequent run, and **Stage case as draft** after generating a selected-policy stress grid. Each action preserves the distinction between applied results and edits. Open **Export** for the applied brief, workbook and CSV package.

## Choose a review path

| Interest | Inspect | Evidence |
| --- | --- | --- |
| FP&A / strategic finance | Policy comparison, minimum cash and capital requirements; 24-month result versus full runoff | [Business memo](business-memo.md), [capital decision brief](capital-decision-brief.md) |
| Credit / risk analysis | Default and funding stress, cohort ages, exposure at default, recovery lag and loss limits | [Model specification](model-spec.md), [default-stress brief](default-stress-decision-brief.md), [source fitness](source-fitness.md) |
| Technical implementation | SQL population grain, pure financial engine, reconciliation and reproducible exports | [SQL walkthrough](data-and-sql.md), [model tests](../tests/test_model.py), [validation](validation.md) |

Download **Decision brief** for the current recommendation, all policy tradeoffs and exact inputs. The audit workbook adds financial schedules and independent loan/recovery benchmarks. Saved [base](base-decision-brief.md), [capital](capital-decision-brief.md) and [default-stress](default-stress-decision-brief.md) briefs support review without opening the app.

## Scope of the evidence

The candidate passes 118 automated checks, compilation and CLI regeneration. Draft/view actions do not rerun projections; opening Export prepares no file; three reference briefs match exactly. The [candidate review](ui-workbench-review.md) and [browser record](workbench-browser-validation.md) retain scoped rendered layout, keyboard/focus and actual download evidence. Earlier hosted desktop scenarios and downloads were verified; the [browser record](browser-validation.md) identifies their tested commits and files. The hosted app retains `feature/lending-simulator` and does not include this redesign. Public-host anonymous access, physical-device behavior, full accessibility and hosting load measurements remain pending.

This is a management scenario simulator. It does not demonstrate borrower prediction accuracy, causal approval benefits, production underwriting, or real business savings.
