"""One local measurement pass; does not claim browser or hosting latency."""

from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import json
import platform
import resource
import time

from streamlit.testing.v1 import AppTest

from lending_simulator.data import load_dataset
from lending_simulator.decisions import compare_policies, sensitivity
from lending_simulator.types import Assumptions


def main():
    root = Path(__file__).resolve().parents[1]
    data = load_dataset(root / "data/applications.csv")
    start = time.perf_counter()
    base = compare_policies(data, Assumptions())
    base_time = time.perf_counter() - start
    start = time.perf_counter()
    compare_policies(data, replace(Assumptions(), default_stress=D(2)))
    scenario_time = time.perf_counter() - start
    start = time.perf_counter()
    sensitivity(data, Assumptions(), "conservative")
    stress_time = time.perf_counter() - start
    page = AppTest.from_file(root / "app.py", default_timeout=30)
    start = time.perf_counter()
    page.run()
    first_time = time.perf_counter() - start
    if page.exception:
        raise RuntimeError("Application measurement failed.")
    start = time.perf_counter()
    page.run()
    warm_time = time.perf_counter() - start
    report = {
        "environment": platform.platform(), "python": platform.python_version(),
        "base_policy_comparison_seconds": base_time,
        "scenario_comparison_seconds": scenario_time,
        "20_cell_stress_grid_seconds": stress_time,
        "apptest_first_run_seconds": first_time, "apptest_warm_run_seconds": warm_time,
        "peak_process_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "measurements_are": "One Linux local-process pass; engine and AppTest, not browser/network/hosting latency or multi-user cache load.",
        "base_run_ids": [r.run_id for r in base],
    }
    output = root / "artifacts/performance.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
