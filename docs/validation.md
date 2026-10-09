# Validation and release status

## Performed locally

The financial model, data, SQL, decision rules, exports, CLI, simulated dashboard and HTTP server have 118 passing automated checks in `tests/`. Run `python -m pytest`. The suite has no disabled or skipped checks. Python compilation and the reproducible base-case CLI also passed. The [workbench candidate review](ui-workbench-review.md) identifies the tested implementation commit, new behavior and scoped browser acceptance. Earlier hosted checks below do not cover this redesign.

Independent financial cases include 12 zero-interest $100 principal payments on a $1,200 loan; a $900 default with a $225 delayed recovery and $675 net loss; $10 monthly interest on $1,000 opening debt at 12%; and a positive-interest amortization benchmark. Other checks cover PD/recovery endpoints, late-loan runoff, equal policy overhead horizon, collateral repayments, funding-rate differences, invalid inputs and monthly financial identities.

Data/SQL checks verify the seeded 10,000-row population and exact band counts, CSV roundtrip/content hash, duplicates and invalid fields, policy denominators, nested approval sets, expected demand weights, empty rates and bound policy inputs.

Decision checks cover exact loss/cash boundaries, an ineligible high-profit policy, no eligible policy, all losses, breakeven, tie rules and identical comparison inputs. AppTest checks preloaded views, scenario apply, complete reset, unchanged numeric input identity, invalid inputs, independent visitor sessions, stress-grid state and matching downloads.

Six startup/state regressions were reproduced before their fixes: a missing CSV, incomplete/non-object manifests, hash/version changes after a warm run, and a valid dataset replacement retaining old results. They now pass. Manifest validation checks the required provenance fields against the loaded dataset; both file digests participate in the cache identity. Valid replacements refresh results using the visitor's applied policy and assumptions.

The HTTP integration check in `tests/test_server.py` starts a real Streamlit process on a temporary loopback port, verifies `/_stcore/health` returns HTTP 200/`ok`, verifies `/` serves an HTML document, and terminates the process. An earlier local preview server also returned HTTP 200/`ok`. These are server checks: they do not render the frontend, establish a browser WebSocket session, or verify user interactions.

Workbook checks inspect formula cells and saved values. The independent workbook was authored/recalculated with Artifact Tool from the inspectable workbook specification. Its 12% nominal amortization benchmark produced a $106.618546414 monthly payment and zero final principal. Changing interest to zero produced $100/month; changing recovery to 100% produced zero net loss. The original inputs were restored, formula errors scanned, and every sheet rendered for review. This is calculation/render verification, not a claim to have tested native Excel on the user's computer.

The app's runtime downloads use the approved Python/XlsxWriter stack. They include the selected run, assumptions, three-policy comparison, monthly/cohort snapshots, financial checks, source links and the same independent benchmark formulas. Portfolio snapshots do not recalculate when workbook inputs are edited; rerun the app/CLI to refresh. CSV packages retain exact Decimal values, units and the selected manifest.

## Performance

`docs/performance.json` records one local measurement pass. Reproduce on Linux with `python -m scripts.measure_performance` after installing development requirements. Timings cover engine calculations and Streamlit's **simulated** AppTest execution. Peak process memory includes those operations, not sustained multi-user load or all possible cached cases. Browser rendering, network latency and hosting cold starts were not measured.

The planning targets were a ≤3-second warm view, ≤2-second ordinary scenario and <250 MB peak runtime. Treat recorded local measurements as scoped evidence, not a deployed service-level claim.

The workbench has a separate [23-operation measurement report](workbench-performance.json), produced with `python -m scripts.measure_workbench`. Each operation retains three local samples, its median and maximum. Source hashes identify the candidate; browser/network/hosting timings and p95 are not inferred. See the candidate review for operation scope and memory limits.

## Hosted browser validation

