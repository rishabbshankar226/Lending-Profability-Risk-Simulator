# Workbench browser validation

**October 9, 2026 · candidate browser checks passed.** The redesigned application was exercised in real headless Chromium on an isolated GitHub Actions runner. This is rendered application evidence, separate from Streamlit AppTest and the earlier hosted dashboard.

Tested application implementation: `c0d6f393c25d0ceaa51152066a03251c45adc5e2`. [CI run 38002523325](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/38002523325) passed **118 tests**, compilation, CLI generation, **nine browser journeys with 59 checks**, and two pre-redesign reference captures. The [raw browser report](workbench-browser-report.json) records the browser version, exact checkout, application/UI/config hashes, individual checks, operation samples and diagnostics. Later capture-only/documentation commits retain these application hashes.

## Method and scope

`scripts/browser_acceptance.py` starts the unchanged `app.py` on a temporary loopback port and uses Playwright 1.58.0 with Chromium 145.0.7632.6. Each journey has a new browser context. Interactions use visible controls, keyboard actions and ordinary scrolling; DOM/chart inspection is read-only. Actual files are downloaded and opened. No hosting login, deployment or application-state injection is involved.

The empty-input journey runs a separate copy of the same app/code/config with a valid zero-row dataset and matching manifest. It exercises real validation and projections. Zero cash/facility inputs do not create an empty portfolio: the model retains negative-cash diagnostic lending paths, so they cannot substitute for that input case.

The [reference capture report](workbench-reference-report.json) pins the exact pre-redesign base, `baeda884355734f534babd2bc73ab7018742569f`, in the same browser/dependency environment. Captures are raw screenshots. Streamlit scrolls the main area independently of the document, so screenshots show the recorded viewport and scroll position rather than a stitched whole application.

## Acceptance results

| Journey | Viewport | Observed result |
| --- | --- | --- |
| Desktop scenario flow | 1440 × 900 | Base identities; immediate typed edit → Run; recommendation/view distinction; draft navigation/restore; pinned 39/48-month comparison; cohort cutoff; exact stress staging/dirty guard; stale-grid clearing; defaults and invalid-input states; reconciliations. |
| Desktop reflow | 1280 × 800 | All five views; policy table; visible initial navigation; no measured main-area horizontal overflow. |
| Downloads | 1440 × 900 | Real Markdown, XLSX and ZIP; filenames and embedded run identities verified; preview and newly identified policy export. |
| Phone | 390 × 844 | Five views; wrapping navigation above the summary; policy cards; sidebar Run reachable; return to analysis; export controls reachable. |
| Narrow reflow | 320 × 800 | Same navigation/card/sidebar/export checks without measured horizontal overflow. |
| Keyboard | 1280 × 800 | Normal Tab path reaches Run, policy selection and analysis; Enter activates navigation; focus survives selection; popover opens/escapes and returns focus; visible outline; reduced-motion preference recognized. |
| Captured file across selection | 1440 × 900 | CSV requested under Conservative, saved after viewing Balanced; original filename/manifest retained. |
| Empty input source | 1440 × 900 | No eligible policy; unavailable loss headroom; empty cohorts; 20-case stress inspection keeps unavailable net loss distinct from zero. |
| Download cancellation/retry | 1440 × 900 | Chromium denies one actual download (`canceled`), then permits retry; applied metrics/run remain intact; retried ZIP manifest retains that run. |

All nine contexts established Streamlit WebSockets. No browser warnings/errors or unexpected failed page requests were recorded. The deliberate download cancellation is recorded separately; it is a browser failure, not a server-generation failure.

Supporting text was checked from rendered styles, backgrounds and inherited opacity. The minimum measured ratio was **5.40:1**, above the 4.5:1 threshold. This covers owned supporting text sampled on the initial views, not every native widget/chart element or a complete accessibility audit.

The browser retains full-resolution monthly chart data: 39 base months, a date axis and exact cash-floor reference. Stress axes explicitly retain percentage and multiplier categories. AppTest/pure-data tests additionally verify suppressed incompatible runoff deltas, future cohort blanks, common scales, exact applied stress markers, deferred per-format generation and captured immutable inputs.

## Defects found and corrected

| Finding from the rendered audit | Resulting change |
| --- | --- |
| Native captions applied inherited 0.6 opacity, weakening supporting text. | Escaped owned caption markup uses the muted text token at full opacity; rendered contrast is measured. |
| Phone navigation followed stacked metrics and long introductory content. | Compact title/copy and wrapping analysis controls before the decision summary; native minimal toolbar removes development controls. |
| Plotly inferred a numeric funding axis and dropped percent labels. | Explicit categorical stress axes; browser checks and a real chart capture verify `4.00%` through `16.00%`. |
| Opening Credit assumptions reran the app and could overwrite a quick edit before Run. | Keep the already-built credit controls client-side on expansion; the browser immediately types a recovery-lag edit and applies it, preserving the 39/48-month comparison. |

The audit also corrected test setup rather than weakening expectations: native radio labels are clicked rather than their covered inputs; dropdown opening waits for settled rendering; zero financing was replaced with a genuine empty dataset. Request interception affected Streamlit's source-URL check rather than the actual download. It was removed from the transport claim and replaced with native download cancellation and file-identity checks.

## Before and after

| Exact pre-redesign base | Workbench candidate |
| --- | --- |
| ![Pre-redesign desktop](screenshots/workbench/reference-desktop-1440.png) | ![Workbench desktop](screenshots/workbench/desktop-1440-overview.png) |
| ![Pre-redesign phone](screenshots/workbench/reference-phone-390.png) | ![Workbench phone](screenshots/workbench/phone-390-overview.png) |

Additional actual captures: [profit and liquidity timelines](screenshots/workbench/desktop-1440-overview-charts.png), [invalid-input message](screenshots/workbench/desktop-1440-invalid-input.png), [policy table](screenshots/workbench/desktop-1440-policy-table.png), [phone policy cards](screenshots/workbench/phone-390-policy-comparison.png), [profit bridge](screenshots/workbench/desktop-1440-profit-bridge-chart.png), [different runoff](screenshots/workbench/desktop-1440-runoff-comparison.png), [cohort chart](screenshots/workbench/desktop-1440-cohort-chart.png), [staged stress](screenshots/workbench/desktop-1440-stress-chart.png), [loss-making warning](screenshots/workbench/desktop-1440-higher-defaults.png), [empty stress loss](screenshots/workbench/empty-portfolio-stress.png). The [evidence manifest](workbench-evidence.json) retains hashes and source identities.

## Remaining release checks

- Human visual review, physical phone/iOS behavior, browser zoom, screen-reader output and a complete native-widget/focus/contrast audit. Mobile sizes here are Chromium emulation; the phone journeys verify control access rather than hardware numeric-keyboard use.
- Actual candidate-host source/access checks, anonymous public access, cold/warm hosting latency, wake behavior and sustained multi-user load. Loopback navigation timings in the report are individual samples including automation waits; they are not hosting latency or p95.
- A deliberately slow generation/transfer overlapping policy selection and a server-generation failure/retry. The captured-file browser check does not prove the transfer was still in flight during selection. Deferred-factory unit coverage proves captured-generation identity independently.

The redesign remains in a draft PR for human review. Merge and hosting rollout have not occurred. The existing public dashboard and tour continue to show the earlier hosting branch.
