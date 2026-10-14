"""Shared local-server lifecycle for integration tests and the lab checker."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def local_server(script: Path | None = None, *, code: str | None = None, env: dict | None = None):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    if code:
        command = [sys.executable, "-c", code.replace("{PORT}", str(port))]
    else:
        command = [sys.executable, str(script or ROOT / "04-lab/mcp-server/weather.py"),
                   "--transport", "streamable-http", "--port", str(port)]
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})}
    # Temporary stderr is intentionally not embedded into evidence (may contain SDK diagnostics).
    with tempfile.TemporaryFile(mode="w+b") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=environment,
                                   stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Local MCP server exited during startup")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    time.sleep(0.05)
            else:
                raise TimeoutError("Local MCP server did not start")
            yield f"http://127.0.0.1:{port}/mcp"
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
