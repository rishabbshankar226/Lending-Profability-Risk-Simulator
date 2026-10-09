-- One row per approval policy. The left join retains empty populations.
-- Count keys rather than COUNT(*) so an empty application table counts as zero.
WITH policy_totals AS (
    SELECT p.policy,
           COUNT(a.application_id) AS application_count,
           SUM(CASE WHEN b.risk_band IS NOT NULL THEN 1 ELSE 0 END) AS approved_count,
           SUM(CASE WHEN b.risk_band IS NOT NULL THEN a.principal_cents ELSE 0 END)
               AS approved_principal_cents
    FROM policies AS p
    LEFT JOIN applications AS a ON 1 = 1
    LEFT JOIN policy_bands AS b
        ON b.policy = p.policy AND b.risk_band = a.risk_band
    GROUP BY p.policy
)
SELECT policy, application_count, approved_count, approved_principal_cents,
       1.0 * approved_count / NULLIF(application_count, 0) AS approval_rate,
       1.0 * approved_principal_cents / NULLIF(approved_count, 0) / 100.0 AS average_ticket_usd
FROM policy_totals
ORDER BY CASE policy WHEN 'conservative' THEN 0 WHEN 'balanced' THEN 1 ELSE 2 END;
