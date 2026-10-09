"""Reproduce the same scenario bundle outside the dashboard."""

import argparse
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
import json
import sys

from lending_simulator import MODEL_VERSION
from lending_simulator.data import DEFAULT_SEED, load_dataset
from lending_simulator.decisions import compare_policies, select_strategy
from lending_simulator.exports import scenario_workbook, workbook_spec
from lending_simulator.presentation import csv_package
from lending_simulator.types import Assumptions, POLICIES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "applications.csv")
    parser.add_argument("--assumptions", type=Path, help="Assumptions JSON or a downloaded manifest.json")
    parser.add_argument("--output", type=Path, default=Path("artifacts/base-case"))
    args = parser.parse_args(argv)
    try:
        saved = json.loads(args.assumptions.read_text()) if args.assumptions else {}
        if not isinstance(saved, dict):
            raise ValueError("Assumptions or manifest must be a JSON object.")
        if "model_version" in saved and saved["model_version"] != MODEL_VERSION:
            raise ValueError("The manifest's model version does not match this simulator.")
        provenance = saved.get("dataset", {})
        if not isinstance(provenance, dict):
            raise ValueError("The manifest's dataset must be a JSON object.")
        dataset = load_dataset(args.dataset, seed=provenance.get("seed", DEFAULT_SEED))
        if any(key in provenance and provenance[key] != value for key, value in dataset.manifest().items()):
            raise ValueError("The manifest's dataset provenance does not match the supplied CSV.")
        assumptions = Assumptions.from_dict(saved.get("assumptions", saved))
        if "dataset_hash" in saved and saved["dataset_hash"] != dataset.dataset_hash:
            raise ValueError("The manifest's dataset hash does not match the supplied CSV.")
        results = compare_policies(dataset, assumptions)
        if "policy" in saved and (not isinstance(saved["policy"], str) or saved["policy"] not in POLICIES):
            raise ValueError("The manifest contains an unknown policy.")
        if "run_id" in saved:
            selected = next((r for r in results if r.policy == saved.get("policy")), None)
            if selected is None or selected.run_id != saved["run_id"]:
                raise ValueError("The manifest's run ID does not match the reproduced policy and inputs.")
            metadata = selected.manifest()
            for key in ("currency", "start_month", "month_index_base", "operating_horizon_months",
                        "full_runoff_months", "data_classification", "historical_evidence_level"):
                if key in saved and saved[key] != metadata[key]:
                    raise ValueError(f"The manifest's {key} does not match the reproduced run.")
            if "expected_applications" in saved and Decimal(str(saved["expected_applications"])) != selected.summary.expected_applications:
                raise ValueError("The manifest's expected applications do not match the reproduced run.")
        decision = select_strategy(results)
        args.output.mkdir(parents=True, exist_ok=True)
        records = []
        for result in results:
            summary = {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(result.summary).items()}
            records.append(result.manifest() | {"summary": summary})
            (args.output / f"{result.policy}.zip").write_bytes(csv_package(result, dataset))
            (args.output / f"{result.policy}.xlsx").write_bytes(scenario_workbook(result, results, dataset))
        comparison = {"dataset": dataset.manifest(), "decision": asdict(decision), "policies": records}
        (args.output / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
        selected_policy = decision.recommended_policy or decision.diagnostic_policy or results[0].policy
        selected = next(r for r in results if r.policy == selected_policy)
        (args.output / "workbook-spec.json").write_text(json.dumps(workbook_spec(selected, results, dataset), indent=2) + "\n")
        print(decision.message)
        for r in results:
            print(f"{r.policy}: operating result ${r.summary.operating_result:,.2f}; minimum cash ${r.summary.minimum_cash:,.2f}; run {r.run_id}")
        return 0 if all(r.checks.passed for r in results) else 1
    except (ValueError, OSError, ArithmeticError) as error:
        print(f"Scenario failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
