# Interview and demo walkthrough

## 90-second demonstration script

**0–20 seconds.** “I built a lending profitability and risk simulator to connect approvals, loan losses, funding and cash. The applicant population is synthetic, and all risk inputs are illustrative. It compares a 24-month origination plan through complete repayment and recovery runoff.” Show Overview.

**20–40 seconds.** Open Strategy comparison. “Broadening approvals increases modeled operating profit from about $48k to $396k, but the aggressive policy reaches a $1.49m cash deficit. With the selected cash floor, conservative is the only eligible policy. The recommendation is calculated, not hard-coded.”

**40–60 seconds.** Change starting cash to $1.25m and run. “Additional equity makes balanced feasible and changes the recommendation. Profit stays unchanged because I have not modeled an equity financing cost. Capital and operating economics are different questions.”

**60–75 seconds.** Reset; set default stress to 2× and run. “There is no profitable eligible policy here. The tool reports the limitation instead of forcing a growth recommendation.”

**75–90 seconds.** Show Methodology and download a workbook. “The engine reconciles loans, debt, cash, cohorts and simplified equity. The workbook has independent amortization/default examples. Historical data did not fit the product, so I make no prediction-accuracy claim.”

This is a recording script. A video and live dashboard screenshots remain pending browser/deployment access.

## Financial questions to practice

1. Why are principal repayments cash but not revenue? Explain the loan asset reducing as cash increases.
2. Why is lifetime PD different from loss/original principal? Defaults happen on amortizing outstanding exposure, followed by recoveries.
3. Why does a charge-off not create another cash outflow? The cash was advanced at origination; default removes future collections and the asset.
4. Why can profitable growth need more capital? New advances occur before repayment, and the debt facility/collateral limit caps funding.
5. Why does the runoff result differ from the 24-month result? Late cohorts remain unfinished and company overhead continues.
6. What would reverse the recommendation? Demonstrate changes to capital, funding cost, defaults, fees or operating cost; identify binding limits.

## SQL checkpoint

Read `policy_population.sql`. Explain the left join, conditional approval sum, `COUNT(application_id)`, and `NULLIF`. Predict counts for one low, one medium and one high application: 1/3, 2/3 and 3/3 approvals. Then run the small SQL test to verify it.

Read `cohort_inputs.sql`. Explain why joining to a nonunique policy-band mapping or loan outcome table could multiply principal. Explain why growth weights are applied to the same dataset rather than newly sampled applicants.

## Python checkpoint

Trace `Assumptions → aggregate_for_model → run_model → select_strategy → presentation`. Follow one $1,200 zero-interest loan through 12 $100 principal payments. Follow a $900 month-1 default to a $225 month-4 recovery. Show the tests for both.

Change funding cost using `dataclasses.replace(Assumptions(), funding_rate=Decimal("0.12"))`, rerun the comparison and explain the profit change. Show which assumptions enter the run ID and why equal numeric inputs share an identity.

## Historical-evidence checkpoint

Explain why a longer-term loss curve or short credit-card default target cannot calibrate this product's lifetime PD. Describe how you would choose mature cohorts, lock a chronological evaluation split, prevent leakage, handle censored loans and limit conclusions from funded-only data. State plainly that those empirical steps have not been completed here.

## Portfolio wording

Use this only after you can explain the financial and SQL/Python checkpoints:

“Built a Python/SQL lending decision simulator comparing approval policies across profitability, credit losses and liquidity, with a Streamlit dashboard, reconciled financial schedules, and reproducible scenario exports.”

Do not claim actual underwriting deployment, prediction accuracy, real business savings, or independent technical mastery from having working software. Add a live-demo claim only after public access has been verified.
