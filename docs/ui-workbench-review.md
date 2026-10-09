# Finance workbench candidate review

**Status: automated candidate browser checks passed; ready for human design review.** The candidate is on `feat/finance-workbench-ui`, based on `baeda884355734f534babd2bc73ab7018742569f`. The tested application implementation is **`c0d6f393c25d0ceaa51152066a03251c45adc5e2`**. Browser and performance reports retain hashes of every application/UI/config source; later capture-only/documentation commits retain that application. [Rendered evidence and before/after captures](workbench-browser-validation.md) are available.

The approved direction is a restrained finance workbench. The candidate replaces the dashboard's five eagerly built tabs with a compact decision summary, three primary decision metrics, a stable toolbar, and one selected analytical view. It retains Python/Streamlit 1.65, the synthetic dataset, and the existing financial model and export formats.

## What changed

| Area | Candidate behavior |
| --- | --- |
| Hierarchy | One title, recommendation separate from viewed policy, profit/cash/loss margins first, secondary measures below. |
| Visual system | Light slate surfaces, dark ink, teal actions, consistent Source Sans typography, compact headings, modest borders, common chart tokens. Only owned markup receives custom CSS. |
| Navigation | Wrapping Overview, Policies, Cohorts, Funding & stress, and Methodology controls precede the decision summary and are visible at the tested phone widths. Hidden analytical views are not executed. |
| Assumptions | Committed edits produce an Unapplied notice and an input review with units and decimal precision. Applied results stay intact until Run. Restore changes inputs without projecting again. |
| Policy selection | Viewing another policy updates its applied results immediately. The recommendation still compares the complete three-policy bundle. |
| Overview | Separate profit and liquidity axes with calendar dates, a cash-floor reference, the minimum-cash month, runoff shading, and a reconciled operating-profit bridge. Principal movements are excluded from revenue. |
| Policies | Equal fields across all three policies, distinct recommendation/view markers, explicit limit/profit status, comparable profit/cash-margin charts, and numeric detail. Owned table switches to definition-list cards when its container is narrow. |
| Pinned comparison | One immutable applied baseline per session, same-policy deltas, changed inputs with units, and both sets of run identities. Incompatible source/model/basis prevents comparison. |
| Different runoff | Full-runoff profit delta is suppressed when lengths differ. The common first-24-month delta is available; each full-runoff total retains its own horizon label. |
| Cohorts | Blank future/unfunded values stay distinct from zero. Both cutoffs and all policies share one scale. Empty policies do not reduce the scale for funded policies. Data alternatives accompany the charts. |
| Funding and stress | Manual 20-case grid for the viewed policy, four result metrics, case inspection, separate profitability/limit status, and a marker only for an exactly matching applied Decimal pair. |
| Stress staging | A clean draft and matching applied grid are required. Stage replaces the stress/rate inputs; results change only after Run compares all policies. |
| Credit controls | Draft effective lifetime PD is calculated without projections and labels the 100% cap. Applied PD remains available in Methodology. |
| Exports | Each format has a deferred callable and its own cache. Opening Export generates no file; preview generates only the brief. Captured run identity, inputs, dataset, and filename stay tied to the requested result. |
| Financial wording | Small nonzero amounts retain their signs, undefined values read Unavailable, and percentages differ from percentage-point margins. Unrounded model values determine all status. |
| Methodology | Financial timing, definitions, checks, applied assumptions, source limitations, SQL and exact manifest remain discoverable. |

## Interaction contract

| Action | Applied results | Draft / other state |
| --- | --- | --- |
| Commit an input or change analysis view | Same bundle and recommendation | Draft retained; hidden-view selections retained |
| View another policy | Same bundle; viewed result changes immediately | Draft retained; selected-policy stress grid cleared |
| Run valid custom inputs | Complete new three-policy transaction | Draft becomes clean in the same response; stale stress cleared |
| Run invalid inputs | Last valid result and exports retained | Human field message and dirty notice remain |
| Restore applied inputs | No model run | Restores all 18 controls; preserves policy, view and baseline |
| Load an example | Immediately replaces all assumptions and runs | Preserves view/baseline; resets cohort cutoff and stress |
| Reset to base | Base run, Conservative | Overview, first-24-month cutoff, no baseline or stress |
| Pin with unapplied edits | Captures applied results | Edits stay draft |
| Stage a grid case | Same applied result and recommendation | Stages exact pair into draft; no projection |
| Valid dataset replacement | Reprojects applied inputs on validated source | Preserves draft controls; baseline incompatibility is explicit |

Expected-count weights remain fractional and illustrative. No optimizer, authentication, saved-scenario backend, pricing response, forecast calibration, or new financial formula was introduced.

## Automated evidence

`python -m pytest --tb=short --junitxml=artifacts/workbench-tests.xml` passed **118 tests**, with no skipped or disabled cases. The original 83 checks retain their financial and business assertions; layout expectations were adapted to the selected-view navigation, semantic policy table, and explicitly requested preview. Thirty-five cases add draft, comparison, download and chart/state coverage.

Python compilation and `python -m lending_simulator.cli --output artifacts/workbench-base-case` passed. Base CSV/workbook outputs were generated. Regenerated base, capital and default-stress decision briefs match the committed reference files exactly.

