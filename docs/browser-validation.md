# Live browser validation

## Test context

- **URL:** https://rishabb-lending-simulator.streamlit.app/
- **Date:** October 7, 2026
- **Browser:** cloud Chrome; desktop screenshot and measured app-frame dimensions **1363 × 936**

Initial end-to-end cases ran at `6375064b54c824d0f1710aa06d98b6f74910343f`. Display fixes, the capital case, keyboard tabs and visitor-session isolation were checked at `01a89be7693a3154627318e6e95f0bb253c43694` after the hosting reboot. The financial engine did not change between those commits.

The app uses Python 3.12 and `app.py` from `feature/lending-simulator`. [CI for the tested application commit](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37657326747) completed successfully: the workflow runs 57 tests, compilation and reproducible CLI exports. The 13 existing AppTest checks also passed locally after the display edits.

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

## Scope and remaining checks

The Share dialog showed **Make this app public** checked, and the actual URL rendered. Owner authentication remained in the available browser, so isolated anonymous viewing is pending.

The final console inspection returned 35 warning/error entries, all from a browser extension. No application-origin message appeared in that bounded window. This is not a full console history or network trace.

No viewport/device-emulation API was available. A zoom attempt left app-frame CSS width at 1363 pixels and was not counted as mobile verification. Full screen-reader/contrast testing, WebSocket inspection, cold/warm viewer load measurements, hibernation, sustained multi-user testing and actual interactive video recording remain unperformed.

The data and risk assumptions remain synthetic and uncalibrated. These checks do not establish historical prediction accuracy, real underwriting suitability or actual lender performance.
