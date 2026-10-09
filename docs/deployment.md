# Hosted deployment

**Live URL:** https://rishabb-lending-simulator.streamlit.app/

The Streamlit Community Cloud review build was deployed and inspected on **October 7, 2026**. The assigned URL rendered the application, and the hosting Share dialog showed **Make this app public** checked. An isolated anonymous browser session has not been tested.

| Setting | Observed deployment |
| --- | --- |
| Repository | `rishabbshankar226/Lending-Profability-Risk-Simulator` |
| Hosting branch (rechecked October 9, 2026 UTC) | `feature/lending-simulator` |
| Implementation branch | `main` |
| Entrypoint | `app.py` |
| Python | 3.12 selected; host log reported 3.12.15 |
| Dependencies | Committed `requirements.txt` |
| Data | Preloaded synthetic CSV and matching manifest |
| Secrets | None required |
| Latest application code tested | `10afcbacd0cda17ba0d3631f1a7dc64f44c024a5` |
| Verified merge commit | `5602a062d3dd0e6f747cb89463252603154376e1` |

[PR #1](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/pull/1) was merged into `main` on October 9, 2026 (UTC), and [merge CI](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/actions/runs/37868969995) passed. The merged tree exactly matches the reviewed implementation. The hosting logs still identify `feature/lending-simulator`; its application code matches `main`. General settings expose the app URL and Python version, but no source-branch editor. The existing hosting branch is retained to keep this deployment available. Future application changes on `main` must also reach the hosting branch until hosting is migrated.

The app was asleep during the post-merge check. After waking it, Overview rendered the expected Conservative run `5a88f7bef3fa93d4`: $48,133 full-runoff operating result, 0.84% net principal loss and $147,450 minimum month-end cash.

## Verified behavior

Desktop Chrome rendered all five views. Capital, default and funding scenarios, apply/reset, cohort cutoffs, stress-grid invalidation, validation errors and both downloads were exercised. A second Streamlit session started at base while the first retained Balanced/$1.25m. See [browser evidence](browser-validation.md) for values, run IDs and screenshots.

The first hosted review exposed three presentation issues: dollar captions rendered as inline mathematics, stress-grid percentages used a numeric axis, and a validation message showed an input identifier with duplicate punctuation. Commit `01a89be` corrects those displays. After the hosting reboot, the actual app showed dollar amounts, the four percentage categories and the corrected error. The financial engine and model version were unchanged.

Commit `8572cec` adds policy summaries above the profit chart and detailed table. After refreshing the host, base and $1.25m capital cases showed the corresponding cash limits and equity gaps alongside each policy's profit. Draft edits retained the applied values until Run. Reset returned the summaries to base.

Guided examples added at `6b5fedd` and simplified at `8959dae` let a reviewer load base, capital and default stress cases immediately. All three applied the expected runs in the hosted app. Custom runs still used the edited inputs; examples replaced old assumptions, restored the cohort cutoff and cleared the generated stress grid. The final buttons and their instructions were captured after the hosting refresh.

Commit `e87a74d` adds the applied-scenario decision brief and preview. The hosted base, capital and default-stress Markdown downloads matched locally regenerated reports exactly; the capital brief used applied inputs during a draft equity edit. Its embedded manifest reproduced the same decision and run through the CLI. The model and its version were unchanged. See the browser evidence for report hashes and captures.

## Operating and release notes

Use the [official deployment workflow](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) to manage the app. Keep Python 3.12, the selected source branch and `app.py` consistent with this repository. After changing code, verify the resulting behavior in the live app; a GitHub commit alone does not establish that the hosting process refreshed.

The first startup log recorded approximately 11 seconds from repository preparation to the listening server. This is a host log interval, **not** a measured viewer cold start. Viewer load timing, hibernation/wake behavior and multi-user capacity have not been measured.

Mobile layout, isolated anonymous access, comprehensive accessibility/network checks and a continuous interactive walkthrough recording remain open; a captioned screenshot tour is available in the [release checklist](release-checklist.md).

The heading presentation was checked live at `10afcbacd0cda17ba0d3631f1a7dc64f44c024a5` after a hosting reboot. All five tab outlines and the nested decision preview were inspected; capital activation, preview expansion and brief download also worked with the keyboard. See the heading follow-up in [browser-validation.md](browser-validation.md).
