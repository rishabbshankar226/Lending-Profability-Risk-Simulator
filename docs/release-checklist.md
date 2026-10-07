# Browser and release acceptance

**October 7, 2026.** [Live review dashboard](https://rishabb-lending-simulator.streamlit.app/) on `feature/lending-simulator`; [draft PR #1](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/pull/1) remains unmerged.

All 57 automated checks pass. Desktop cases below were exercised against the hosted app, with final display fixes checked at `01a89be7693a3154627318e6e95f0bb253c43694`. Detailed run identities, file inspection and screenshots are in [browser-validation.md](browser-validation.md).

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
| Downloads | ZIP and nine-sheet workbook opened; run, inputs, dataset hash and values matched | Passed |
| Visitor sessions | Second session started at base while first retained Balanced/$1.25m | Passed in tabs sharing owner authentication |

Amounts are rounded display values and conditional illustrative projections. Exact base outputs and identities remain in `base-case.json` and the exports.

## Layout, access and runtime

| Check | Evidence / scope | Status |
| --- | --- | --- |
| Desktop layout | Chrome, 1363 × 936; charts, sidebar, tabs, warnings and downloads inspected | Passed at tested size |
| Chart labels | Dollar caption and percentage categories verified after reboot | Passed |
| Keyboard controls | Arrow keys changed sliders; ArrowRight moved Overview to Strategy comparison; keyboard policy selection worked | Basic checks passed |
| Console | Latest 35 warning/error entries were extension messages; none from app origin in that window | Scoped check passed |
| Public setting | Make this app public checked in hosting Share dialog | Observed |
| Anonymous access | Available browser retained owner authentication | Pending |
| Narrow/mobile layout | No viewport/device-emulation control; zoom attempt left measured CSS width unchanged | Pending |
| Full accessibility | Screen reader, contrast measurement and full focus order not tested | Pending |
| Network requests | WebSocket/download request diagnostics unavailable through current browser control | Pending |
| Hosting load behavior | Cold/warm viewer loads, hibernation and sustained multi-user behavior not measured | Pending |
| Screenshots | Real overview, capital, comparison, cohort, stress and methodology captures saved | Complete |
| Walkthrough video | 90-second script prepared; actual interactive recording not captured | Pending |

The public review build is available with these scoped limitations. Server health and simulated AppTest do not establish the pending access, mobile, performance or accessibility checks.
