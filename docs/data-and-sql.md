# Data dictionary and SQL walkthrough

## Synthetic demand

`data/applications.csv` is the one versioned base population. It contains no personal identifiers or real borrower records. The seed is 2262026; generator behavior is documented in `data/manifest.json`.

| Field | Type | Definition / check |
| --- | --- | --- |
| `application_id` | Text | Unique fictional `syn-000001` style key; nonempty |
| `month` | Integer | Application/origination month, 0–23; month 0 is October 2026 |
| `risk_band` | Text | Illustrative `low`, `medium`, or `high`; no trained score |
| `principal_cents` | Integer | Requested USD principal in cents; synthetic generator uses $500–$2,500 |

Generation fixes exactly 4,500 low, 3,500 medium and 2,000 high applications. It shuffles band membership and a near-uniform monthly allocation with Python 3.12 `random.Random`. Requested principal is sampled uniformly over inclusive integer cents 50,000–250,000. Months 0–15 contain 417 applications each; 16–23 contain 416 each. There is no empirical relationship between synthetic band, time and principal.

Scenario demand applies `(1 + growth)^month` to the fixed application counts and principal aggregates. This changes **expected weighted volume**. It does not regenerate the population. Base counts, scenario expected counts, and expected surviving/defaulted counts are separate concepts.

The dataset content hash includes its version and canonical rows. Load validation checks duplicates, missing fields, integer cents, positive principal, allowed bands and valid months before any SQL joins. Database primary keys also prevent duplicate applications and duplicate policy-band mappings.

## SQL responsibilities

The database is SQLite in memory, created and closed inside each analytics call. No connection or mutable scenario table is shared across visitors.

`lending_simulator/queries/policy_population.sql` uses a CTE, a left join, and conditional aggregation. Each policy gets the same application denominator. Counting application keys handles empty populations; `NULLIF` preserves undefined rates. Approved ticket size divides approved principal by approved count, not total applicants.

`cohort_inputs.sql` binds `:policy` and groups by application month and risk band. Count and integer-cent principal totals feed the financial model. Decimal weights are applied after SQL, avoiding binary-float aggregation in financial inputs.

Policy-band relationships are unique. The approved populations nest: low ⊆ low+medium ⊆ all. Joining to outcomes or another table would require verifying its key grain before aggregation; a one-to-many join can multiply both counts and principal.

Run the actual queries through Python:

```python
from pathlib import Path
from decimal import Decimal
from lending_simulator.data import load_dataset
from lending_simulator.analytics import policy_population, aggregate_for_model

dataset = load_dataset(Path("data/applications.csv"))
print(policy_population(dataset))
cohorts, expected_applications = aggregate_for_model(dataset, "balanced", Decimal("0.05"))
print(cohorts[0], expected_applications)
```

## Result grain and units

| Output | Grain | Interpretation |
| --- | --- | --- |
| Monthly results | Policy/run × calendar month | Expected flows and opening/ending balances |
| Cohort results | Policy/run × origination month × risk band × loan age | Cohort repayment, default, recovery and principal |
| Summary | Policy/run | Full-runoff totals, separate 24-month operating profit, minimum cash and ratios |
| Manifest | Run | Dataset/model identity, exact assumptions, horizon and reconciliation results |

USD flow values are separate from stocks; never sum month-end debt or cash to get a financial total. Approval and loss ratios use their matching denominators. Do not average band ratios without exposure weights. Undefined denominators are unavailable, not zero. Heatmaps omit future ages at the selected cutoff.

CSV packages preserve exact Decimal strings. `units.json` defines monthly/cohort fields; the manifest defines currency, time indices, scope and classification. Workbooks retain numeric snapshots for convenient inspection. Only their small benchmark sheets are live calculation schedules.

## Historical records

Zero historical outcome rows were accepted. `lending_simulator/evidence/sources.json` records the sources and fitness decision, separate from the synthetic dataset. No invented historical SQL, fitted probabilities, evaluation split, observed loss curve, or prediction-accuracy statistic is included.
