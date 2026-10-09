from pathlib import Path
import json
import subprocess
import sys


def test_cli_produces_reproducible_manifests_and_policy_outputs(tmp_path):
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run([sys.executable, "-m", "lending_simulator.cli", "--output", str(tmp_path)],
                               cwd=root, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    summary = json.loads((tmp_path / "comparison.json").read_text())
    assert summary["decision"]["recommended_policy"] == "conservative"
    assert len(summary["policies"]) == 3
    assert all(p["checks"]["passed"] for p in summary["policies"])
    for policy in ("conservative", "balanced", "aggressive"):
        assert (tmp_path / f"{policy}.zip").is_file()
        assert (tmp_path / f"{policy}.xlsx").is_file()
