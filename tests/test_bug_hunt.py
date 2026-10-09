"""Regressions for failures reproduced during the repository-wide bug hunt."""

from dataclasses import replace
from decimal import Decimal as D, localcontext
from io import BytesIO
import json

from openpyxl import load_workbook
import pytest

from lending_simulator.cli import main
from lending_simulator.data import Application, Dataset, generate_dataset, load_dataset, save_dataset
from lending_simulator.decisions import compare_policies, evaluate_policy
from lending_simulator.exports import scenario_workbook
from lending_simulator.model import run_model
from lending_simulator.types import Assumptions, CohortInput


@pytest.mark.parametrize("amount", ["1000000000000.01", "1e309"])
@pytest.mark.parametrize("field", ["initial_cash", "facility_limit", "acquisition_cost",
                                   "servicing_cost", "monthly_opex", "cash_floor"])
def test_usd_inputs_reject_magnitudes_that_cannot_be_reliably_modeled_or_exported(field, amount):
    with pytest.raises(ValueError, match="at most"):
        replace(Assumptions(), **{field: D(amount)}).validate()


@pytest.mark.parametrize("rate", ["1e-16", "1e-24", "1e-30", "1e-34"])
def test_tiny_positive_rates_preserve_the_loan_present_value(rate):
    a = replace(Assumptions(), borrower_rate=D(rate), pd_low=D(0),
                merchant_fee=D(0), funding_rate=D(0), acquisition_cost=D(0),
                servicing_cost=D(0), monthly_opex=D(0))
    result = run_model((CohortInput(0, "low", D(1), D(1200)),), a,
                       "conservative", D(1), "tiny-rate")
    first = result.monthly[1]
    with localcontext() as context:
        context.prec = 80
        payment = first.principal_collections + first.interest_revenue
        present_value = sum((payment / (1 + D(rate) / 12) ** age
                             for age in range(1, 13)), D(0))
        assert abs(present_value - D(1200)) < D("1e-26")
    assert result.checks.passed


@pytest.mark.parametrize("pd", ["1e-16", "1e-24", "1e-32", "1e-34"])
def test_tiny_lifetime_pd_preserves_the_expected_default_count(pd):
    a = replace(Assumptions(), pd_low=D(pd), borrower_rate=D(0))
    result = run_model((CohortInput(0, "low", D(1), D(1200)),), a,
                       "conservative", D(1), "tiny-pd")
    with localcontext() as context:
        context.prec = 80
        defaults = sum((row.expected_defaults for row in result.cohorts), D(0))
        assert abs(defaults / D(pd) - 1) < D("1e-25")
    assert result.checks.passed


@pytest.mark.parametrize("pd, lag", [(".02", 0), (".02", 3), (".5", 12)])
def test_full_recovery_has_exact_zero_loss_and_meets_a_zero_loss_cap(pd, lag):
    a = replace(Assumptions(), pd_low=D(pd), recovery_rate=D(1), recovery_lag=lag,
                loss_cap=D(0), initial_cash=D(10000000), cash_floor=D(0))
    result = run_model((CohortInput(0, "low", D(1), D(1200)),), a,
                       "conservative", D(1), "full-recovery")
    assert result.summary.gross_chargeoffs > 0
    assert result.summary.net_credit_loss == 0
    assert result.summary.loss_ratio == 0
    assert evaluate_policy(result).eligible
    assert result.checks.passed


@pytest.mark.parametrize("band", ["medium", "high"])
def test_workbook_marks_unfunded_policy_ratios_unavailable(band):
    dataset = Dataset((Application("only-band", 0, band, 100000),), 1)
    results = compare_policies(dataset, Assumptions())
    book = load_workbook(BytesIO(scenario_workbook(results[0], results, dataset)), data_only=True)
    assert book["Summary"]["B8"].value == "n.a."
    assert book["Policies"]["G2"].value == "n.a."
    assert book["Policies"]["H2"].value == "n.a."
    assert book["Policies"]["K2"].value is False
    assert isinstance(book["Policies"]["H4"].value, float)


def test_workbook_rejects_comparison_from_different_applied_inputs():
    dataset = generate_dataset(count=24)
    base = compare_policies(dataset, Assumptions())
    capital = compare_policies(dataset, replace(Assumptions(), initial_cash=D(1250000)))
    with pytest.raises(ValueError, match="same population, assumptions, and horizon"):
        scenario_workbook(base[0], (base[0], capital[1], base[2]), dataset)


@pytest.mark.parametrize("saved", [None, [], "text", 1, {"assumptions": None},
                                  {"assumptions": []}, {"assumptions": "text"}])
def test_cli_reports_invalid_json_shapes_without_a_traceback(tmp_path, capsys, saved):
    path = tmp_path / "assumptions.json"
    path.write_text(json.dumps(saved))
    output = tmp_path / "exports"
    assert main(["--assumptions", str(path), "--output", str(output)]) == 2
    assert "Scenario failed:" in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize("field, value", [("model_version", "unavailable-version"),
                                        ("run_id", "incorrect-run"),
                                        ("policy", "unknown-policy"),
                                        ("policy", []), ("policy", {}),
                                        ("currency", "EUR"),
                                        ("expected_applications", "999999"),
                                        ("full_runoff_months", 1)])
def test_cli_rejects_manifests_that_cannot_reproduce_the_saved_run(tmp_path, capsys, field, value):
    dataset = generate_dataset(count=24)
    dataset_path = tmp_path / "applications.csv"
    save_dataset(dataset, dataset_path)
    manifest = compare_policies(dataset, Assumptions())[0].manifest()
    manifest[field] = value
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    output = tmp_path / "exports"
    assert main(["--dataset", str(dataset_path), "--assumptions", str(path), "--output", str(output)]) == 2
    assert "Scenario failed:" in capsys.readouterr().err
    assert not output.exists()


def test_cli_roundtrip_of_nonbase_manifest_preserves_the_selected_run(tmp_path):
    dataset = generate_dataset(seed=99, count=24)
    dataset_path = tmp_path / "applications.csv"
    save_dataset(dataset, dataset_path)
    assumptions = replace(Assumptions(), recovery_lag=12, funding_rate=D(".12"),
                          demand_growth=D(".10"), initial_cash=D(1250000))
    selected = compare_policies(dataset, assumptions)[1]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(selected.manifest() | {"dataset": dataset.manifest()}))
    output = tmp_path / "exports"
    assert main(["--dataset", str(dataset_path), "--assumptions", str(path), "--output", str(output)]) == 0
    replay = json.loads((output / "comparison.json").read_text())
    balanced = next(r for r in replay["policies"] if r["policy"] == "balanced")
    assert balanced["run_id"] == selected.run_id
    assert balanced["assumptions"] == assumptions.to_dict()
    assert replay["dataset"] == dataset.manifest()


@pytest.mark.parametrize("row", ["a,0,low,10000,unexpected", "a,0,low,10000,"])
def test_csv_rejects_extra_record_fields_instead_of_discarding_them(tmp_path, row):
    path = tmp_path / "applications.csv"
    path.write_text("application_id,month,risk_band,principal_cents\n" + row + "\n")
    with pytest.raises(ValueError, match="fields"):
        load_dataset(path)


@pytest.mark.parametrize("values", [None, [], "text", 1])
def test_assumptions_parser_rejects_nonobject_inputs_as_value_errors(values):
    with pytest.raises(ValueError, match="object"):
        Assumptions.from_dict(values)
