# Live browser validation

## Test context

- **URL:** https://rishabb-lending-simulator.streamlit.app/
- **Date:** October 7, 2026
- **Browser:** cloud Chrome; desktop screenshot and measured app-frame dimensions **1363 × 936**

Initial end-to-end cases ran at `6375064b54c824d0f1710aa06d98b6f74910343f`. Display fixes, the capital case, keyboard tabs and visitor-session isolation were checked at `01a89be7693a3154627318e6e95f0bb253c43694` after the hosting reboot. The financial engine did not change between those commits.

The app uses Python 3.12 and `app.py` from `feature/lending-simulator`. [CI for the tested application commit](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37657326747) completed successfully: the workflow runs 57 tests, compilation and reproducible CLI exports. The 13 existing AppTest checks also passed locally after the display edits.

The later policy summaries were checked at `8572cec4cd1bf093a1a2a2cecd4d4276a1190f82` at the same desktop size. Two comparison cases increased the suite to 59 checks; the full local suite and [application CI](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37688578471) passed. Financial calculations, model version and run identity rules remained unchanged.

Guided examples were checked at `6b5fedd516a604e21a963d778351b4b01635f44e`; the final button presentation was checked at `8959dae4da566c286ff67325acae12efc4c4a8f9`. Four additional AppTest cases raised the suite to 63 checks. The full local suite and [CI for the final application code](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37694153765) passed. The financial engine and model version did not change.

Decision briefs and their preview were checked at `e87a74d65c59a24103e67b4dafd2e75d6abf2413`. Seven additional checks raised the suite to 70 tests; the full local suite and [application CI](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37698159872) passed. The financial engine and model version remained unchanged.

## Observed scenarios

These are applied scenarios. Selected policy controls the displayed portfolio; recommendations compare all three policies on shared assumptions.

| Inputs / selected policy | Full-runoff result | Minimum cash | Run ID |
| --- | ---: | ---: | --- |
| Base / Conservative | $48,133; recommended | $147,450 | `5a88f7bef3fa93d4` |
| $1.25m equity / Balanced | $294,468; recommended | $53,857 | `690e9fa563e2d475` |
| $2.1m equity / Aggressive | $396,446; recommended | $114,145 | `820023c1a19e26c2` |
| 2× defaults / Conservative | −$11,563; no profitable eligible policy | $129,605 | `a2d0056e84a3ceb8` |
| 12% funding / Conservative | −$70,421; no profitable eligible policy | $110,795 | `e9ddf6d6531a6939` |
| Base equity / Balanced | $294,468; selected policy ineligible | −$696,143 | `a2feec5a72facbc3` |

Base loss ratio was 0.84%; Balanced/$1.25m showed 1.58% and Aggressive/$2.1m showed 2.29%. Base-equity Balanced needed $746,143 additional equity to meet the floor, with $2m peak debt and zero minimum facility headroom.

### Apply, validation and reset

- Changing equity before Run left the base applied metrics and run ID unchanged.
- Applying capital and policy changes produced the corresponding recommendation and selected-policy values.
- A negative cash floor retained the previous funding-stress run. On the corrected build it was also checked at base: “Scenario could not run: cash floor cannot be negative. Showing the last successful result.” appeared and the base run ID remained.
- Reset restored base controls, Conservative and First 24 months. The old stress grid was cleared, including when returning to the same previously tested base run.
- Applying Balanced after generating a Conservative grid removed the stale grid and showed the instruction to run a new one.
- At final verification, one tab retained Balanced/$1.25m run `690e9fa563e2d475` while a new tab started at base run `5a88f7bef3fa93d4`. The tabs shared owner authentication: this verifies separate Streamlit state, not anonymous access.

### Charts and methodology

First 24 months showed the incomplete-cohort triangle with future ages blank. Complete runoff showed the full projected tail. Both were rendered and captured; projected future cells were not presented as observed zero losses.

The Conservative grid displayed all 20 cases: default multipliers 0.5×, 1×, 1.5×, 2× and 3× crossed with funding rates 4%, 8%, 12% and 16%. Final chart labels showed those four percentage categories. Reference cells matched individual scenarios: 1×/8% $48,133; 2×/8% −$11,563; 1×/12% −$70,421. Profit and eligibility were separately labeled.

Methodology rendered timing, assumptions, sources, SQL and the selected manifest. Base checks showed Passed = True, tolerance $1e−16, maximum residual $1.45e−27, zero debt/cash residual and exposure limits satisfied.

Keyboard arrow changes were used for stress/funding sliders. On the final build, ArrowRight moved Overview to Strategy comparison and keyboard policy selection worked. Control names were present in the accessibility tree; this is a basic check, not a full accessibility audit.

## Policy summary follow-up

The initial comparison view placed cash and eligibility farther across the detailed table. Summaries now show each policy's full-runoff profit, minimum cash, net principal loss, credit/cash eligibility and equity gap together above the chart.

