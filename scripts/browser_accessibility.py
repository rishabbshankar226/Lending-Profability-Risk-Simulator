"""Inspect native accessibility semantics and real tab zoom in isolated Chromium.

AX tree and DOM/style inspection are read-only. The test-only extension changes
Chrome's native tab zoom through a visible helper control, never the app DOM.
Each zoom case uses a new, temporary profile; no account or production host is
involved. These checks do not replace screen-reader or physical-device review.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import tempfile
import traceback
from urllib.parse import quote

from playwright.sync_api import expect, sync_playwright

from scripts.browser_acceptance import BASE_RUN, ROOT, VIEWS, Review, live_server


def viewport(page):
    return page.evaluate("""() => ({width:innerWidth,height:innerHeight,dpr:devicePixelRatio,
        visualScale:visualViewport.scale,outerWidth:outerWidth,outerHeight:outerHeight})""")


def text_contrast(page):
    """Sample visible HTML text and input values; retain exclusions explicitly."""
    samples = page.evaluate("""() => {
        const items=[];
        function sample(element,text){
            const style=getComputedStyle(element);
            if(!element.getClientRects().length||style.visibility!=='visible'||
               element.closest('svg,script,style,[aria-hidden="true"],[disabled]')||
               /Material|icomoon/i.test(style.fontFamily))return;
            const backgrounds=[];let opacity=1;
            for(let node=element;node;node=node.parentElement){
                const current=getComputedStyle(node);opacity*=Number(current.opacity);
                backgrounds.push(current.backgroundColor);
            }
            if(!opacity)return;
            items.push({text:text.trim().slice(0,110),tag:element.tagName,
                foreground:style.color,backgrounds,opacity,fontSize:parseFloat(style.fontSize),
                fontWeight:parseInt(style.fontWeight)||400});
        }
        for(const root of document.querySelectorAll('[data-testid="stMain"],[data-testid="stSidebar"]')){
            const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
            while(walker.nextNode()){
                const node=walker.currentNode;
                if(node.textContent.trim())sample(node.parentElement,node.textContent);
            }
            for(const input of root.querySelectorAll('input')){
                if(input.value&&['number','text'].includes(input.type))sample(input,input.value);
            }
        }
        return items;
    }""")

    def rgba(value):
        values = [float(v) for v in re.findall(r"[0-9.]+", value)]
        assert len(values) in (3, 4), value
        return values[:3], values[3] if len(values) == 4 else 1

    def luminance(channels):
        values = [v / 255 for v in channels]
        return sum((v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4) * w
                   for v, w in zip(values, (.2126, .7152, .0722)))

    assert samples, "No HTML text samples were inspected"
    for item in samples:
        background = [255, 255, 255]
        for value in reversed(item.pop("backgrounds")):
            color, alpha = rgba(value)
            background = [c * alpha + b * (1 - alpha) for c, b in zip(color, background)]
        color, alpha = rgba(item["foreground"])
        alpha *= item["opacity"]
        foreground = [c * alpha + b * (1 - alpha) for c, b in zip(color, background)]
        low, high = sorted((luminance(foreground), luminance(background)))
        item.update(background=background, ratio=(high + .05) / (low + .05))
        large = item["fontSize"] >= 24 or (item["fontSize"] >= 18.6667 and item["fontWeight"] >= 700)
        item["required_ratio"] = 3 if large else 4.5
    failures = [item for item in samples if item["ratio"] < item["required_ratio"]]
    return {"samples": samples, "failures": failures,
            "minimum_ratio": min(item["ratio"] for item in samples),
            "scope": "Visible HTML text/input values, including offscreen scroll content. SVG/chart/canvas, hidden/decorative material icons and disabled controls excluded. Computed colors/background alpha and inherited opacity sampled; not a complete accessibility audit."}


def ax_snapshot(page, session):
    tree = session.send("Accessibility.getFullAXTree")
    exposed = [node for node in tree["nodes"] if not node.get("ignored")]
    controls = [{"role": node.get("role", {}).get("value"), "name": node.get("name", {}).get("value", ""),
                 "backend_node": node.get("backendDOMNodeId"), "properties": node.get("properties", [])}
                for node in exposed if node.get("role", {}).get("value") in
                ("button", "combobox", "slider", "spinbutton", "radio", "link", "textbox", "checkbox")]
    headings = page.get_by_test_id("stMain").locator("h1,h2,h3,h4,h5,h6").evaluate_all(
        "els=>els.filter(e=>e.getClientRects().length).map(e=>({level:Number(e.tagName[1]),text:e.innerText}))")
    unnamed = [control for control in controls if not control["name"].strip()]
    for control in unnamed:
        if control["backend_node"]:
            control["html"] = session.send("DOM.getOuterHTML", {"backendNodeId": control["backend_node"]})["outerHTML"][:2500]
    return {"tree": tree, "controls": controls, "headings": headings, "unnamed_controls": unnamed}


def accessibility(review, _):
    page = review.page
    session = page.context.new_cdp_session(page)
    session.send("Accessibility.enable")
    views, findings = [], []
    for view in VIEWS:
        review.navigate(view)
        snapshot = ax_snapshot(page, session)
        contrast = text_contrast(page)
        path = review.output / ("accessibility-" + view.lower().replace(" & ", "-") + ".json")
        path.write_text(json.dumps({"view": view, **snapshot, "contrast": contrast}, indent=2))
        headings = snapshot["headings"]
        heading_errors = (["Expected one main h1"] if sum(h["level"] == 1 for h in headings) != 1 else [])
        for previous, current in zip(headings, headings[1:]):
            if current["level"] > previous["level"] + 1:
                heading_errors.append(f"Heading level skipped: {previous} -> {current}")
        controls = snapshot["controls"]
        required = [("combobox", "Viewed policy"), ("button", "Applied inputs"), ("button", "Export")]
        missing = [name for role, name in required if not any(c["role"] == role and c["name"] == name for c in controls)]
        radio_names = {c["name"] for c in controls if c["role"] == "radio"}
        missing += [name for name in VIEWS if name not in radio_names]
        item = {"view": view, "raw_snapshot": path.name, "headings": headings,
                "controls": len(controls), "unnamed_controls": snapshot["unnamed_controls"],
                "missing_controls": missing, "heading_errors": heading_errors,
                "contrast_samples": len(contrast["samples"]), "minimum_text_ratio": contrast["minimum_ratio"],
                "contrast_failures": contrast["failures"]}
        views.append(item)
        if heading_errors or missing or snapshot["unnamed_controls"] or contrast["failures"]:
            findings.append(item)
    review.report["view_audits"] = views
    assert not findings, json.dumps(findings, indent=2)
    review.check("Five views expose named native controls and a continuous main heading hierarchy", views)
    review.check("Sampled visible HTML text and input values meet their normal/large text thresholds", {
        "samples": sum(v["contrast_samples"] for v in views),
        "minimum_ratio": min(v["minimum_text_ratio"] for v in views), "scope": contrast["scope"]})

    review.open_sidebar()
    for title in ("Capital & funding", "Credit assumptions", "Credit and cash limits", "Advanced economics"):
        review.expand(title)
    snapshot = ax_snapshot(page, session)
    financial = [c for c in snapshot["controls"] if c["role"] in ("slider", "spinbutton")]
    assert len(financial) == 18, financial
    assert all(c["name"].strip() for c in financial), financial
    review.check("All 18 financial inputs have accessible names when their editors are open", financial)

    metrics = review.metrics()
    page.get_by_role("spinbutton", name="Minimum month-end cash ($)", exact=True).fill("-100")
    page.get_by_role("button", name="Run scenario", exact=True).click()
    error = page.get_by_text(re.compile("Scenario could not run:"))
    expect(error).to_be_visible()
    review.ready()
    assert review.metrics() == metrics
    tree = session.send("Accessibility.getFullAXTree")
    nodes = {node["nodeId"]: node for node in tree["nodes"]}
    def content(node):
        return node.get("name", {}).get("value", "") + " " + " ".join(content(nodes[c]) for c in node.get("childIds", []) if c in nodes)
    alerts = [content(node) for node in tree["nodes"] if not node.get("ignored") and node.get("role", {}).get("value") == "alert"]
    assert any("Scenario could not run:" in alert for alert in alerts), alerts
    review.capture("invalid-input-alert", target=error)
    review.check("Invalid Run exposes an accessibility alert and retains the previous scenario", {"alerts": alerts, "metrics": metrics})
    page.get_by_role("button", name="Restore applied inputs", exact=True).click()
    review.ready()
    assert review.applied_run() == BASE_RUN
    session.detach()


def write_zoom_extension(directory):
    directory.mkdir()
    (directory / "manifest.json").write_text(json.dumps({"manifest_version": 3,
        "name": "Workbench native zoom test fixture", "version": "1.0",
        "host_permissions": ["http://127.0.0.1/*"], "background": {"service_worker": "background.js"}}))
    (directory / "background.js").write_text("chrome.runtime.onInstalled.addListener(() => {});\n")
    (directory / "control.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Native zoom test control</title>'
        '<label>Browser zoom factor <input id="factor" type="number" value="1" step="0.1"></label>'
        '<button id="apply">Set browser zoom</button><output id="result" role="status"></output>'
        '<script src="control.js"></script></html>')
    (directory / "control.js").write_text("""document.querySelector('#apply').addEventListener('click', async () => {
    const output=document.querySelector('#result');output.textContent='';
    try {
        const address=new URL(location.href).searchParams.get('target');
        if(new URL(address).hostname!=='127.0.0.1')throw Error('Only the local test server is allowed');
        const tabs=await chrome.tabs.query({});
        const tab=tabs.find(t=>t.url?.startsWith(address+'/'));
        if(!tab)throw Error('Local test tab not found');
        await chrome.tabs.setZoomSettings(tab.id,{mode:'automatic',scope:'per-tab'});
        await chrome.tabs.setZoom(tab.id,Number(document.querySelector('#factor').value));
        output.textContent=String(await chrome.tabs.getZoom(tab.id));
    } catch(error){output.textContent='ERROR: '+error.message;}
});\n""")


def zoom(review, controls):
    page, helper, factor = review.page, controls["page"], controls["factor"]
    baseline = viewport(page)
    helper.get_by_role("spinbutton", name="Browser zoom factor", exact=True).fill(str(factor))
    helper.get_by_role("button", name="Set browser zoom", exact=True).click()
    helper.wait_for_function("document.querySelector('#result').textContent.length>0")
    measured = helper.locator("#result").inner_text()
    assert measured == str(factor), measured
    page.bring_to_front()
    page.wait_for_function("expected=>Math.abs(devicePixelRatio-expected)<.02", arg=baseline["dpr"] * factor)
    enlarged = viewport(page)
    assert abs(enlarged["width"] * factor - baseline["width"]) <= factor, (baseline, enlarged)
    assert enlarged["visualScale"] == 1, enlarged
    review.ready()
    review.report["native_zoom"] = {"requested": factor, "chrome_reported": float(measured),
        "before": baseline, "after": enlarged, "mechanism": "Chrome automatic per-tab zoom; no CSS scaling, pinch zoom or viewport override."}
    review.check("Chrome reports the requested native zoom and the CSS viewport shrinks accordingly", review.report["native_zoom"])
    for view in VIEWS:
        review.navigate(view)
        geometry = review.geometry()
        assert page.get_by_role("radio", name=view, exact=True).is_checked()
        review.check(view + " reflows without measured main-area horizontal overflow", geometry)
        if view in ("Overview", "Policies"):
            review.capture(view.lower(), target=page.get_by_role("heading", name=view, exact=True))
    review.open_sidebar()
    equity = page.get_by_role("spinbutton", name="Starting equity cash ($)", exact=True)
    equity.fill("1250000")
    page.get_by_role("button", name="Run scenario", exact=True).click()
    expect(page.get_by_role("heading", name="Recommended policy: Balanced", exact=True)).to_be_visible()
    review.close_sidebar()
    review.policy("Balanced")
    assert review.applied_run() == "690e9fa563e2d475"
    review.check("Scaled native inputs apply a scenario and policy selection keeps the correct identity")
    page.get_by_role("button", name="Export", exact=True).click()
    with page.expect_download() as event:
        page.get_by_role("button", name="Decision brief", exact=True).click()
    download = event.value
    assert download.failure() is None
    path = review.output / (review.name + "-" + download.suggested_filename)
    download.save_as(path)
    assert "690e9fa563e2d475" in path.name and "690e9fa563e2d475" in path.read_text()
    review.capture("export")
    review.check("Export controls remain reachable and download the correct brief at native zoom", {"file": path.name, "bytes": path.stat().st_size})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "browser-accessibility")
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sources = [ROOT / "app.py", ROOT / ".streamlit/config.toml", *sorted((ROOT / "lending_simulator/ui").glob("*.py"))]
    report = {"created_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in sources},
        "scope": "Read-only browser AX/HTML audits and native 200%/400% Chrome zoom through a local-only test extension, against unchanged app.py. No accounts/hosting or app DOM/state injection. Not physical-device or full screen-reader/accessibility certification.",
        "cases": []}
    with live_server(ROOT, output / "streamlit.log") as address, sync_playwright() as engine, \
         tempfile.TemporaryDirectory(prefix="lending-native-zoom-") as directory:
        temporary = Path(directory)
        extension = temporary / "extension"
        write_zoom_extension(extension)
        for name, factor in (("accessibility", None), ("zoom-200", 2), ("zoom-400", 4)):
            case = {"name": name, "checks": [], "captures": [], "operations": []}
            report["cases"].append(case)
            browser = None
            if factor:
                context = engine.chromium.launch_persistent_context(str(temporary / name), channel="chromium",
                    headless=True, no_viewport=True, accept_downloads=True,
                    downloads_path=str(output / "native-downloads"), args=["--window-size=1280,900",
                    f"--disable-extensions-except={extension}", f"--load-extension={extension}"])
            else:
                browser = engine.chromium.launch(downloads_path=str(output / "native-downloads"))
                context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.set_default_timeout(15000)
            review = Review(page, output, name, case)
            try:
                page.goto(address, wait_until="domcontentloaded")
                review.ready()
                identity = context.new_cdp_session(page)
                case["browser"] = identity.send("Browser.getVersion")
                identity.detach()
                case["initial_viewport"] = viewport(page)
                if factor:
                    worker = context.service_workers[0] if context.service_workers else context.wait_for_event("serviceworker")
                    extension_id = worker.url.split("/")[2]
                    helper = context.new_page()
                    helper.goto(f"chrome-extension://{extension_id}/control.html?target={quote(address, safe='')}")
                    zoom(review, {"page": helper, "factor": factor})
                else:
                    accessibility(review, None)
                assert not review.console, review.console
                assert not review.requests, review.requests
                assert review.websockets, "No Streamlit WebSocket observed"
                review.check("No browser warnings/errors or failed requests; WebSocket connected")
                case["status"] = "passed"
            except Exception:
                case["status"] = "failed"
                case["error"] = traceback.format_exc()
                print(f"FAIL {name}: {case['error']}", flush=True)
                page.screenshot(path=str(output / (name + "-failure.png")), full_page=True)
                (output / (name + "-failure.txt")).write_text(page.locator("body").inner_text())
            finally:
                case.update(console=review.console, failed_requests=review.requests, websockets=review.websockets)
                context.tracing.stop(path=str(output / (name + "-trace.zip")))
                context.close()
                if browser:
                    browser.close()
                (output / "report.json").write_text(json.dumps(report, indent=2))
    failures = sum(case.get("status") != "passed" for case in report["cases"])
    print(f"Accessibility/zoom: {len(report['cases'])-failures} passed, {failures} failed. Evidence: {output}", flush=True)
    if failures or len(report["cases"]) != 3:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