The [live review dashboard](https://rishabb-lending-simulator.streamlit.app/) was exercised in cloud Chrome at 1363 × 936 on October 7, 2026. All five tabs, capital and stress cases, scenario apply/reset, validation errors, cohort cutoffs and stress-grid invalidation were inspected. Both actual downloads opened and matched the selected Balanced run, dataset hash, assumptions and displayed values. A second Streamlit session retained separate scenario state. See [browser evidence and screenshots](browser-validation.md) for the tested commits, exact run IDs and file inspection.

Real browser inspection identified three presentation defects. Commit `01a89be7693a3154627318e6e95f0bb253c43694` preserves dollar signs in captions, uses percentage categories on the stress grid and cleans the validation message. The 13 existing AppTest checks passed after those edits; [CI on that application commit](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37657326747) passed the full workflow. All three corrected displays were verified in the hosted app after its reboot. No financial-engine change was needed.

Basic keyboard tab, slider and policy-selector checks passed. In the earlier verification tab, the latest 35 console warning/error entries were extension messages, with no application-origin error in that window. This is bounded evidence, not a comprehensive accessibility or network audit.

The later policy summaries expose each policy's profit, minimum cash, principal loss, eligibility and additional equity above the detailed table. Two added AppTest cases check base and $1.25m capital inputs, including the unchanged profits and policy cash/equity values. [Application CI](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37688578471) passed all 59 checks. The actual hosted cards were checked at both capital levels, during unsaved edits and after reset; their values and eligibility matched the applied runs.

Four added AppTest cases cover one-click base, capital and default examples, plus custom editing after an example and independent visitor state. They verify expected run identities, financial values, recommendations, restoration of advanced/draft controls and clearing of old stress results. The full local suite and [CI on the final application code](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37694153765) passed all 63 checks.

Live checks exercised those examples, custom funding/cost changes, replacement of an invalid cash-floor draft, restored cohort cutoff, grid clearing and Enter activation of the capital button. The capital ZIP matched its applied run, inputs and exact financial values. A help tooltip remained over the instructions after keyboard use; the redundant example tooltips were removed, and the clear final capital/default views were captured. Financial calculations and model version did not change.

Seven additional checks cover generated decision briefs: selected portfolio versus recommendation, base/capital/unprofitable/unfunded cases, complete manifest identity, stale selected or mixed comparison inputs, and applied-preview state through edits/errors/reset. The full local suite and [application CI](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37698159872) passed all 70 checks. The case-study funded-principal typo was corrected, and all three table rows were compared with the saved exact base outputs.

Actual base, capital and default-stress Markdown downloads matched local regeneration byte for byte. The capital download retained $1.25m applied equity while the sidebar draft showed $2.1m. Extracting the capital brief's JSON and passing it to the CLI reproduced the Balanced decision and selected run. The live preview and reset were checked, and decision/table captures were saved. The latest console window contained 34 extension metadata errors and one app-origin WebSocket close warning across the refresh session; subsequent scenario/preview/download interactions succeeded.

## Remaining limits

- Full screen-reader/native-widget/zoom testing and physical-device behavior. The workbench candidate has separate CI Chromium reflow, scoped keyboard/contrast, WebSocket and actual-download evidence; the earlier host below is a different build.
- Isolated anonymous viewing. Hosting showed the public setting checked, but the test browser retained owner authentication.
- Measured viewer cold/warm loads, hibernation/wake behavior and sustained multi-user capacity.
- Actual demo recording; real dashboard screenshots and the 90-second script are available.
- Historical calibration/backtesting. Sources remain contextual, and the synthetic risk inputs are illustrative.

PR #1 was merged into `main` at `5602a062d3dd0e6f747cb89463252603154376e1`. Its tree exactly matches the reviewed head `becb7231ec7006e6d5a1e23d6a7d53c21f29f956`; [merge CI](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37868969995) passed. The live deployment still uses the retained `feature/lending-simulator` branch with the same application code. No predictive accuracy, real loan approvals, investment return or actual business improvement is claimed.

### Heading structure follow-up

The presentation-only change at `10afcbacd0cda17ba0d3631f1a7dc64f44c024a5` passed all 70 existing checks, compilation and [CI](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37703275592). Hosted DOM inspection confirmed one main title and level-two sections across five views, with the decision preview nested at levels three/four. Keyboard navigation activated the capital example, expanded its preview and downloaded the unchanged brief. See [browser-validation.md](browser-validation.md#heading-and-keyboard-follow-up) and [heading-outline.json](heading-outline.json). This is a scoped accessibility repair; full accessibility, mobile and anonymous checks remain pending.

### Decision-panel implementation before the workbench candidate

The dashboard now presents the calculated recommendation, viewed policy, full-runoff operating result and cash/credit margins before the guided examples. Limit margins use 34-digit Decimal arithmetic; credit-loss differences are percentage points. Breaches smaller than display precision are labeled with a less-than amount rather than rounded to zero. Undefined loss ratios remain n.a., and an empty portfolio retains full-horizon operating expenses.

Thirteen additional automated cases bring the suite to 83. They cover the base panel, a viewed Balanced policy with a Conservative recommendation, no profitable or eligible recommendation, a credit-cap breach, applied-input continuity through draft/invalid edits, an empty portfolio, five exact margin cases and level-two decision/exploration headings. Existing capital/default/reset, stress-cache and export tests still pass with the same run identities. No financial-engine or model-version changes were made, and no dependency was added.

A local Streamlit preview was started, but the cloud browser could not connect to its loopback URL. The HTTP integration check passed within its controlled subprocess. No screenshots, mobile/desktop visual result, browser keyboard result, screen-reader result or measured interaction-performance claim is made for this layout. Browser validation and hosting-branch rollout remain pending.

### Workbench candidate

The candidate adds 35 cases to the prior 83-check suite and preserves its financial assertions while adapting layout-specific expectations. All 118 pass. It separates draft inputs from applied results, selects policies immediately, builds only the active view, compares an immutable baseline, stages exact stress cases and defers each export format. Empty stress loss values remain unavailable, and cohort scaling ignores unfunded policies. The engine, model version, dataset, SQL, export formats and three saved example briefs are unchanged.

The cloud browser initially could not reach the candidate, so the first-screen gate did not precede broad implementation. The subsequent isolated Chromium workflow passed nine rendered browser journeys (59 checks), two exact-base reference captures and the full 118-test suite. A further two controlled CSV export journeys passed ten checks for policy selection during held generation and failure/retry, bringing browser coverage to eleven journeys and 69 checks. They retain the same application/UI/config hashes, use fresh server caches and generate successful files through the original exporter. The [browser record](workbench-browser-validation.md) retains source hashes, actual files/captures, corrected defects and the scope of keyboard, reflow, contrast and transport evidence. The [full review](ui-workbench-review.md) lists remaining physical-device, accessibility and intended-host checks with the rollback/source reconciliation. The candidate has not been merged or deployed.
