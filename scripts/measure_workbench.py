"""Separate local operation timings. No browser/hosting or percentile claims."""

import argparse
from dataclasses import replace
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path
import platform
import resource
from statistics import median
import subprocess
from time import perf_counter

import streamlit as st
from streamlit.testing.v1 import AppTest

from lending_simulator.data import load_dataset
from lending_simulator.decisions import compare_policies, sensitivity
from lending_simulator.types import Assumptions
from lending_simulator.ui.downloads import download_factory, cached_export


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('artifacts/workbench-performance.json'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    measurements = {}

    def measure(name, operation):
        start = perf_counter()
        value = operation()
        measurements.setdefault(name, []).append(perf_counter() - start)
        if isinstance(value, AppTest) and value.exception:
            raise RuntimeError(f'AppTest failed during {name}.')
        return value

    dataset = load_dataset(root / 'data/applications.csv')
    results = None
    for _ in range(3):
        results = measure('engine_three_policy_base', lambda: compare_policies(dataset, Assumptions()))
        measure('engine_three_policy_custom', lambda: compare_policies(dataset,
            replace(Assumptions(), funding_rate=D('.12'))))
        measure('engine_twenty_stress_cases', lambda: sensitivity(dataset, Assumptions(), 'conservative'))
        st.cache_data.clear()
        app = AppTest.from_file(root / 'app.py', default_timeout=30)
        measure('apptest_cold_application_caches', app.run)
        measure('apptest_warm_overview', app.run)
        measure('apptest_draft_commit', lambda: app.slider(key='funding_percent').set_value(12).run())
        for view in ('Policies', 'Cohorts', 'Funding & stress', 'Methodology', 'Overview'):
            measure('apptest_view_'+view.lower().replace(' & ', '_').replace(' ', '_'),
                lambda view=view: app.button_group(key='analysis_view').set_value(view).run())
        measure('apptest_immediate_policy', lambda: app.selectbox(key='policy').set_value('balanced').run())
        measure('apptest_restore_draft', lambda: app.button(key='restore_applied').click().run())
        app.slider(key='funding_percent').set_value(12).run()
        measure('apptest_custom_apply_uncached', lambda: app.button(key='run_scenario').click().run())
        measure('apptest_custom_apply_cached', lambda: app.button(key='run_scenario').click().run())
        app.button_group(key='analysis_view').set_value('Funding & stress').run()
        measure('apptest_stress_grid_uncached', lambda: app.button(key='run_stress').click().run())
        measure('apptest_stress_grid_cached', lambda: app.button(key='run_stress').click().run())
        for kind in ('brief', 'csv', 'workbook'):
            cached_export.clear()
            factory = download_factory(kind, results[1], results, dataset)
            measure('export_'+kind+'_uncached', factory)
            measure('export_'+kind+'_cached', factory)

    source_files = [root/'app.py', root/'.streamlit/config.toml',
                    *sorted((root/'lending_simulator/ui').glob('*.py'))]
    report = {
        'environment': platform.platform(), 'python': platform.python_version(),
        'base_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'source_sha256': {str(path.relative_to(root)):sha256(path.read_bytes()).hexdigest() for path in source_files},
        'scope': 'Three local-process samples per named operation. AppTest executes server code; no browser paint, focus, WebSocket/download transport, network, hosting or multi-user latency. Cold means cleared application caches after Python imports. Export cached timing includes payload deserialization. No p95 or service-level acceptance is inferred.',
        'operations': {name: {'samples_seconds': samples, 'median_seconds': median(samples), 'maximum_seconds': max(samples)}
                       for name,samples in measurements.items()},
        'peak_process_rss_mb': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        'memory_scope': 'Peak for this sequential mixed measurement process, including AppTest, models, Plotly and exports. Not isolated runtime or sustained multi-user cache load.',
        'base_run_ids': [result.run_id for result in results],
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'operations':len(measurements),
        'peak_process_rss_mb':report['peak_process_rss_mb'],
        'median_seconds':{name:round(median(samples),3) for name,samples in measurements.items()}},indent=2))


if __name__ == '__main__':
    main()
