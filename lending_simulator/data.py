"""Versioned synthetic demand. All rows are fictional and contain no PII."""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from random import Random

from lending_simulator.types import BANDS, ORIGINATION_MONTHS, stable_hash

DATASET_VERSION = "synthetic-applications-v1"
DEFAULT_SEED = 2262026
CSV_FIELDS = ("application_id", "month", "risk_band", "principal_cents")


@dataclass(frozen=True)
class Application:
    application_id: str
    month: int
    risk_band: str
    principal_cents: int


@dataclass(frozen=True)
class Dataset:
    applications: tuple[Application, ...]
    seed: int
    version: str = DATASET_VERSION
    dataset_hash: str = field(init=False)

    def __post_init__(self):
        self.validate()
        content = [(a.application_id, a.month, a.risk_band, a.principal_cents) for a in self.applications]
        object.__setattr__(self, "dataset_hash", stable_hash({"version": self.version, "rows": content}))

    def validate(self):
        if type(self.seed) is not int or not isinstance(self.applications, tuple):
            raise ValueError("Dataset requires an integer seed and an immutable tuple of applications.")
        seen = set()
        for a in self.applications:
            if not isinstance(a.application_id, str) or not a.application_id.strip():
                raise ValueError("Application ID cannot be missing or empty.")
            if a.application_id in seen:
                raise ValueError(f"duplicate application ID: {a.application_id}")
            seen.add(a.application_id)
            if type(a.month) is not int or not 0 <= a.month < ORIGINATION_MONTHS:
                raise ValueError("Application month must be an integer from 0 to 23.")
            if a.risk_band not in BANDS:
                raise ValueError(f"Unknown risk band: {a.risk_band}")
            if type(a.principal_cents) is not int or not 0 < a.principal_cents <= 100000000:
                raise ValueError("Requested principal must be positive integer cents, at most $1m.")

    def manifest(self):
        return {
            "dataset_version": self.version, "seed": self.seed, "dataset_hash": self.dataset_hash,
            "rows": len(self.applications), "classification": "synthetic",
            "grain": "one fictional application", "primary_key": "application_id",
            "currency": "USD", "start_month": "2026-10", "origination_months": ORIGINATION_MONTHS,
            "risk_counts": {band: sum(a.risk_band == band for a in self.applications) for band in BANDS},
            "generator": "Python 3.12 random.Random; fixed band counts shuffled; shuffled month allocation; inclusive uniform integer cents $500-$2500",
            "growth_weight": "(1 + monthly_demand_growth) ** month; same rows for all policies",
        }


def generate_dataset(seed: int = DEFAULT_SEED, count: int = 10000) -> Dataset:
    if type(seed) is not int or type(count) is not int or not 0 <= count <= 100000:
        raise ValueError("Seed must be an integer; count must be an integer from 0 to 100000.")
    rng = Random(seed)
    low, medium = count * 45 // 100, count * 35 // 100
    bands = ["low"] * low + ["medium"] * medium + ["high"] * (count - low - medium)
    months = [i % ORIGINATION_MONTHS for i in range(count)]
    rng.shuffle(bands)
    rng.shuffle(months)
    rows = tuple(Application(f"syn-{i + 1:06d}", months[i], bands[i], rng.randint(50000, 250000)) for i in range(count))
    return Dataset(rows, seed)


def save_dataset(dataset: Dataset, path: Path) -> None:
    dataset.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(CSV_FIELDS)
        for a in dataset.applications:
            writer.writerow((a.application_id, a.month, a.risk_band, a.principal_cents))


def load_dataset(path: Path, seed: int = DEFAULT_SEED) -> Dataset:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != CSV_FIELDS:
            raise ValueError(f"CSV must have exactly these fields: {CSV_FIELDS}")
        try:
            rows = []
            for r in reader:
                if None in r or any(r[name] is None for name in CSV_FIELDS):
                    raise ValueError("Each CSV record must have exactly the declared fields.")
                rows.append(Application(r["application_id"], int(r["month"]), r["risk_band"], int(r["principal_cents"])))
        except (TypeError, KeyError, ValueError) as e:
            raise ValueError("CSV contains missing or invalid application fields.") from e
    return Dataset(tuple(rows), seed)