| Applied example | Viewed policy | Run ID | Rounded profit / minimum cash |
| --- | --- | --- | --- |
| Base | Conservative | `5a88f7bef3fa93d4` | $48,133 / $147,450 |
| Base, viewing Balanced | Balanced | `a2feec5a72facbc3` | $294,468 / ($696,143) |
| $1.25m starting equity | Balanced | `690e9fa563e2d475` | $294,468 / $53,857 |
| 2× defaults | Conservative | `a2d0056e84a3ceb8` | ($11,563) / $129,605; no profitable recommendation |

Model version remains **0.1.0**. The model, decision rules, dataset, SQL, presentation/export source and production dependency versions are unchanged. Optional browser-test dependencies are pinned separately in `requirements-browser.txt`.

The audit reproduced and fixed the empty-portfolio stress conversion failure, stale dirty notice after applying, draft loss during a valid source refresh, and incorrect common cohort scaling when Conservative funds no loans. The full suite also caught a Methodology import cleanup error; it was corrected before this tested commit.

AppTest confirms every view executes, not browser appearance or focus. AppTest lacks an expander-opening action; preview tests explicitly request its state. Deferred-factory tests verify captured data after another result exists. Actual browser downloads retain their captured filename/manifest across a policy switch, and browser cancellation/retry retains the scenario. Two further browser cases use an isolated test-only wrapper around the CSV builder: one proves policy selection while server generation remains held, and one proves inline error/retry after an uncached builder failure. Successful files use the original exporter and captured applied inputs. Network transfer throttling is not claimed.

## Local operation measurements

Reproduce with `python -m scripts.measure_workbench --output artifacts/workbench-performance.json`. The saved [operation report](workbench-performance.json) contains three samples for each of 23 separately named operations, source hashes, medians, maxima and measurement scope. These are local server-code/AppTest timings with already imported Python libraries. They exclude browser rendering, network, hosting and multi-user effects. No p95 is inferred from three samples.

| Operation | Median local seconds |
| --- | ---: |
| Preload with application caches cleared | 0.486 |
| Warm Overview rerun | 0.133 |
| Commit a draft input | 0.122 |
| Navigate to Policies / Cohorts / Funding / Methodology | 0.093 / 0.172 / 0.089 / 0.103 |
| Immediate policy switch | 0.112 |
| Restore draft | 0.134 |
| Uncached custom Run | 0.291 |
| Uncached selected-policy stress grid | 0.427 |
| Generate brief / CSV / workbook | 0.001 / 0.042 / 0.141 |

Peak RSS was 238.25 MB for this sequential mixed process, including AppTest, models, Plotly and exports. It does not establish sustained hosting capacity or independent per-operation memory. Cache limits remain bounded.

## Token contrast calculation

These are sRGB relative-luminance calculations for chosen color pairs, not a rendered accessibility audit. Text pairs exceed 4.5:1.

| Pair | Ratio |
| --- | ---: |
| Ink on page | 13.32:1 |
| Muted text on page | 5.67:1 |
| White action text on teal | 7.58:1 |
| Good / warning / error status text on its surface | 6.39 / 6.22 / 6.37:1 |
| Policy markers on table header | 6.73:1 |

Labels, line patterns, limit references, and numeric alternatives supplement color. Rendered owned supporting text measures at least 5.40:1; keyboard focus and 390/320-pixel reflow passed the scoped browser checks. Full native-widget contrast, zoom and screen-reader output remain unverified.

## Browser gate and plan deviation

The cloud browser initially could not reach the workspace candidate. The first-screen visual gate could not precede broad implementation; state/framework work proceeded in a draft candidate. This deviation remains part of the record.

The authorized automated-software route subsequently exercised the unchanged app in isolated Chromium on a GitHub Actions runner. **Eleven browser journeys (69 checks) and two exact pre-redesign reference captures passed**, alongside all 118 tests, compilation and CLI generation. Nine journeys run the normal app; two wrap only the CSV generation boundary to exercise slow generation and server failure recovery with fresh caches. The [browser record](workbench-browser-validation.md) identifies exact sources, rendered fixes, raw reports, capture hashes and bounded remaining checks. The native caption-opacity, phone-navigation, stress-axis-label and immediate-edit findings were corrected before acceptance.

Human design review, physical devices, browser zoom, full screen-reader/native-widget accessibility and intended-host behavior remain separate release checks. The source-URL interception experiment did not delay the actual browser download; it is not used as in-flight transport evidence. Native cancellation/retry, actual captured-file identity, controlled slow server generation and uncached generation failure/retry are verified. The test fixture does not establish hosted failures or slow network transfer behavior.

Merge and public rollout are separate release actions. The current public app uses the older `feature/lending-simulator` source. Its existing media is distinct from the candidate captures.

## Review and rollback

Start locally with Python 3.12 and the pinned requirements, then `python -m streamlit run app.py`. Review Base, More capital, Higher defaults, a draft/restore, pin → different runoff, and selected-case staging. The automated suites are `tests/test_app_workbench.py`, `tests/test_ui_foundations.py`, and `tests/test_ui_downloads.py` alongside all existing tests.

Application assembly remains in `app.py`; pure draft transformations, exact comparison adapters, formatters, charts, components, views and deferred downloads are in `lending_simulator/ui/`. No private Streamlit selectors are used. Financial and export layers remain independently testable.

Before deployment, record the source commit actually running on the candidate host, verify the reference run identities there, and preserve the existing audience/access settings. The previous source `baeda884355734f534babd2bc73ab7018742569f` is the rollback target for the application redesign; record the old deployment separately before changing any hosting source. The retained hosting branch has an older build and must not be overwritten incidentally.
