# Browser and release acceptance

**October 7, 2026.** The implementation is reviewable in draft PR #1 on `feature/lending-simulator`. All 57 local automated checks pass, including real HTTP startup. Browser inspection and public deployment remain pending: the cloud browser cannot reach the healthy workspace localhost server.

## Expected user flows

Run these on the actual hosted or locally accessible app. Record the tested URL, commit, browser, viewport, date and observed run IDs. Every browser case below is currently **pending**, even where AppTest or financial-model checks provide supporting evidence.

| Case | Action | Expected result |
| --- | --- | --- |
| First visit | Open without signing in, uploading files or entering keys | Preloaded synthetic base case, five usable views, conservative recommended |
| Base case | Reset to base; compare all policies | Conservative profit $48,133 and minimum cash $147,450; balanced/aggressive fail the cash floor |
| Capital | Set starting equity to $1.25m and run | Balanced becomes eligible and recommended; its full-runoff profit remains $294,468 and minimum cash is $53,857 |
| Broader policy | Set starting equity to $2.1m and run | Aggressive becomes eligible and recommended; its profit is $396,446 and minimum cash is $114,145 |
| Credit stress | Reset; set default stress to 2× and run | No profitable eligible policy; conservative profit is about −$11,563 |
| Funding stress | Reset; set funding cost to 12% and run | No profitable eligible policy; conservative profit is about −$70,421 |
| Draft edits | Change controls without clicking Run scenario | Applied metrics, policy, run ID and downloads keep the previous successful scenario |
| Invalid inputs | Enter a negative cash floor and run | Clear validation error; previous successful scenario remains visible |
| Complete reset | Change assumptions, policy, cutoff and run stress; reset | Base assumptions/policy/cutoff restored; old stress grid removed |
| Cohorts | Switch First 24 months to Complete runoff | Future ages blank at the first cutoff; complete projected repayment/recovery tail at runoff |
| Stress grid | Generate for a selected applied policy | 20 cases, legible values/eligibility; displayed inputs and failure reasons agree |
| Downloads | Download CSV ZIP and workbook after applying a scenario | Files open; run ID, dataset hash, inputs and selected policy match the visible applied scenario |

Rounded values are expected display amounts, not separate recalculations. Exact base outputs and identities are in `base-case.json`; conditional capital/stress results are explained in `business-memo.md`. All are illustrative projections.

## Layout, access and runtime

- Inspect desktop and narrow/mobile widths. Confirm all five tabs, charts, labels, sidebar controls and downloads are reachable; tables may scroll horizontally.
- Inspect chart marks and tooltips, legend positions, long warning messages, and negative amounts. Record screenshots only from the real rendered dashboard.
- Use keyboard navigation, inspect accessible control names/focus, and check text contrast. Record limitations without calling the dashboard fully accessible from automated checks alone.
- Inspect browser console and network requests, including the Streamlit WebSocket and download requests. Save actual errors or success observations.
- Open the final URL in a separate anonymous session. Verify intended viewers do not need an invitation or login.
- Measure actual cold and warm loads separately from `performance.json`; local calculation/AppTest timings do not measure hosting behavior.
- Capture the walkthrough in `walkthrough.md` only after browser checks. Store the actual screenshots/recording and returned public URL; do not construct a hosting URL.

If any case fails, reproduce and fix it before treating the public demo as released. Passing HTTP readiness means the server is reachable from its test process; it does not establish browser or public access.
