-- Application-month/risk-band grain, used directly by the financial engine.
-- Integer cents are aggregated before Decimal demand weights are applied.
-- :policy is a bound parameter, never interpolated SQL.
SELECT a.month, a.risk_band, COUNT(*) AS application_count,
       SUM(a.principal_cents) AS principal_cents
FROM applications AS a
JOIN policy_bands AS b ON b.risk_band = a.risk_band AND b.policy = :policy
GROUP BY a.month, a.risk_band
ORDER BY a.month, a.risk_band;
