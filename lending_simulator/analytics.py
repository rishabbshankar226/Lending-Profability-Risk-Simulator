"""Useful SQLite aggregations; a private short-lived database for each call."""

from contextlib import contextmanager
from decimal import Decimal, localcontext
from importlib.resources import files
import sqlite3

from lending_simulator.data import Dataset
from lending_simulator.types import CohortInput, POLICIES

D = Decimal


def query_text(name: str) -> str:
    if name not in ("policy_population", "cohort_inputs"):
        raise ValueError("Unknown query.")
    return files("lending_simulator").joinpath("queries", f"{name}.sql").read_text()


@contextmanager
def _database(dataset: Dataset):
    dataset.validate()
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    try:
        db.executescript("""
            CREATE TABLE applications (
                application_id TEXT PRIMARY KEY, month INTEGER NOT NULL,
                risk_band TEXT NOT NULL, principal_cents INTEGER NOT NULL CHECK(principal_cents > 0)
            );
            CREATE TABLE policies (policy TEXT PRIMARY KEY);
            CREATE TABLE policy_bands (
                policy TEXT NOT NULL, risk_band TEXT NOT NULL, PRIMARY KEY(policy, risk_band)
            );
        """)
        db.executemany("INSERT INTO applications VALUES (?, ?, ?, ?)",
                       ((a.application_id, a.month, a.risk_band, a.principal_cents) for a in dataset.applications))
        db.executemany("INSERT INTO policies VALUES (?)", ((p,) for p in POLICIES))
        db.executemany("INSERT INTO policy_bands VALUES (?, ?)",
                       ((p, band) for p, bands in POLICIES.items() for band in bands))
        yield db
    finally:
        db.close()


def policy_population(dataset: Dataset) -> tuple[dict, ...]:
    """Raw base counts, without projected demand weights."""
    with _database(dataset) as db:
        return tuple(dict(row) for row in db.execute(query_text("policy_population")))


def aggregate_for_model(dataset: Dataset, policy: str, growth: Decimal) -> tuple[tuple[CohortInput, ...], Decimal]:
    if policy not in POLICIES:
        raise ValueError("Unknown policy.")
    if not isinstance(growth, Decimal) or not growth.is_finite() or not D(-1) < growth <= 1:
        raise ValueError("Growth must be a finite Decimal greater than -1 and at most 1.")
    with _database(dataset) as db:
        approved = tuple(db.execute(query_text("cohort_inputs"), {"policy": policy}))
        demand = tuple(db.execute("SELECT month, COUNT(*) AS n FROM applications GROUP BY month"))
    with localcontext() as ctx:
        ctx.prec = 34
        weights = {month: (1 + growth) ** month for month in range(24)}
        cohorts = tuple(CohortInput(r["month"], r["risk_band"], D(r["application_count"]) * weights[r["month"]],
                                   D(r["principal_cents"]) / 100 * weights[r["month"]]) for r in approved)
        denominator = sum((D(r["n"]) * weights[r["month"]] for r in demand), D(0))
    return cohorts, denominator
