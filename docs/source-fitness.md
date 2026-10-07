# Historical evidence decision

**Reviewed October 7, 2026. Evidence achieved: contextual comparison only.** The simulator is uncalibrated. No borrower-level or cohort-level historical validation was completed.

| Candidate | Fit / access finding | Decision |
| --- | --- | --- |
| [Prosper September 2026 prospectus](https://www.sec.gov/Archives/edgar/data/1416265/000141626526000038/prospectus-september2026.htm) | Published term/rating/vintage loss charts; 24/36/48/60-month products differ from this 12-month product. | Context only; no chart values digitized or fitted. |
| [Prosper data access](https://help.prosper.com/hc/en-us/articles/210013083-Where-can-I-download-data-about-loans-through-Prosper) | Account access for loan-level data; agreement required for the monthly file. | No access or redistribution rights obtained. |
| [UCI credit-card default](https://archive.ics.uci.edu/dataset/350/default) | Taiwan revolving credit and 2005 payment history differ from the product and horizon. | Excluded from calibration. |

These decisions follow the approved source gate, rather than substituting unrelated observations for missing evidence. Numerical PD, recovery, pricing, demand, costs and constraints remain illustrative. Financial benchmark verification establishes calculation behavior under inputs; it does not establish predictive accuracy.

## What a future empirical version needs

Before accepting outcome rows, verify original-publisher provenance and reuse rights, currency/geography, installment product and term, origination population, observation dates, unique loan/cohort keys, exposure and recovery fields, and extraction completeness. A matched licensed dataset may be useful without being suitable for public redistribution.

Specify the default/delinquency/charge-off outcome and denominator before fitting. A principal-loss ratio is not a default probability: exposure at default and recoveries differ. Preserve loan age and incomplete outcomes. Do not select only fully paid and charged-off records from an immature cohort.

Lock an earlier-origination fitting period and a later evaluation period before examining held-out outcomes. Use consistently mature cohorts or a defensible censoring method. Record sample sizes, exposure weighting, observed-versus-expected errors and uncertainty at the supported grain. Keep future collections, recovery and final status out of origination-time predictors.

Funded-loan records describe an already selected population. Without rejected-applicant outcomes, they do not prove that expanding approvals would cause profitable growth. A material change to product term or model basis requires another specification review.
