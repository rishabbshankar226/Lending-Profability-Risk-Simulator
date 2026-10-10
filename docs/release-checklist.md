# Browser and release acceptance

**October 9, 2026 (UTC).** [PR #1](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/pull/1) is merged into `main`; [merge checks](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37868969995) passed. The [live dashboard](https://rishabb-lending-simulator.streamlit.app/) still uses `feature/lending-simulator`, with application code matching the merged implementation.

**Workbench candidate:** 118 automated checks pass, plus compilation and CLI regeneration. 14 CI Chromium journeys (94 checks) and two exact pre-redesign reference captures pass. Controlled export cases prove policy selection during held generation, original-file identity after release and retry after an uncached server-generation failure. Native 200%/400% Chrome zoom, exposed control names/main headings, expanded HTML readability and complete SQL/manifest reference contents now pass on the final candidate; 27 raw images accompany the reports. Full screen-reader/cross-browser/interaction-state accessibility and physical devices remain separate checks. The [rendered browser record](workbench-browser-validation.md) identifies tested sources, screenshots, corrections and remaining physical-device/accessibility/hosting checks. The candidate remains in draft for human design review; merge/public rollout need a separate release decision.

**Earlier hosted evidence:** the build below had 70 automated checks at its review. Its desktop cases were exercised against the hosted app, with decision briefs last checked at `e87a74d65c59a24103e67b4dafd2e75d6abf2413`. Detailed run identities, file inspection and screenshots are in [browser-validation.md](browser-validation.md). These passes do not apply to the workbench candidate.

## Financial and interaction cases

| Case | Observed result | Status |
| --- | --- | --- |
| First visit | Preloaded base case and five usable tabs; no upload or API key | Passed in owner session; anonymous access pending |
| Base case | Conservative profit $48,133, minimum cash $147,450; other policies fail cash floor | Passed |
| Capital | $1.25m equity makes Balanced eligible and recommended; profit $294,468, minimum cash $53,857 | Passed |
| Broader policy | $2.1m equity makes Aggressive eligible and recommended; profit $396,446, minimum cash $114,145 | Passed |
| Credit stress | 2× defaults: no profitable eligible policy; Conservative profit −$11,563 | Passed |
| Funding stress | 12% funding: no profitable eligible policy; Conservative profit −$70,421 | Passed |
| Draft edits | Edits before Run left applied metrics and run identity unchanged | Passed |
| Invalid inputs | Negative cash floor showed clear error and retained previous successful result | Passed |
| Complete reset | Base assumptions, policy and First 24 months restored; old stress grid removed | Passed |
| Cohorts | Future ages blank at First 24 months; complete projected tail at runoff | Passed |
| Stress grid | 20 cases; 4%, 8%, 12%, 16% categories; stale grid removed on new applied run | Passed |
| Policy summaries | Profit, minimum cash, loss, limits and equity gaps visible together; base/$1.25m, draft edits and reset checked | Passed |
| Guided examples | Base, $1.25m capital and 2× defaults applied immediately; custom/draft inputs replaced, cohort cutoff restored and old grid cleared | Passed |
| Decision briefs | Base, capital and default-stress files matched local regeneration; preview, draft-input preservation and reset checked; embedded capital manifest reproduced through CLI | Passed |
| Downloads | ZIP and nine-sheet workbook opened; run, inputs, dataset hash and values matched | Passed |
| Visitor sessions | Second session started at base while first retained Balanced/$1.25m | Passed in tabs sharing owner authentication |

Amounts are rounded display values and conditional illustrative projections. Exact base outputs and identities remain in `base-case.json` and the exports.

## Layout, access and runtime

| Check | Evidence / scope | Status |
| --- | --- | --- |
| Desktop layout | Chrome, 1363 × 936; charts, sidebar, tabs, warnings and downloads inspected | Passed at tested size |
| Chart labels | Dollar caption and percentage categories verified after reboot | Passed |
| Keyboard controls | Arrow keys changed sliders; ArrowRight moved Overview to Strategy comparison; keyboard policy selection and Enter on the capital example worked | Basic checks passed |
| Console | Latest 35 entries: 34 extension metadata errors and one app-origin WebSocket close warning across the refresh session; subsequent interactions/downloads worked | Scoped observation recorded |
| Public setting | Make this app public checked in hosting Share dialog | Observed |
| Anonymous access | Available browser retained owner authentication | Pending |
| Narrow/mobile layout | No viewport/device-emulation control; zoom attempt left measured CSS width unchanged | Pending |
| Heading structure | All five views have one main title and level-two sections; preview nests at levels three/four; see heading-outline.json | Passed at tested size |
| Full accessibility | Heading outline and example/preview/download keyboard actions checked; screen reader, contrast measurement and full focus order not tested | Pending |
| Network requests | WebSocket/download request diagnostics unavailable through current browser control | Pending |
| Hosting load behavior | Cold/warm viewer loads, hibernation and sustained multi-user behavior not measured | Pending |
| Screenshots | Fourteen validation captures plus six current tour captures; native screenshots retained | Complete |
| Captioned screenshot tour | 90-second MP4, transcript, captions and hashed storyboard; all six decoded scene samples inspected | Complete |
| Continuous walkthrough recording | 90-second script prepared; actual interactive recording not captured | Pending |

The public review build is available with these scoped limitations. Server health and simulated AppTest do not establish the pending access, mobile, performance or accessibility checks.

External performance/accessibility audits were unavailable during the follow-up pass; no audit score or mobile result was produced.
