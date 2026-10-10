"""Real-browser export boundary checks with explicit, isolated fault injection.

The fixture wraps only the CSV builder: a gate holds one generation until the
browser has changed policy, or raises once before generation. All successful
files come from the original factory/cache/export code. app.py and financial
inputs/results are unchanged. No fixture is loaded by the production app.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import threading
import time
import traceback
from uuid import uuid4
import zipfile

from playwright.sync_api import expect, sync_playwright

from scripts.browser_acceptance import BASE_RUN, BALANCED_RUN, ROOT, Review, live_server


def instrumented_app(root, controls):
    """Test-only entrypoint; retain the original generator across app reruns."""
    from lending_simulator.ui import downloads

    root, controls = Path(root), Path(controls)
    if not getattr(downloads.csv_package, "_browser_export_fixture", False):
        original = downloads.csv_package
        lock = threading.Lock()

        def record(event):
            with lock, (controls / "events.jsonl").open("a") as stream:
                stream.write(json.dumps({**event, "time": time.monotonic()}) + "\n")

        def generate(selected, dataset):
            kind, run_id = "csv", selected.run_id
            pending = controls / "next.json"
            with lock:
                instruction = json.loads(pending.read_text()) if pending.exists() else {}
                if instruction.get("kind") == kind:
                    pending.replace(controls / "claimed.json")
                else:
                    instruction = {}
            token, mode = instruction.get("token", uuid4().hex), instruction.get("mode", "normal")
            event = {"token": token, "mode": mode, "kind": kind, "run_id": run_id}
            record({**event, "event": "started"})
            if mode == "fail":
                record({**event, "event": "failed"})
                raise OSError("Browser acceptance: injected export generation failure")
            if mode == "hold":
                deadline = time.monotonic() + 40
                while not (controls / (token + ".release")).exists():
                    if time.monotonic() > deadline:
                        raise TimeoutError("Browser export gate was not released")
                    time.sleep(.025)
                record({**event, "event": "released"})
            result = original(selected, dataset)
            data = result.encode() if isinstance(result, str) else result
            record({**event, "event": "completed", "bytes": len(data), "sha256": sha256(data).hexdigest()})
            return result

        generate._browser_export_fixture = True
        downloads.csv_package = generate
    runpy.run_path(str(root / "app.py"), run_name="__main__")


class Gate:
    def __init__(self, directory):
        self.directory = directory

    def arm(self, mode):
        token = uuid4().hex
        temporary = self.directory / "instruction.tmp"
        temporary.write_text(json.dumps({"kind": "csv", "mode": mode, "token": token}))
        temporary.replace(self.directory / "next.json")
        return token

    def events(self):
        path = self.directory / "events.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def wait(self, page, token, event):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            matches = [e for e in self.events() if e["token"] == token and e["event"] == event]
            if matches:
                return matches[-1]
            page.wait_for_timeout(25)
        raise AssertionError(f"Export fixture did not record {event} for {token}")

    def assert_held(self, token):
        events = [e["event"] for e in self.events() if e["token"] == token]
        assert events == ["started"], events

    def release(self, token):
        (self.directory / (token + ".release")).touch()


def save_csv(review, download, expected_run, prefix):
    assert download.failure() is None
    assert expected_run in download.suggested_filename
    path = review.output / (prefix + download.suggested_filename)
    download.save_as(path)
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["run_id"] == expected_run
    return {"file": path.name, "bytes": path.stat().st_size,
            "sha256": sha256(path.read_bytes()).hexdigest(), "run_id": manifest["run_id"]}


def slow_generation(review, gate):
    page = review.page
    page.get_by_role("button", name="Export", exact=True).click()
    token = gate.arm("hold")
    button = page.get_by_role("button", name="CSV results + manifest", exact=True)
    button.click()
    started = gate.wait(page, token, "started")
    assert started["run_id"] == BASE_RUN
    expect(button).to_be_disabled()
    gate.assert_held(token)
    review.capture("generating")
    review.check("Requested export shows a disabled generating control while held on the server", started)

    page.keyboard.press("Escape")
    review.policy("Balanced")
    assert review.applied_run() == BALANCED_RUN
    gate.assert_held(token)
    switched = time.monotonic()
    metrics = review.metrics()
    review.capture("changed-policy-while-generating")
    review.check("Balanced renders and its applied identity changes before original generation is released", {
        "applied_run": BALANCED_RUN, "selected_at": switched, "original_started_at": started["time"],
        "original_still_held": True, "metrics": metrics})

    with page.expect_download() as event:
        gate.release(token)
    file = save_csv(review, event.value, BASE_RUN, "held-")
    completed = gate.wait(page, token, "completed")
    released = gate.wait(page, token, "released")
    assert started["time"] < switched < released["time"] <= completed["time"]
    assert file["sha256"] == completed["sha256"]
    assert review.applied_run() == BALANCED_RUN and review.metrics() == metrics
    review.check("Released export downloads the original Conservative file while Balanced stays applied", {
        **file, "started_at": started["time"], "switched_at": switched,
        "released_at": released["time"], "completed_at": completed["time"]})

    page.get_by_role("button", name="Export", exact=True).click()
    with page.expect_download() as event:
        page.get_by_role("button", name="CSV results + manifest", exact=True).click()
    review.check("A later export uses the currently viewed Balanced run", save_csv(review, event.value, BALANCED_RUN, "new-"))


def generation_retry(review, gate):
    page = review.page
    metrics = review.metrics()
    downloads = []
    page.on("download", lambda download: downloads.append(download))
    page.get_by_role("button", name="Export", exact=True).click()
    token = gate.arm("fail")
    button = page.get_by_role("button", name="CSV results + manifest", exact=True)
    button.click()
    failed = gate.wait(page, token, "failed")
    assert failed["run_id"] == BASE_RUN
    error = page.get_by_test_id("stDownloadButtonError")
    expect(error).to_have_text("Failed to generate file for download")
    expect(button).to_be_enabled()
    assert not downloads
    review.capture("generation-error", target=error)
    review.check("Server generation failure shows an inline error and restores the same download control", failed)
    assert review.metrics() == metrics
    assert page.get_by_test_id("stException").count() == 0
    review.check("Failed generation produces no download and leaves applied metrics intact", {"metrics": metrics})

    with page.expect_download() as event:
        button.click()
    file = save_csv(review, event.value, BASE_RUN, "retry-")
    expect(error).to_have_count(0)
    assert len(downloads) == 1
    assert review.metrics() == metrics
    review.check("Retry clears the error and downloads the exact applied run", file)
    page.keyboard.press("Escape")
    assert review.applied_run() == BASE_RUN
    review.navigate("Policies")
    review.check("The applied scenario and normal analysis remain usable after failure and retry")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "browser-export-resilience")
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sources = [ROOT / "app.py", ROOT / ".streamlit/config.toml", *sorted((ROOT / "lending_simulator/ui").glob("*.py"))]
    report = {"created_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in sources},
        "fixture": "Test-only wrapper holds or fails one CSV builder call inside the real cached_export. Each case has a fresh server/cache. Original builder produces every successful file. Unchanged app.py, model, dataset and UI. No deployment or state injection.",
        "cases": []}
    with tempfile.TemporaryDirectory(prefix="lending-export-fixture-") as directory:
        with sync_playwright() as engine:
            browser = engine.chromium.launch(downloads_path=str(output / "native-downloads"))
            report["browser"] = browser.version
            for name, task in (("slow-generation", slow_generation), ("generation-retry", generation_retry)):
                controls = Path(directory) / name
                controls.mkdir()
                entrypoint = controls / "fixture.py"
                entrypoint.write_text("import sys\nsys.path.insert(0, " + repr(str(ROOT)) + ")\n"
                    "from scripts.browser_export_resilience import instrumented_app\n"
                    f"instrumented_app({str(ROOT)!r}, {str(controls)!r})\n")
                gate = Gate(controls)
                case = {"name": name, "viewport": [1440, 900], "checks": [], "captures": [], "operations": []}
                report["cases"].append(case)
                context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
                context.tracing.start(screenshots=True, snapshots=True, sources=True)
                page = context.new_page()
                page.set_default_timeout(15000)
                review = Review(page, output, name, case)
                with live_server(ROOT, output / (name + "-streamlit.log"), entrypoint=entrypoint) as address:
                    try:
                        page.goto(address, wait_until="domcontentloaded")
                        review.ready()
                        task(review, gate)
                        assert not review.console, review.console
                        assert not review.requests, review.requests
                        assert review.websockets, "No Streamlit WebSocket observed"
                        review.check("No unexpected browser errors or failed requests; WebSocket connected")
                        case["status"] = "passed"
                    except Exception:
                        case["status"] = "failed"
                        case["error"] = traceback.format_exc()
                        print(f"FAIL {name}: {case['error']}", flush=True)
                        page.screenshot(path=str(output / f"{name}-failure.png"), full_page=True)
                        (output / f"{name}-failure.txt").write_text(page.locator("body").inner_text())
                    finally:
                        case.update(console=review.console, failed_requests=review.requests, websockets=review.websockets)
                        context.tracing.stop(path=str(output / f"{name}-trace.zip"))
                        context.close()
                        case["generation_events"] = gate.events()
                        (output / "report.json").write_text(json.dumps(report, indent=2))
            browser.close()
    failures = sum(case.get("status") != "passed" for case in report["cases"])
    print(f"Export resilience: {len(report['cases']) - failures} passed, {failures} failed. Evidence: {output}", flush=True)
    if failures or len(report["cases"]) != 2:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
