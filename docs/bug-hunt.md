# Bug-hunt plan and evidence

## Scope and baseline

Audit starts from `main` at `baeda884355734f534babd2bc73ab7018742569f`, in the isolated `fix/comprehensive-bug-hunt` branch. No repository or ancestor `AGENTS.md`, `CONTEXT.md`, or ADR was found. The authoritative contracts are `docs/model-spec.md`, the public model types, documented dashboard behavior, and CI in `.github/workflows/checks.yml`.

The product is a synthetic expected-value lending simulator, not a calibrated underwriting model. The audit preserves its fixed 12-month loan product, monthly event order, policy definitions, financial meaning, exact decision thresholds, and distinction between applied and draft inputs. A modeling limitation is not automatically a software defect.

## Ordered work

1. **Establish a baseline.** Install the committed Python 3.12 requirements in an isolated environment. Run the existing pytest suite, compilation, and the base-case CLI. Record the starting counts, run identities, exact financial outputs, and any existing failures.
2. **Inspect every execution boundary.** Read the financial engine and input types, CSV/manifest validation, SQL analytics, decision selection and stress calculations, presentation and exports, CLI, Streamlit state/cache transitions, tests, and deployment configuration.
3. **Construct deterministic probes.** Exercise finite/nonfinite and boundary inputs; zero and complete default/recovery; zero rates and funding; small/empty portfolios; growth and recovery timing; exact loss/cash boundaries; schema/content changes; applied/draft/invalid/reset sequences; export and manifest roundtrips. Use fixed seeds for broader input combinations. Assert independent financial identities rather than copy implementation formulas into tests.
4. **Triage demonstrated failures.** Record the smallest input/interaction, expected contract, observed symptom, affected path, and impact. Rank wrong financial decisions/data corruption before crashes, stale state, misleading exports, and presentation defects. Distinguish confirmed defects from design limitations and unverified suspicions.
5. **Patch one root cause at a time.** Add a regression test at the actual failing boundary and observe it fail before changing production code. Use the existing test conventions. Prefer small changes over unrelated refactoring or dependency upgrades. A complex defect may use a separate test author under the testing skill's workflow.
6. **Verify and publish for review.** Run the complete suite and CI-equivalent commands after fixes; reproduce CLI results from exported manifests; inspect workbook/CSV/report consistency; perform available browser checks. Review the diff for numerical drift, debug artifacts, leaked data, and accidental scope expansion. Commit and publish a branch/PR with evidence and explicit remaining limits.

## Coverage matrix

| Area | Main files | Evidence required |
| --- | --- | --- |
| Input/numerical contracts | `types.py`, `model.py` | Rejection of unusable inputs; amortization, survival, cash/debt/equity identities; common runoff |
| Dataset and provenance | `data.py`, `data/manifest.json` | Exact cents, uniqueness, field domains, declared identity matching actual content |
| Policy population and cohorts | `analytics.py`, `queries/*.sql` | Independent counts/denominators, approval nesting, weights, empty inputs |
| Recommendations and stress | `decisions.py` | Exact eligibility/tie rules, no profitable/eligible policy, consistent assumptions |
| Tables/charts and downloads | `presentation.py`, `exports.py` | Undefined values, unit labels, roundtrip identity, workbook formulas and exact CSV values |
| CLI | `cli.py` | Base invocation, malformed manifest, saved-input replay, packaged/local entrypoints |
| Dashboard | `app.py`, `tests/test_app.py` | Startup errors, state isolation, draft/apply/reset/example transitions, data refresh, download identity |
| Runtime/release | requirements, workflow, Streamlit config, deployment docs | Pinned setup succeeds; real HTTP startup; local/headless browser checks if available; deployed branch distinction |

## Plan audit before implementation

- **Coverage:** All production modules and their public boundaries are assigned a pass; financial logic has independent invariants in addition to example snapshots.
- **False positives:** A passing baseline does not prove absence of bugs. Each proposed behavioral fix needs an observed failure against a stated contract. Deliberate synthetic assumptions, negative diagnostic cash, and continued common-horizon overhead are preserved.
- **Numerical risk:** Preserve Decimal precision and canonical identities. If a fix legitimately changes modeled outputs, document why and version the model/identity accordingly; do not silently refresh expected values.
- **State risk:** Exercise invalid and draft edits after successful runs, multiple visitor sessions, and warm-cache data changes rather than testing only startup.
- **Export risk:** Validate the actual public export path and replay its manifest; include non-base inputs and empty portfolios.
- **Environment risk:** Separate infrastructure limitations from application defects. AppTest and HTTP checks are not visual browser verification. The documented hosted branch differs from `main`, so this audit cannot claim the live app has received new code merely because a PR exists.
- **Change control:** Work stays on an isolated branch; the initial plan is completed before production patches. No hosting change, main merge, or unrelated feature work is needed to conduct the requested hunt.
- **Completion:** All confirmed defects in this pass are fixed or given a concrete blocked reason; regression checks, full-suite results, reviewed diff, and PR evidence are recorded. Unverified coverage remains labeled.

The plan passes this review. Execution evidence is recorded below as the audit proceeds.

## Execution evidence

### Baseline and triage

The untouched checkout passed **83 tests in 46.34 seconds**, compilation and the base CLI. Python 3.12.14 used the exact committed dependencies in an isolated environment. Every production module, SQL query, state boundary and release configuration in the matrix was inspected before fixes. Deterministic probes then exposed failures that the passing examples did not cover.

Each defect below was reproduced before its production patch. The initial focused regression run had 26 failures and two passes; additional boundary and AppTest probes reproduced the full-recovery, custom-seed, metadata and oversized-input failures. Financial errors received priority over export/state crashes. No suspected issue was patched solely because a test was absent.

