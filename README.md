# Lending Profitability & Risk Simulator

Compare how expanding loan approvals changes credit losses, profit, debt use, and cash. A standalone portfolio project for fintech finance and credit/risk analysis, separate from the Financial Underwriting Tool.

The app models a hypothetical lender retaining 12-month merchant-financed installment loans. Its 10,000 applications and risk assumptions are **synthetic and illustrative**. Historical sources provide context only; this is an **uncalibrated expected-value simulator**.

**Live dashboard:** [Open the dashboard](https://rishabb-lending-simulator.streamlit.app/) · **Source code:** [main](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/tree/main) · **Merge history:** [PR #1](https://github.com/rishabbshankar226/Lending-Profability-Risk-Simulator/pull/1)

**UI workbench candidate:** this branch adds the redesigned interface. Read the [candidate review and acceptance gates](docs/ui-workbench-review.md). The public dashboard and existing media show the earlier `feature/lending-simulator` build; candidate browser acceptance and deployment remain pending.

**Start here:** [Two-minute reviewer guide](docs/reviewer-guide.md) · [Application and interview notes](docs/interview-notes.md)

**Quick visual tour:** [90-second captioned screenshot video](docs/tour/lending-simulator-tour.mp4) · [Transcript and source captures](docs/tour/README.md). Six real dashboard screenshots, assembled with captions; no audio or continuous interaction recording.

![Live guided capital example](docs/screenshots/guided-capital.jpg)

## The decision

Choose the highest full-runoff management operating profit among three policies that meet a net principal loss cap and minimum month-end cash floor. Defaults: 5% net loss and $50,000 cash. No eligible or profitable policy means no profitable recommendation.

With $500,000 starting equity and a $2m facility, the base case demonstrates why profit alone is insufficient:

| Policy | Approval rate | Full-runoff operating profit | Net principal loss | Minimum cash | Eligible |
| --- | ---: | ---: | ---: | ---: | --- |
| Conservative | 45% | $48,133 | 0.84% | $147,450 | Yes |
| Balanced | 80% | $294,468 | 1.58% | −$696,143 | No: cash floor |
| Aggressive | 100% | $396,446 | 2.29% | −$1,485,855 | No: cash floor |

These are conditional modeled results, not observed lender performance. See the [business memo](docs/business-memo.md) and [saved base-case manifest](docs/base-case.json).

## Run locally

Use Python **3.12**. Direct dependency versions were installed and smoke-tested together.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```

On Windows, activate with `.venv\Scripts\activate`. Open the localhost URL printed by Streamlit. The app preloads the dataset and needs no upload, API key, or login.

```bash
python -m pytest
python -m lending_simulator.cli --output artifacts/base-case
python -m scripts.generate_dataset
```

The CLI produces three scenario workbooks, exact-value CSV packages, comparison metadata, and a workbook specification. Regeneration reproduces the committed application CSV and content hash.

The server test starts Streamlit on a temporary local port, checks HTTP health and the frontend document, then stops it. This verifies startup; it does not inspect browser rendering or interactions.

To reproduce downloaded inputs, unzip `manifest.json` and use:

```bash
python -m lending_simulator.cli --assumptions path/to/manifest.json --output artifacts/reproduced
```

## Explore the dashboard

Start with the decision summary and three primary metrics. **Recommended policy** compares all three policies; **Viewed policy** immediately selects the applied portfolio used by the metrics, charts and exports. The summary shows full-runoff operating profit, the cash cushion or shortfall relative to the floor, and credit-loss headroom or excess in percentage points. Actual minimum cash, loss ratio and both limits remain visible. **Applied inputs** in the toolbar retains the last successful run while you edit the sidebar.

Then explore the one-click examples:

| Example | Selected policy | Change from base |
| --- | --- | --- |
| Base case | Conservative | Restore $500,000 equity and all base assumptions |
| More capital · $1.25m | Balanced | Set starting equity to $1.25m |
| Higher defaults · 2× | Conservative | Double lifetime default assumptions |

Each example replaces all inputs, runs immediately, restores the First 24 months cohort cutoff and clears the old stress grid. It preserves the active view and a pinned baseline. Recommendations still compare all three policies using the model's rules.

1. **Overview:** separate profit and liquidity timelines, dated cash-floor/minimum references, funded volume, contribution and a reconciled profit bridge.
2. **Policies:** equal policy summaries, profit/cash-margin comparisons and a pinned applied baseline. Different runoff lengths use a common first-24-month profit delta.
3. **Cohorts:** projected loss by origination month and loan age; blank future values and a shared scale across policies/cutoffs.
4. **Funding & stress:** cash/debt, additional equity and a manually requested 20-case selected-policy grid. Inspect a case and stage its inputs before Run.
5. **Methodology:** timing, assumptions, sources, financial checks, SQL, and run manifest.

Committed sidebar edits show **Unapplied changes** and an input review; **Run scenario** applies them. **Restore applied inputs** discards the draft without running projections. Navigation and policy selection preserve drafts. **Reset to base** restores all assumptions, Conservative, Overview and the cohort cutoff, clearing stress and the pinned baseline. Only the selected analytical view is built on each rerun.

Open **Export** for **Decision brief**, **Audit workbook** or **CSV results + manifest**. Each format is prepared only when requested and captures the viewed applied run; draft edits are not exported. **Preview decision brief** prepares only that report. Workbook portfolio sheets are saved snapshots; independent loan/recovery benchmarks contain editable formulas.

## How it works

| Layer | Files | Responsibility |
| --- | --- | --- |
| Dataset | `data.py`, `data/` | Immutable, validated seeded demand and provenance |
| SQL analytics | `analytics.py`, `queries/*.sql` | Correct policy denominators and cohort inputs in integer cents |
| Financial model | `model.py`, `types.py` | Pure expected-value repayment, defaults, recoveries, funding and cash |
| Decisions | `decisions.py` | Exact eligibility, ranking, ties, stress cases and honest empty/loss states |
| Presentation and exports | `presentation.py`, `exports.py` | Model tables, exact packages and reproducible reports |
| Workbench | `ui/`, `app.py` | Draft/apply state, shared formatting, selected views, charts and deferred exports |

Finance uses 34-digit Decimal arithmetic with a $1e−16 internal reconciliation tolerance. Chart values and workbook snapshots use ordinary numeric display precision; CSVs retain exact Decimal strings. The operating view has 24 origination months; the default comparison runs 39 months through complete recovery runoff. No charge-off is subtracted as a second cash payment.

## Review and learn

- [Two-minute reviewer guide for finance and credit/risk roles](docs/reviewer-guide.md)
- [Project pitch, resume drafts and interview answer checkpoints](docs/interview-notes.md)
- [Model specification and assumptions](docs/model-spec.md)
- [Dataset dictionary and SQL walkthrough](docs/data-and-sql.md)
- [Historical source-fitness decision](docs/source-fitness.md)
- [Validation and measured limitations](docs/validation.md)
- [UI workbench review, state contract and pending visual acceptance](docs/ui-workbench-review.md)
- [Base-case audit workbook](docs/audit-workbook.xlsx)
- Decision brief examples: [base](docs/base-decision-brief.md), [capital](docs/capital-decision-brief.md), [default stress](docs/default-stress-decision-brief.md)
- [Interview and 90-second demo walkthrough](docs/walkthrough.md)
- [Hosted review deployment](docs/deployment.md)
- [Live browser results and screenshots](docs/browser-validation.md)
- [Browser and release checklist](docs/release-checklist.md)

All 118 automated model, application-state, export, and HTTP startup checks pass. Workbench coverage includes draft preservation/restoration, immediate policy selection, hidden-view navigation, immutable baseline comparison, exact stress staging/markers, undefined values and deferred format generation. The financial engine, model version and example run identities are unchanged; three saved decision briefs match exact regeneration. [Separate operation measurements](docs/workbench-performance.json) cover local server code and AppTest, not browser or hosting latency.

The cloud browser cannot reach the local candidate. Desktop/mobile rendering, keyboard/focus, actual deferred downloads and before/after captures remain required before releasing this redesign. The [candidate review](docs/ui-workbench-review.md) records the blocked visual gate and remaining acceptance cases.

The earlier hosted desktop build was exercised across all five tabs, scenario apply/reset, capital and stress cases, validation errors, cohort cutoffs, and downloads. Guided examples were checked for the correct applied runs, replacement of draft/advanced inputs, stress-grid clearing and keyboard activation. The three actual decision-brief downloads matched local regeneration exactly; the capital brief retained applied inputs during a draft edit, and its saved manifest reproduced the same CLI decision and run. The comparison summaries were verified at base and $1.25m starting equity. See the browser evidence for tested commits and run IDs. Missing or invalid base data stops the dashboard with a clear error; validated replacements refresh the applied scenario and exports.

PR #1 is merged into `main`, with passing GitHub checks. The live demo still uses `feature/lending-simulator`; that branch is retained for hosting and does not yet include the decision-panel upgrade. The existing screenshots and tour show that earlier build. Anonymous-session and mobile testing, a full accessibility/network audit, hosting load measurements, and a continuous interactive walkthrough recording remain pending. The hosting public setting was observed, but an isolated anonymous browser was unavailable.
