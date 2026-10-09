# Validation and release status

## Performed locally

The financial model, data, SQL, decision rules, exports, CLI, simulated dashboard and HTTP server have 136 passing automated checks in `tests/` (86.29 seconds in the October 9 audit environment). Run `python -m pytest`. The suite has no disabled or skipped checks. Python compilation and reproducible base-case CLI exports also passed. The new local browser evidence below covers the decision panel; earlier hosted checks retain their tested commits and do not establish deployment of the audit branch.

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

## October 9 repository-wide audit

The [plan, self-audit and defect inventory](bug-hunt.md) document 11 patched defect groups. The untouched baseline passed 83 tests; 53 added cases bring the final suite to 136. Regressions cover tiny positive interest/PD, exact zero loss with full recovery, unavailable workbook ratios, empty stress grids, mixed workbook inputs, malformed JSON and CSV, manifest/provenance replay, and oversized USD inputs retaining successful dashboard state. A deterministic test covers 160 input combinations across three policies (480 runs), checking principal, final cash/profit, loss and approval identities independently.

Version 0.1.1 intentionally changes canonical run identities. Dataset bytes, base recommendations and all base displayed values are unchanged; the largest exact base-summary difference is $3e−27. The saved base manifest and three decision briefs were regenerated. The existing nine-sheet audit workbook was imported and refreshed, its independent zero-interest/full-recovery inputs tested and restored, and formula errors scanned. Saved-file checks compare formulas, styles, validation, dimensions and panes with the previous workbook. Native Excel execution remains untested.

Real isolated headless Chromium 153 ran local Streamlit subprocesses at 1440 × 1000 and 390 × 844. Desktop checks exercised all five tabs, the decision panel, capital inputs, actual ZIP/XLSX/Markdown downloads, draft/invalid retention, reset, and empty/high-only startup, workbooks and stress grids. A separate mobile-width visitor started at base, activated capital with Enter and had no document overflow. The tested sessions recorded no console errors, warnings or failed requests; [the report](bug-hunt-browser.json) names the bounded coverage. These checks do not establish hosted anonymous access, physical-device behavior, complete focus/screen-reader support or hosting performance.

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

- Hosted narrow/mobile layout and full screen-reader/focus/contrast testing. Local mobile-width and request checks have the scoped coverage above.
- Isolated anonymous viewing on the hosted service. Hosting showed the public setting checked, but its test browser retained owner authentication.
- Measured viewer cold/warm loads, hibernation/wake behavior and sustained multi-user capacity.
- Actual demo recording; real dashboard screenshots and the 90-second script are available.
- Historical calibration/backtesting. Sources remain contextual, and the synthetic risk inputs are illustrative.

PR #1 was merged into `main` at `5602a062d3dd0e6f747cb89463252603154376e1`. Its tree exactly matches the reviewed head `becb7231ec7006e6d5a1e23d6a7d53c21f29f956`; [merge CI](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37868969995) passed. The live deployment still uses the retained `feature/lending-simulator` branch with the same application code. No predictive accuracy, real loan approvals, investment return or actual business improvement is claimed.

### Heading structure follow-up

The presentation-only change at `10afcbacd0cda17ba0d3631f1a7dc64f44c024a5` passed all 70 existing checks, compilation and [CI](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37703275592). Hosted DOM inspection confirmed one main title and level-two sections across five views, with the decision preview nested at levels three/four. Keyboard navigation activated the capital example, expanded its preview and downloaded the unchanged brief. See [browser-validation.md](browser-validation.md#heading-and-keyboard-follow-up) and [heading-outline.json](heading-outline.json). This is a scoped accessibility repair; full accessibility, mobile and anonymous checks remain pending.

### Decision-panel follow-up (before this audit)

The dashboard now presents the calculated recommendation, viewed policy, full-runoff operating result and cash/credit margins before the guided examples. Limit margins use 34-digit Decimal arithmetic; credit-loss differences are percentage points. Breaches smaller than display precision are labeled with a less-than amount rather than rounded to zero. Undefined loss ratios remain n.a., and an empty portfolio retains full-horizon operating expenses.

Thirteen additional automated cases bring the suite to 83. They cover the base panel, a viewed Balanced policy with a Conservative recommendation, no profitable or eligible recommendation, a credit-cap breach, applied-input continuity through draft/invalid edits, an empty portfolio, five exact margin cases and level-two decision/exploration headings. Existing capital/default/reset, stress-cache and export tests still pass with the same run identities. No financial-engine or model-version changes were made, and no dependency was added.

A local Streamlit preview was started, but that pass's cloud browser could not connect to its loopback URL. The October 9 audit subsequently verified the panel in a local headless browser, as described above. Hosting-branch rollout, full accessibility and measured interaction performance remain pending.