At base run `5a88f7bef3fa93d4`, Conservative showed $48,133 profit, $147,450 minimum cash and both limits met. Balanced and Aggressive showed cash-floor breaches with equity gaps of $746,143 and $1,535,855 respectively. Actual dollar signs, parentheses and percentage labels rendered correctly.

Editing equity to $1.25m without Run retained those base summaries and run ID. After Run, selected Conservative had run `0f6c65f5141988cc`; the recommendation changed to Balanced. The three policy profits stayed $48,133/$294,468/$396,446. Minimum cash became $897,450/$53,857/−$735,855, and equity gaps became $0/$0/$785,855. The Conservative and Balanced cards showed both limits met; Aggressive showed the cash breach. The policy displayed in Overview remains a separate selection from the calculated recommendation.

Reset returned the base run and Balanced's −$696,143 minimum cash. Both base and capital summaries were captured from the actual hosted app with all three cards visible together at 1363 × 936.

## Guided example follow-up

The three buttons above the tabs run immediately, starting from base controls and applying only the named change. The selected policy changes the displayed portfolio; the model still calculates the recommendation across all three policies.

| Button | Selected run | Observed result |
| --- | --- | --- |
| Base case | Conservative / `5a88f7bef3fa93d4` | $48,133 profit, $147,450 minimum cash; Conservative recommended |
| More capital · $1.25m | Balanced / `690e9fa563e2d475` | $294,468 profit, $53,857 minimum cash; Balanced recommended |
| Higher defaults · 2× | Conservative / `a2d0056e84a3ceb8` | −$11,563 profit, $129,605 minimum cash; no profitable eligible policy |

After the capital example, custom edits to 12% funding and $10,000 monthly platform expense applied as Balanced run `0fd49b61946d3595`. Before Run, the original capital result stayed applied. A Complete runoff cohort view and a stress grid were then generated for the custom scenario.

Draft edits to 5% monthly growth and a negative cash floor left that custom result unchanged. Clicking Higher defaults replaced both draft edits and the applied custom assumptions: growth returned to 0%, funding to 8%, equity to $500,000, platform expense to $7,500 and cash floor to $50,000. Stress became 2×. The old grid was removed and its Run instruction returned; First 24 months was checked again in the cohort view.

Base case returned the original run. Enter on the capital button applied the expected Balanced run. A redundant button help tooltip stayed over the instructions after keyboard use on the first build; `8959dae` removes those tooltips. After refreshing the host, all three example runs were confirmed again and capital/default views showed clear instructions. The final browser was left at base Overview.

## Download inspection

Both download controls were used after applying **Balanced with $1.25m equity**. The returned ZIP and workbook were opened and inspected directly.

| Check | CSV ZIP | Audit workbook |
| --- | --- | --- |
| Size | 93,411 bytes | 116,496 bytes |
| Run ID | `690e9fa563e2d475` in manifest | Same in Assumptions |
| Policy | balanced | Balanced |
| Equity / horizon | $1.25m; 24 operating / 39 runoff months | Matching saved assumptions |
| Full-runoff profit | Exact CSV values matched the selected run | $294,467.6198309034 saved in Summary |
| Minimum cash | Matching selected-run output | $53,857.07476634917 saved in Summary |
| Checks | Passed; maximum residual 3.2e−27 | Matching residuals in Checks |

The ZIP contained `monthly.csv`, `cohorts.csv`, `summary.csv`, `manifest.json` and `units.json`. The workbook's nine sheets were Summary, Assumptions, Policies, Monthly snapshot, Cohort snapshot, Loan benchmark, Default benchmark, Checks and Sources.

Both carried dataset hash `ae93b99dafe7655cc435e73a892a3a34e0a24378de890580f06dfb57fc60a67f` and model version `0.1.0`. Workbook 24-month profit was $305,862.8114496939, matching the displayed $305,863. Its Policies sheet showed Balanced and Conservative eligible and Aggressive below the cash floor.

SHA-256 identifiers for the specific downloads inspected (regenerated XLSX packaging metadata may differ):

- ZIP: `6bdd5fd4be97f1810302f4c61f15af43f0dcb8ac7cec1e418dffe446fcee4c10`
- XLSX: `371ff97426ea1abef6ecf55e4de5a6ac7e536fd3ff2c89c5e066f035126c4816`

A later ZIP downloaded from the guided capital example at `6b5fedd` was also inspected. Its five files, Balanced run `690e9fa563e2d475`, complete base-plus-capital assumptions, dataset hash, exact profit and minimum cash matched the applied example. That 93,411-byte package had SHA-256 `e2cf21ee3ecfd6fb9643d9a98dd40ad6f83393c27490ab78f57555f1165cd647`; ZIP packaging timestamps can change the file hash without changing the scenario identity.

## Decision brief follow-up

