"""Run Day26 production demos locally; save real outputs and stop auth server."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def run_client(script: str, output: Path, env: dict | None = None):
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(ROOT / "03-production" / script), "--output", str(output)],
        cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})},
        capture_output=True, text=True, encoding="utf-8", timeout=45,
    )
    # Raw child SDK stderr is intentionally excluded; auth_client records safe errors.
    return result.returncode, result.stdout


def run_demos(output_dir: Path, auth_port: int = 0) -> dict:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", auth_port))
        port = reservation.getsockname()[1]
    url = f"http://127.0.0.1:{port}/mcp"
    demo_env = {"MCP_AUTH_HOST": "127.0.0.1", "MCP_AUTH_PORT": str(port),
                "MCP_AUTH_SERVER_URL": url, "MCP_AUTH_TOKEN": "dev-token-abc123",
                "PYTHONIOENCODING": "utf-8"}
    with tempfile.TemporaryFile(mode="w+b") as server_log:
        server = subprocess.Popen(
            [sys.executable, "-u", "-X", "utf8", str(ROOT / "03-production/auth_server.py")],
            cwd=ROOT, env={**os.environ, **demo_env}, stdout=server_log, stderr=server_log,
        )
        try:
            deadline = time.monotonic() + 15
            while True:
                if server.poll() is not None:
                    raise RuntimeError("Auth server exited during startup")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Auth server startup timed out")
                    time.sleep(0.05)
            ok_exit, ok_text = run_client("auth_client.py", output_dir / "auth_ok.json", demo_env)
            if ok_exit != 0:
                raise RuntimeError("Authorized auth_client failed")
            (output_dir / "auth-ok.txt").write_text(f"Endpoint: {url}\n\n" + ok_text, encoding="utf-8-sig")
            fail_exit, fail_text = run_client("auth_client.py", output_dir / "auth_fail.json",
                                              {**demo_env, "MCP_AUTH_TOKEN": "wrong-token"})
            if fail_exit == 0:
                raise RuntimeError("Invalid token unexpectedly succeeded")
            body = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-11-25", "capabilities": {},
                "clientInfo": {"name": "day26-auth-check", "version": "1"},
            }}
            missing_status = httpx.post(url, json=body, timeout=10,
                                       headers={"Accept": "application/json, text/event-stream"}).status_code
        finally:
            # Windows virtualenv launchers may own a Python child; stop our whole tree.
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(server.pid), "/T", "/F"],
                               capture_output=True, timeout=10)
            else:
                server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
            server_log.seek(0)
            access_lines = [line for line in server_log.read().decode("utf-8", errors="replace").splitlines()
                            if '"POST /mcp HTTP/1.1"' in line]
    stopped = False
    cleanup_deadline = time.monotonic() + 5
    while time.monotonic() < cleanup_deadline:
        with socket.socket() as probe:
            probe.settimeout(0.2)
            stopped = server.poll() is not None and probe.connect_ex(("127.0.0.1", port)) != 0
        if stopped:
            break
        time.sleep(0.05)
    auth_stdout = f"Endpoint: {url}\n\n{fail_text}\nServer access log (actual POST requests):\n"
    auth_stdout += "\n".join(access_lines) + "\n"
    (output_dir / "auth-fail.txt").write_text(auth_stdout, encoding="utf-8-sig")
    for script in ["registry_client.py", "versioned_client.py"]:
        name = script.removesuffix(".py")
        exit_code, stdout = run_client(script, output_dir / (name + ".json"))
        (output_dir / (name + ".txt")).write_text(stdout, encoding="utf-8-sig")
        if exit_code:
            raise RuntimeError(f"Production demo {script} failed")
    ok = json.loads((output_dir / "auth_ok.json").read_text(encoding="utf-8"))
    fail = json.loads((output_dir / "auth_fail.json").read_text(encoding="utf-8"))
    registry = json.loads((output_dir / "registry_client.json").read_text(encoding="utf-8"))
    versioning = json.loads((output_dir / "versioned_client.json").read_text(encoding="utf-8"))
    invalid_statuses = sorted({status for status in fail["http_statuses"] if status >= 400})
    checks = {
        "authorized_initialize_list_and_call": ok["status"] == "passed" and "get_weather" in ok["tools"],
        "invalid_token_rejected": fail["status"] == "failed" and invalid_statuses == [401],
        "missing_token_rejected": missing_status == 401,
        "auth_server_stopped": stopped,
        "registry_two_weather_matches": len(registry["weather_matches"]) == 2,
        "registry_active_v2_selected": registry["best_match"]["tool"] == "get_weather_v2"
                                       and registry["best_match"]["version"] == "2.0.0"
                                       and not registry["best_match"]["deprecated"],
        "version_metadata": versioning["metadata"]["version"] == "2.0.0"
                            and versioning["metadata"]["deprecated_tools"] == ["get_weather"],
        "legacy_v1_works": not versioning["v1"]["is_error"] and versioning["v1"]["result"].startswith("Hanoi: 29"),
        "v2_forecast_works": versioning["v2_forecast"]["result"]["api_version"] == "2.0"
                             and len(versioning["v2_forecast"]["result"]["forecast"]) == 2,
        "v2_optional_defaults_work": versioning["v2_defaults"]["result"]["units"] == "celsius"
                                     and "forecast" not in versioning["v2_defaults"]["result"],
    }
    sources = ["03-production/auth_server.py", "03-production/auth_client.py",
               "03-production/registry_client.py", "03-production/registry.json",
               "03-production/versioned_client.py", "03-production/versioned_server.py",
               "scripts/run_production.py"]
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "three_actual_local_production_demos_mock_weather_no_llm",
              "auth_url": url, "auth_server_pid": server.pid, "auth_server_exit_code": server.returncode,
              "auth_server_stopped": stopped, "missing_token_http_status": missing_status,
              "invalid_token_http_statuses": invalid_statuses, "checks": checks,
              "passed": all(checks.values()), "native_terminal_screenshots_captured": False,
              "source_hashes": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources}}
    (output_dir / "production_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                                        encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-port", type=int, default=0, help="0 selects a free local port; use 8000 if available.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/evidence")
    args = parser.parse_args()
    report = run_demos(args.output_dir, args.auth_port)
    for name, passed in report["checks"].items():
        print(name + ":", "passed" if passed else "failed")
    print("Auth endpoint:", report["auth_url"])
    print("Evidence:", args.output_dir / "production_results.json")
    raise SystemExit(0 if report["passed"] else 1)