| Priority | Confirmed defect / trigger | Patch and regression evidence |
| --- | --- | --- |
| High | Tiny positive interest cancels the annuity denominator, producing incorrect payments or division by zero | Evaluate the equivalent discounted-payment sum; four small-rate cases independently recover principal from payment present values |
| High | Tiny lifetime PD loses significant digits or becomes zero | Add temporary guard precision through hazard subtractions; four cases reconcile expected default counts to lifetime PD |
| High | 100% recovery leaves signed rounding residue and can falsely fail an exact zero-loss cap | Derive full-runoff net loss from gross charge-offs × unrecovered fraction; three lag/PD cases and seeded scenarios require exact zero |
| High | A workbook silently compares policies calculated from different applied assumptions | Validate the shared population, assumptions and horizon before export; a mixed base/capital comparison must fail |
| High | CLI replay accepts a wrong model version, run ID, policy or reporting metadata | Validate supplied identity/invariants before writing exports; eight corrupted manifest cases must fail, while equivalent Decimal input spellings replay |
| Medium | A partial-band dataset produces pandas NaN for unfunded policy ratios and crashes workbook generation/downloads | Normalize unavailable numeric values to `n.a.`; two workbook cases, high-only AppTest startup/refresh and actual browser downloads pass |
| Medium | Empty-portfolio stress results contain the string `None`, which cannot be plotted as a number | Preserve null ratios; AppTest and real browser stress generation pass with 20 ineligible cells |
| Medium | Non-object JSON or malformed nested assumptions raises an uncaught exception | Reject incompatible shapes with a user-facing ValueError/CLI exit 2; seven CLI and four direct parser cases pass |
| Medium | Custom-seed manifests replay under the default seed and lose declared provenance | Load the saved seed and verify supplied dataset metadata; non-base, growing-demand, lag-12 replay preserves selected run and provenance |
| Medium | CSV records with extra fields are silently truncated | Reject missing/extra record fields before parsing; two extra-field cases fail clearly |
| Medium | Enormous finite USD assumptions overflow chart/workbook values after replacing successful applied state | Bound six USD fields to $1 trillion; 12 direct boundary cases and a warm-dashboard overflow case verify rejection and retention of previous results/downloads |

### Validation after patches

- **Full suite:** 136 passed in 86.29 seconds, with no skips or disabled tests. The 53 added cases comprise 48 focused parametrized regressions, four dashboard regressions and one seeded invariant test.
- **Broader financial coverage:** 160 deterministic input combinations × three policies = 480 model runs. Independent assertions cover lifetime principal repayment/charge-offs, ending cash versus initial equity plus profit, monthly versus lifetime losses, approval/loss ranges and exact full-recovery zero. Boundary combinations include empty/tiny populations, zero/complete default, recovery lags 0–12, growth −99% to 100%, and zero/max rate/funding settings.
- **CLI/export:** Base CLI, malformed manifest rejection and non-base/custom-seed manifest replay pass. Actual browser ZIP, XLSX and Markdown downloads match the applied inputs and run; draft/invalid edits retain them. Undefined ratios stay unavailable rather than plausible zeros. Compilation passes.
- **Real browser:** Isolated headless Chromium 153, local Streamlit subprocesses, desktop 1440 × 1000 and mobile-width 390 × 844. All five desktop tabs, capital/reset, draft/invalid retention, independent visitor state, Enter activation, empty/high-only startup, workbook download and stress-grid generation pass. No console errors, warnings or failed requests occurred during tested cases. See [the scoped report](bug-hunt-browser.json).
- **Audit workbook:** Imported the existing nine-sheet file and refreshed only model snapshots/identity. Zero-interest and 100%-recovery formula edits recalculate and are restored. Final scan finds no formula errors. Changed ranges were rendered; the saved workbook preserves formulas, styles, data validation, dimensions and panes. Benchmark inputs and Sources stay intact. Native Excel is not tested.
- **Numerical compatibility:** Version bumped to **0.1.1** because financial precision legitimately changed. Dataset manifest/bytes, policy definitions, rounded base summaries and recommendation stay unchanged. Largest exact base-summary difference is $3e−27. Saved base comparison, three briefs and audit workbook were refreshed to the new identities.

| Current saved example | Selected policy | Version 0.1.1 run |
| --- | --- | --- |
| Base | Conservative | `438a13c9e03c52a9` |
| Starting equity $1.25m | Balanced | `89fea7fd94029201` |
| Lifetime default stress 2× | Conservative | `153c7d2b57999d98` |

### Final planning and scope review

Every coverage row received a code review and appropriate baseline/regression evidence. Tests assert financial identities and public boundary behavior; they do not simply mirror the changed formulas. New production code is limited to nine existing Python/config files, with no application dependency or UI redesign. No dataset generation, historical calibration, accounting convention, approval policy, negative-cash diagnostic or exact decision threshold was changed.

The new USD bound is an intentional input-contract restriction, documented in the model specification. CLI rejects old-version manifests because new-version runs cannot truthfully reproduce their identity; extracting their assumptions allows a new evaluation. Historical screenshots, tour, performance results and hosted evidence retain their old versions/commits rather than being relabeled.

The audit branch is prepared for pull-request review. No `main` merge or hosting change is part of this pass. The live `feature/lending-simulator` build does not contain these patches. Remaining unverified areas are hosted anonymous/mobile access, physical-device and full accessibility behavior, native Excel, hosting/load performance, and real-data calibration. They are coverage limits, not asserted defects. All confirmed defects found in this pass have patches and regression evidence.
