from dataclasses import replace
from decimal import Decimal as D

import pytest

from lending_simulator.analytics import aggregate_for_model, policy_population
from lending_simulator.data import Application, Dataset, generate_dataset, load_dataset, save_dataset


def test_base_population_is_reproducible_exact_mix_and_integer_cents():
    one = generate_dataset()
    two = generate_dataset()
    assert one == two
    assert len(one.applications) == 10000
    assert {b: sum(a.risk_band == b for a in one.applications) for b in ("low", "medium", "high")} == {
        "low": 4500, "medium": 3500, "high": 2000,
    }
    assert {a.month for a in one.applications} == set(range(24))
    assert all(type(a.principal_cents) is int and 50000 <= a.principal_cents <= 250000 for a in one.applications)
    assert one.dataset_hash != generate_dataset(seed=99).dataset_hash


def test_csv_roundtrip_preserves_content_hash_and_population(tmp_path):
    dataset = generate_dataset(count=100)
    path = tmp_path / "applications.csv"
    save_dataset(dataset, path)
    reloaded = load_dataset(path, dataset.seed)
    assert reloaded == dataset


@pytest.mark.parametrize("bad", [
    Application("a", 0, "low", 0), Application("a", 24, "low", 10000),
    Application("a", 0, "unknown", 10000), Application("", 0, "low", 10000),
    Application("a", 0, "low", 100.5),
])
def test_invalid_application_records_are_rejected(bad):
    with pytest.raises(ValueError):
        Dataset((bad,), seed=1).validate()


def test_duplicate_ids_are_rejected_before_sql_joins():
    a = Application("syn-a", 0, "low", 10000)
    with pytest.raises(ValueError, match="duplicate"):
        aggregate_for_model(Dataset((a, a), 1), "conservative", D(0))


def test_sql_approvals_have_correct_denominators_and_nested_sets():
    dataset = Dataset((Application("a", 0, "low", 10000),
                       Application("b", 0, "medium", 20000),
                       Application("c", 1, "high", 30000)), 1)
    rows = policy_population(dataset)
    assert [r["approved_count"] for r in rows] == [1, 2, 3]
    assert [r["approved_principal_cents"] for r in rows] == [10000, 30000, 60000]
    assert all(r["application_count"] == 3 for r in rows)
    assert rows[1]["approval_rate"] == pytest.approx(2 / 3)
    strict, denominator = aggregate_for_model(dataset, "conservative", D(0))
    broad, _ = aggregate_for_model(dataset, "aggressive", D(0))
    assert denominator == D(3)
    assert sum(c.principal for c in broad) == D(600)
    assert {c.risk_band for c in strict} <= {c.risk_band for c in broad}


def test_growth_scales_same_population_with_explicit_expected_weights():
    dataset = Dataset((Application("a", 0, "low", 10000),
                       Application("b", 1, "low", 10000)), 1)
    cohorts, denominator = aggregate_for_model(dataset, "aggressive", D(".10"))
    assert denominator == D("2.10")
    assert [c.expected_count for c in cohorts] == [D(1), D("1.10")]
    assert sum(c.principal for c in cohorts) == D(210)


def test_empty_dataset_retains_policy_rows_with_unavailable_rates():
    rows = policy_population(Dataset((), 1))
    assert len(rows) == 3
    assert all(r["approved_count"] == 0 and r["approval_rate"] is None for r in rows)


def test_sql_policy_parameter_does_not_accept_sql_text():
    with pytest.raises(ValueError, match="policy"):
        aggregate_for_model(generate_dataset(count=24), "aggressive' OR 1=1 --", D(0))
