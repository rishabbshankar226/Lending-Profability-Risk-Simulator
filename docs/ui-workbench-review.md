# Finance workbench candidate review

**Status: implementation ready for review; browser acceptance incomplete.** This is the candidate on `feat/finance-workbench-ui`, based on `baeda884355734f534babd2bc73ab7018742569f`. The tested implementation commit is **`511cd7fe783b8e1d8186aa863f4a81386150333e`**. Documentation follows in a separate commit; the performance report records hashes of every application/UI source file.

The approved direction is a restrained finance workbench. The candidate replaces the dashboard's five eagerly built tabs with a compact decision summary, three primary decision metrics, a stable toolbar, and one selected analytical view. It retains Python/Streamlit 1.65, the synthetic dataset, and the existing financial model and export formats.

## What changed

| Area | Candidate behavior |
| --- | --- |
| Hierarchy | One title, recommendation separate from viewed policy, profit/cash/loss margins first, secondary measures below. |
| Visual system | Light slate surfaces, dark ink, teal actions, consistent Source Sans typography, compact headings, modest borders, common chart tokens. Only owned markup receives custom CSS. |
| Navigation | Wrapping Overview, Policies, Cohorts, Funding & stress, and Methodology controls. Hidden analytical views are not executed. |
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

`python -m pytest --tb=short --junitxml=artifacts/workbench-tests.xml` passed **118 tests in 69.69 seconds**, with no skipped or disabled cases. The original 83 checks retain their financial and business assertions; layout expectations were adapted to the selected-view navigation, semantic policy table, and explicitly requested preview. Thirty-five cases add draft, comparison, download and chart/state coverage.

Python compilation and `python -m lending_simulator.cli --output artifacts/workbench-base-case` passed. Base CSV/workbook outputs were generated. Regenerated base, capital and default-stress decision briefs match the committed reference files exactly.

| Applied example | Viewed policy | Run ID | Rounded profit / minimum cash |
| --- | --- | --- | --- |
| Base | Conservative | `5a88f7bef3fa93d4` | $48,133 / $147,450 |
| Base, viewing Balanced | Balanced | `a2feec5a72facbc3` | $294,468 / ($696,143) |
| $1.25m starting equity | Balanced | `690e9fa563e2d475` | $294,468 / $53,857 |
| 2× defaults | Conservative | `a2d0056e84a3ceb8` | ($11,563) / $129,605; no profitable recommendation |

Model version remains **0.1.0**. The model, decision rules, dataset, SQL, presentation/export source and dependency versions are unchanged.

The audit reproduced and fixed the empty-portfolio stress conversion failure, stale dirty notice after applying, draft loss during a valid source refresh, and incorrect common cohort scaling when Conservative funds no loans. The full suite also caught a Methodology import cleanup error; it was corrected before this tested commit.

AppTest confirms every view executes, not browser appearance or focus. AppTest lacks an expander-opening action; preview tests explicitly request its state. Deferred-factory tests verify captured data after another result exists, not an actual browser download during an in-flight policy switch.

## Local operation measurements

Reproduce with `python -m scripts.measure_workbench --output artifacts/workbench-performance.json`. The saved [operation report](workbench-performance.json) contains three samples for each of 23 separately named operations, source hashes, medians, maxima and measurement scope. These are local server-code/AppTest timings with already imported Python libraries. They exclude browser rendering, network, hosting and multi-user effects. No p95 is inferred from three samples.

| Operation | Median local seconds |
| --- | ---: |
| Preload with application caches cleared | 0.770 |
| Warm Overview rerun | 0.263 |
| Commit a draft input | 0.232 |
| Navigate to Policies / Cohorts / Funding / Methodology | 0.172 / 0.288 / 0.194 / 0.162 |
| Immediate policy switch | 0.204 |
| Restore draft | 0.216 |
| Uncached custom Run | 0.497 |
| Uncached selected-policy stress grid | 0.689 |
| Generate brief / CSV / workbook | 0.002 / 0.329 / 0.490 |

Peak RSS was 237.48 MB for this sequential mixed process, including AppTest, models, Plotly and exports. It does not establish sustained hosting capacity or independent per-operation memory. Cache limits remain bounded.

## Token contrast calculation

These are sRGB relative-luminance calculations for chosen color pairs, not a rendered accessibility audit. Text pairs exceed 4.5:1.

| Pair | Ratio |
| --- | ---: |
| Ink on page | 13.32:1 |
| Muted text on page | 5.67:1 |
| White action text on teal | 7.58:1 |
| Good / warning / error status text on its surface | 6.39 / 6.22 / 6.37:1 |
| Policy markers on table header | 6.73:1 |

Labels, line patterns, limit references, and numeric alternatives supplement color. Real focus outlines, native widget contrast, browser zoom, mobile reflow and screen-reader output remain unverified.

## Browser gate and plan deviation

A real Streamlit candidate server was started. The cloud browser could not connect to localhost, and the candidate's workspace address returned **net::ERR_BLOCKED_BY_CLIENT**. No supported native preview-forwarding or viewport-control capability was available. No tunnel, browser security bypass, alternate stack or replacement production deployment was introduced.

The first-screen visual gate could therefore not be completed before the rest of the implementation. State, financial, export and native-framework work continued to produce this reviewable candidate; this is a documented deviation from the preferred order, not a passed visual gate. No candidate screenshots or before/after browser comparisons are claimed. The existing media shows the earlier hosted build.

**Keep this PR in draft until a reachable candidate preview can be reviewed.** The following remain required:

- Desktop at 1440 × 900 and 1280 × 800: first-screen density, hierarchy, table/legend clipping, all views, every chart and long warning.
- Phone at approximately 390 × 844 and 320 CSS-pixel reflow: navigation wrapping, sidebar return path, policy cards, numeric input use, tables and reachable exports.
- Keyboard/focus: normal tab order, Run/Restore/examples/policy actions, nav, inspect actions, popovers and conditional preview; no lost focus or accidental rerun application.
- Commit a typed numeric edit and immediately click Run; confirm the intended draft was committed.
- Browser cohort zero versus blank, shared scale, full dates, limit markers and runoff labels.
- Actual deferred downloads: one format at a time, open/preview laziness, in-flight policy change preserving filename/manifest, failure/retry preserving scenario.
- Browser console/WebSocket diagnostics, screen-reader summaries, native contrast and reduced-motion checks.
- Repeat representative operation timing in the intended hosting environment; report operation-specific samples separately.

Merge and public rollout are separate release actions. The current public app uses the older `feature/lending-simulator` source. Do not treat its screenshots or successful interactions as evidence for this candidate.

## Review and rollback

Start locally with Python 3.12 and the pinned requirements, then `python -m streamlit run app.py`. Review Base, More capital, Higher defaults, a draft/restore, pin → different runoff, and selected-case staging. The automated suites are `tests/test_app_workbench.py`, `tests/test_ui_foundations.py`, and `tests/test_ui_downloads.py` alongside all existing tests.

Application assembly remains in `app.py`; pure draft transformations, exact comparison adapters, formatters, charts, components, views and deferred downloads are in `lending_simulator/ui/`. No private Streamlit selectors are used. Financial and export layers remain independently testable.

Before deployment, record the source commit actually running on the candidate host, verify the reference run identities there, and preserve the existing audience/access settings. The previous source `baeda884355734f534babd2bc73ab7018742569f` is the rollback target for the application redesign; record the old deployment separately before changing any hosting source. The retained hosting branch has an older build and must not be overwritten incidentally.
