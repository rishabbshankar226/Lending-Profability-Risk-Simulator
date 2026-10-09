"""Format-specific generation from immutable applied snapshots."""

from functools import partial

import streamlit as st

from lending_simulator import MODEL_VERSION
from lending_simulator.decisions import select_strategy
from lending_simulator.exports import scenario_workbook
from lending_simulator.presentation import csv_package, decision_brief


@st.cache_data(max_entries=12, show_spinner=False)
def cached_export(kind, run_id, model_version, dataset_hash, _selected, _results, _dataset):
    if run_id != _selected.run_id or model_version != MODEL_VERSION or dataset_hash != _dataset.dataset_hash:
        raise ValueError('Export identity does not match its captured inputs.')
    if kind == 'brief':
        return decision_brief(_selected, _results)
    if kind == 'csv':
        return csv_package(_selected, _dataset)
    if kind == 'workbook':
        return scenario_workbook(_selected, _results, _dataset)
    raise ValueError('Unknown export format.')


def download_factory(kind, selected, results, dataset):
    if selected not in results or selected.dataset_hash != dataset.dataset_hash:
        raise ValueError('Export must use one complete applied result bundle and its dataset.')
    select_strategy(results)
    if kind not in ('brief', 'csv', 'workbook'):
        raise ValueError('Unknown export format.')
    return partial(cached_export, kind, selected.run_id, MODEL_VERSION, dataset.dataset_hash,
                   selected, results, dataset)
