from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import json

import pytest

from lending_simulator.data import load_dataset
from lending_simulator.decisions import compare_policies
from lending_simulator.types import Assumptions


def test_deferred_brief_uses_captured_run_and_does_not_prepare_other_formats(monkeypatch):
    from lending_simulator.ui import downloads
    dataset = load_dataset(Path(__file__).resolve().parents[1] / 'data/applications.csv')
    results = compare_policies(dataset, Assumptions())
    downloads.cached_export.clear()

    def unexpected_workbook(*args):
        raise AssertionError('Workbook generation must wait for its own download.')

    monkeypatch.setattr(downloads, 'scenario_workbook', unexpected_workbook)
    factory = downloads.download_factory('brief', results[1], results, dataset)
    newer = compare_policies(dataset, replace(Assumptions(), initial_cash=D(1250000)))
    assert newer[1].run_id != results[1].run_id
    text = factory()
    manifest = json.loads(text.split('```json\n')[1].split('```')[0])
    assert manifest['run_id'] == results[1].run_id
    assert manifest['assumptions']['initial_cash'] == '500000'


def test_download_factory_rejects_mixed_or_stale_result_bundles():
    from lending_simulator.ui.downloads import download_factory
    dataset = load_dataset(Path(__file__).resolve().parents[1] / 'data/applications.csv')
    base = compare_policies(dataset, Assumptions())
    other = compare_policies(dataset, replace(Assumptions(), default_stress=D(2)))
    with pytest.raises(ValueError):
        download_factory('brief', base[1], other, dataset)
    with pytest.raises(ValueError):
        download_factory('workbook', base[0], (base[0], other[1], base[2]), dataset)
