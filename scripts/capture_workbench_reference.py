"""Capture the real pre-redesign source for a reproducible visual comparison."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from playwright.sync_api import expect, sync_playwright

from scripts.browser_acceptance import live_server


REFERENCE_COMMIT = "baeda884355734f534babd2bc73ab7018742569f"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    assert commit == REFERENCE_COMMIT, "Reference checkout differs from the recorded redesign base"
    output.mkdir(parents=True, exist_ok=True)
    files = [source / "app.py", source / ".streamlit" / "config.toml",
             *sorted((source / "lending_simulator").rglob("*.py"))]
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "source_commit": commit,
        "source_sha256": {str(p.relative_to(source)): sha256(p.read_bytes()).hexdigest() for p in files},
        "scope": "Unmodified pre-redesign application in the same CI browser and dependency environment; first-screen reference captures only.",
        "captures": []}
    with live_server(source, output / "reference-streamlit.log") as address, sync_playwright() as engine:
        browser = engine.chromium.launch()
        report["browser"] = browser.version
        for name, size, options in (
            ("reference-desktop-1440", (1440, 900), {}),
            ("reference-phone-390", (390, 844), {"is_mobile": True, "has_touch": True}),
        ):
            context = browser.new_context(viewport={"width": size[0], "height": size[1]}, **options)
            page = context.new_page()
            page.set_default_timeout(15000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(address, wait_until="domcontentloaded")
            expect(page.get_by_role("heading", name="Lending Profitability & Risk Simulator", exact=True)).to_be_visible()
            expect(page.get_by_test_id("stMetricValue").first).to_have_text("$48,133")
            page.wait_for_function("() => !document.querySelector('[data-stale=\"true\"]')")
            page.wait_for_function("""() => Array.from(document.querySelectorAll('[data-testid="stPlotlyChart"]'))
                .every(e => e.querySelector('.js-plotly-plot')?.data?.length)""")
            assert not errors, errors
            assert not page.get_by_test_id("stException").count()
            filename = name + ".png"
            page.screenshot(path=str(output / filename), full_page=True)
            report["captures"].append({"file": filename, "viewport": size, "status": "passed"})
            context.close()
        browser.close()
    (output / "reference-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Reference captures: 2 passed; exact pre-redesign source.", flush=True)


if __name__ == "__main__":
    main()
