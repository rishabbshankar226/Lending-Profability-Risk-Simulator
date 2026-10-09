"""Real HTTP readiness, separate from AppTest and real-browser verification."""

from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

import pytest


def test_streamlit_server_serves_health_and_frontend(tmp_path):
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with (tmp_path / "server.log").open("w+b") as logs:
        server = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py",
             "--server.address", "127.0.0.1", "--server.port", str(port),
             "--server.headless", "true", "--server.fileWatcherType", "none"],
            cwd=root, stdin=subprocess.DEVNULL, stdout=logs, stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 30
            healthy = False
            while time.monotonic() < deadline and server.poll() is None:
                try:
                    with opener.open(base_url + "/_stcore/health", timeout=1) as response:
                        healthy = response.status == 200 and response.read().strip() == b"ok"
                    if healthy:
                        break
                except OSError:
                    pass
                time.sleep(.1)
            if not healthy:
                logs.seek(0)
                pytest.fail("Streamlit failed HTTP readiness:\n" + logs.read().decode(errors="replace")[-4000:])
            with opener.open(base_url + "/", timeout=5) as response:
                assert response.status == 200
                assert response.headers.get_content_type() == "text/html"
                assert b"<html" in response.read().lower()
        finally:
            if server.poll() is None:
                server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