The new Markdown report states the calculated recommendation separately from the selected portfolio, lists shared inputs and all policy tradeoffs, and includes the selected manifest plus all comparison run IDs. The preview and download use the same applied result bundle. Monetary columns are explicitly USD and use whole-dollar rounding; the CSV package retains exact financial values.

Base, capital and default-stress previews produced the expected recommendations and run identities. After the capital example, editing equity to $2.1m without Run left the Balanced recommendation and $1.25m report inputs unchanged. Its downloaded file matched that applied capital case. The default example reported no profitable recommendation, and Reset restored the base brief. The final capital preview showed the recommendation, assumptions and all three policy rows clearly at the tested desktop size.

The three actual files were decoded as UTF-8, their JSON manifests inspected, and their entire contents compared with reports regenerated by the local engine from those same inputs and dataset. All matched exactly. The base download also matched the committed sample. The capital and default downloads are saved as inspectable examples.

| Brief | Selected run | Size | Saved example |
| --- | --- | ---: | --- |
| Base | `5a88f7bef3fa93d4` | 4,427 bytes | [Base brief](base-decision-brief.md) |
| Capital | `690e9fa563e2d475` | 4,329 bytes | [Capital brief](capital-decision-brief.md) |
| Default stress | `a2d0056e84a3ceb8` | 4,454 bytes | [Default brief](default-stress-decision-brief.md) |

SHA-256 of the downloaded files:

- Base: `87737f79818a12f26d05894431559dc4d8cc4009334b982cc1c7267aa41c7625`
- Capital: `a07859eff8a48cf26b058d39f1b2216bab1f4a419bac2c799cdfa181f1760e1b`
- Defaults: `05a3c9f0d2bd04ce54852d9c2d518c81372eb9ccbcb5e0c553c17338b60aa6f3`

The capital JSON block was saved and supplied to the documented CLI command. It reproduced the Balanced recommendation, run `690e9fa563e2d475`, $294,467.62 operating profit and $53,857.07 minimum cash. The source case-study principal typo was also corrected: Aggressive base funded principal is $14,989,287. All three case-study table rows matched `base-case.json`.

The latest console window returned 34 extension metadata errors and one app-origin `WebSocket onclose` warning across the hosting refresh session. Subsequent scenario changes, preview updates and downloads worked. This does not establish complete console or network coverage.

## Screenshots

Real hosted dashboard captures, without compositing or generated chart marks:

| Capture | State / application commit |
| --- | --- |
| [Overview](screenshots/overview.jpg) | Base Conservative; final `01a89be` display fixes |
| [Capital decision](screenshots/capital-balanced.jpg) | Balanced/$1.25m; `01a89be` |
| [Strategy comparison](screenshots/comparison.jpg) | Base; `01a89be`; table continues horizontally/below viewport |
| [Stress grid](screenshots/stress-grid.jpg) | Base Conservative, all 20 cells and percentage labels; `01a89be` |
| [First 24-month cohorts](screenshots/cohorts-first24.jpg) | Base; `6375064` |
| [Complete runoff cohorts](screenshots/cohorts-runoff.jpg) | Base; `6375064` |
| [Methodology](screenshots/methodology.jpg) | Base checks; `6375064` |
| [Policy summaries at base](screenshots/policy-summaries-base.jpg) | Base, all three profit/cash/eligibility cards; `8572cec` |
| [Policy summaries with capital](screenshots/policy-summaries-capital.jpg) | $1.25m equity, Conservative selected / Balanced recommended; `8572cec` |
| [Guided capital example](screenshots/guided-capital.jpg) | Balanced/$1.25m, clear example controls and recommendation; `8959dae` |
| [Guided default example](screenshots/guided-defaults.jpg) | Conservative/2× defaults, no profitable eligible policy; `8959dae` |
| [Decision brief controls and preview](screenshots/decision-brief-preview.jpg) | Capital/Balanced; download controls and calculated decision; `e87a74d` |
| [Decision brief policy tradeoffs](screenshots/decision-brief-tradeoffs.jpg) | Capital/Balanced; recommendation, shared assumptions and all policy rows; `e87a74d` |

## Scope and remaining checks

The Share dialog showed **Make this app public** checked, and the actual URL rendered. Owner authentication remained in the available browser, so isolated anonymous viewing is pending.

The earlier console inspection returned 35 warning/error entries, all from a browser extension. The decision-brief follow-up records the later window separately. Neither is a full console history or network trace.

No viewport/device-emulation API was available. A zoom attempt left app-frame CSS width at 1363 pixels and was not counted as mobile verification. Full screen-reader/contrast testing, WebSocket inspection, cold/warm viewer load measurements, hibernation, sustained multi-user testing and actual interactive video recording remain unperformed.

External performance/accessibility audit requests were unavailable during the follow-up pass. No audit score, mobile result or additional accessibility finding was returned.

The data and risk assumptions remain synthetic and uncalibrated. These checks do not establish historical prediction accuracy, real underwriting suitability or actual lender performance.
