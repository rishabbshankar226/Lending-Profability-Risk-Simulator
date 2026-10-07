import csv
from dataclasses import replace
from decimal import Decimal as D
from io import BytesIO, StringIO
import json
import zipfile

from openpyxl import load_workbook

from lending_simulator.data import generate_dataset
from lending_simulator.decisions import compare_policies
from lending_simulator.presentation import cohort_heatmap, csv_package, workbook_payload, monthly_frame, assumption_register
from lending_simulator.exports import scenario_workbook
from lending_simulator.types import Assumptions


def test_csv_package_has_manifest_units_exact_values_and_matching_run():
    dataset = generate_dataset(count=100)
    result = compare_policies(dataset, Assumptions())[1]
    archive = zipfile.ZipFile(BytesIO(csv_package(result, dataset)))
    manifest = json.loads(archive.read("manifest.json"))
    assert manifest["run_id"] == result.run_id
    assert manifest["dataset_hash"] == dataset.dataset_hash
    assert manifest["assumptions"] == result.assumptions.to_dict()
    assert manifest["currency"] == "USD"
    rows = list(csv.DictReader(StringIO(archive.read("monthly.csv").decode())))
    assert len(rows) == 39
    assert D(rows[0]["ending_cash"]) == result.monthly[0].ending_cash
    assert json.loads(archive.read("units.json"))["monthly"]["ending_cash"] == "USD, month-end balance"
    assert json.loads(archive.read("units.json"))["summary"]["operating_result"] == "USD, full-runoff total"


def test_heatmap_preserves_future_unobserved_ages_as_missing():
    result = compare_policies(generate_dataset(count=100), Assumptions())[1]
    heatmap = cohort_heatmap(result, as_of_month=23)
    assert heatmap.loc[23, 0] == 0
    assert heatmap.loc[23, 1:].isna().all()
    assert heatmap.loc[0, 12] > 0
    assert monthly_frame(result)["ending_cash"].iloc[0] == float(result.monthly[0].ending_cash)


def test_workbook_contains_selected_scenario_and_independent_formula_benchmarks():
    dataset = generate_dataset(count=100)
    assumptions = replace(Assumptions(), funding_rate=D(".12"))
    results = compare_policies(dataset, assumptions)
    result = results[1]
    book = load_workbook(BytesIO(scenario_workbook(result, results, dataset)), data_only=False)
    cached = load_workbook(BytesIO(scenario_workbook(result, results, dataset)), data_only=True)
    assert book["Assumptions"]["B2"].value == result.run_id
    assert cached["Summary"]["B5"].value == float(result.summary.operating_result)
    assert book["Loan benchmark"]["B8"].value.startswith("=IF(")
    assert book["Loan benchmark"]["B6"].number_format.endswith("%")
    assert book["Loan benchmark"]["F23"].value.startswith("=")
    assert abs(cached["Loan benchmark"]["F23"].value) < .01
    assert cached["Default benchmark"]["B7"].value == 675
    assert cached["Default benchmark"]["E16"].value == 225
    assert cached["Default benchmark"]["E15"].value == 0
    assert workbook_payload(result, results, dataset)["selected_run_id"] == result.run_id


def test_changed_assumptions_export_a_new_scenario_without_mutating_original():
    dataset = generate_dataset(count=100)
    base = compare_policies(dataset, Assumptions())[1]
    changed = compare_policies(dataset, replace(Assumptions(), default_stress=D(2)))[1]
    assert base.run_id != changed.run_id
    base_archive = zipfile.ZipFile(BytesIO(csv_package(base, dataset)))
    changed_archive = zipfile.ZipFile(BytesIO(csv_package(changed, dataset)))
    assert json.loads(base_archive.read("manifest.json"))["assumptions"]["default_stress"] == "1"
    assert json.loads(changed_archive.read("manifest.json"))["assumptions"]["default_stress"] == "2"


def test_assumptions_table_serializes_to_the_dashboard_without_arrow_type_fixes():
    import pyarrow as pa
    import pandas as pd
    table = pa.Table.from_pandas(pd.DataFrame(assumption_register(Assumptions())))
    assert table.num_rows == 19
