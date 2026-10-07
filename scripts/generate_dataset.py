"""Recreate the committed fictional population and manifest, deterministically."""

from pathlib import Path
import json

from lending_simulator.data import generate_dataset, save_dataset


def main():
    root = Path(__file__).resolve().parents[1]
    dataset = generate_dataset()
    save_dataset(dataset, root / "data" / "applications.csv")
    (root / "data" / "manifest.json").write_text(json.dumps(dataset.manifest(), indent=2) + "\n")
    print(dataset.dataset_hash)


if __name__ == "__main__":
    main()
