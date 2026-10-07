# Validation and release status

## Performed locally

The financial model, data, SQL, decision rules, exports, CLI and simulated dashboard have 50 passing automated checks in `tests/` (final local run: 8.04 seconds, October 7, 2026). Run `python -m pytest`. The suite has no disabled or skipped checks. Python compilation and the reproducible base-case CLI also passed.

Independent financial cases include 12 zero-interest $100 principal payments on a $1,200 loan; a $900 default with a $225 delayed recovery and $675 net loss; $10 monthly interest on $1,000 opening debt at 12%; and a positive-interest amortization benchmark. Other checks cover PD/recovery endpoints, late-loan runoff, equal policy overhead horizon, collateral repayments, funding-rate differences, invalid inputs and monthly financial identities.

Data/SQL checks verify the seeded 10,000-row population and exact band counts, CSV roundtrip/content hash, duplicates and invalid fields, policy denominators, nested approval sets, expected demand weights, empty rates and bound policy inputs.

Decision checks cover exact loss/cash boundaries, an ineligible high-profit policy, no eligible policy, all losses, breakeven, tie rules and identical comparison inputs. AppTest checks preloaded views, scenario apply, complete reset, unchanged numeric input identity, invalid inputs, independent visitor sessions, stress-grid state and matching downloads.

Workbook checks inspect formula cells and saved values. The independent workbook was authored/recalculated with Artifact Tool from the inspectable workbook specification. Its 12% nominal amortization benchmark produced a $106.618546414 monthly payment and zero final principal. Changing interest to zero produced $100/month; changing recovery to 100% produced zero net loss. The original inputs were restored, formula errors scanned, and every sheet rendered for review. This is calculation/render verification, not a claim to have tested native Excel on the user's computer.

The app's runtime downloads use the approved Python/XlsxWriter stack. They include the selected run, assumptions, three-policy comparison, monthly/cohort snapshots, financial checks, source links and the same independent benchmark formulas. Portfolio snapshots do not recalculate when workbook inputs are edited; rerun the app/CLI to refresh. CSV packages retain exact Decimal values, units and the selected manifest.

## Performance

`docs/performance.json` records one local measurement pass. Reproduce on Linux with `python -m scripts.measure_performance` after installing development requirements. Timings cover engine calculations and Streamlit's **simulated** AppTest execution. Peak process memory includes those operations, not sustained multi-user load or all possible cached cases. Browser rendering, network latency and hosting cold starts were not measured.

The planning targets were a ≤3-second warm view, ≤2-second ordinary scenario and <250 MB peak runtime. Treat recorded local measurements as scoped evidence, not a deployed service-level claim.

## Pending

- Live desktop/narrow-screen browser inspection, actual chart readability, keyboard/accessibility and console/network checks. The available cloud browser could not reach the workspace's localhost server (`ERR_CONNECTION_REFUSED`).
- Public hosting and verification of anonymous access; no live URL is claimed.
- Dashboard screenshots and demo recording; the walkthrough script is prepared.
- Borrower-level or cohort-level historical calibration/backtesting. The source-fitness gate concluded contextual comparison only; risk inputs remain illustrative.

No predictive accuracy, real loan approvals, investment return, actual business improvement or deployment completion is claimed. The pull request is a reviewable implementation package with these explicit remaining release checks.
