# Hosted review deployment

**Live URL:** https://rishabb-lending-simulator.streamlit.app/

The Streamlit Community Cloud review build was deployed and inspected on **October 7, 2026**. The assigned URL rendered the application, and the hosting Share dialog showed **Make this app public** checked. An isolated anonymous browser session has not been tested.

| Setting | Observed deployment |
| --- | --- |
| Repository | `rishabbshankar226/Lending-Profability-Risk-Simulator` |
| Branch | `feature/lending-simulator` |
| Entrypoint | `app.py` |
| Python | 3.12 selected; host log reported 3.12.15 |
| Dependencies | Committed `requirements.txt` |
| Data | Preloaded synthetic CSV and matching manifest |
| Secrets | None required |
| Application code tested | `01a89be7693a3154627318e6e95f0bb253c43694` |

[Draft PR #1](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/pull/1) is open and unmerged. The app runs from the review branch; `main` is not the implementation branch. A future approved merge must be followed by a deliberate hosting branch update.

## Verified behavior

Desktop Chrome rendered all five views. Capital, default and funding scenarios, apply/reset, cohort cutoffs, stress-grid invalidation, validation errors and both downloads were exercised. A second Streamlit session started at base while the first retained Balanced/$1.25m. See [browser evidence](browser-validation.md) for values, run IDs and screenshots.

The first hosted review exposed three presentation issues: dollar captions rendered as inline mathematics, stress-grid percentages used a numeric axis, and a validation message showed an input identifier with duplicate punctuation. Commit `01a89be` corrects those displays. After the hosting reboot, the actual app showed dollar amounts, the four percentage categories and the corrected error. The financial engine and model version were unchanged.

## Operating and release notes

Use the [official deployment workflow](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) to manage the app. Keep Python 3.12, the selected source branch and `app.py` consistent with this repository. After changing code, verify the resulting behavior in the live app; a GitHub commit alone does not establish that the hosting process refreshed.

The first startup log recorded approximately 11 seconds from repository preparation to the listening server. This is a host log interval, **not** a measured viewer cold start. Viewer load timing, hibernation/wake behavior and multi-user capacity have not been measured.

Mobile layout, isolated anonymous access, comprehensive accessibility/network checks and the walkthrough recording remain open in the [release checklist](release-checklist.md).
