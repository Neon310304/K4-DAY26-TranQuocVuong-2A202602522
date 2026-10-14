"""Reproducible Day26 local checks. Live APIs are opt-in and separately evidenced."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from lab_support import ROOT, local_server


def run_command(command: list[str], timeout: int = 180) -> dict:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout,
                            env={**os.environ, "PYTHONIOENCODING": "utf-8",
                                 "LITELLM_LOCAL_MODEL_COST_MAP": "True"})
    return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-agent", action="store_true")
    parser.add_argument("--live-weather", action="store_true")
    parser.add_argument("--skip-tests", action="store_true", help="Use only when tests already ran against the same sources.")
    args = parser.parse_args()
    evidence = ROOT / "reports/evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    report = {"format_version": 1, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "scope": "local_day26_checks", "checks": {}}
    if not args.skip_tests:
        test = run_command([sys.executable, "-m", "pytest", "tests", "-q",
                            "--junitxml=" + str(evidence / "pytest.xml")])
        (evidence / "pytest.txt").write_text(test["stdout"] + test["stderr"], encoding="utf-8")
        report["checks"]["tests"] = {"status": "passed" if test["exit_code"] == 0 else "failed",
                                     "evidence": "reports/evidence/pytest.xml"}
        print("tests:", report["checks"]["tests"]["status"], flush=True)
    else:
        report["checks"]["tests"] = {"status": "not_run"}
    for directory, script in [
        ("02-mcp-basics", "weather_client.py"),
        ("03-production", "versioned_client.py"),
        ("03-production", "registry_client.py"),
    ]:
        result = run_command([sys.executable, str(ROOT / directory / script)])
        (evidence / (script.removesuffix(".py") + ".txt")).write_text(
            result["stdout"] + result["stderr"], encoding="utf-8")
        report["checks"][script] = {"status": "passed" if result["exit_code"] == 0 else "failed"}
        print(script + ":", report["checks"][script]["status"], flush=True)
    with local_server() as url:
        output = evidence / ("live_setup.json" if args.live_agent or args.live_weather else "local_setup.json")
        command = [sys.executable, str(ROOT / "04-lab/mcp-client/verify_setup.py"),
                   "--server-url", url, "--output", str(output)]
        if args.live_agent:
            command.append("--live-agent")
        if args.live_weather:
            command.append("--live-weather")
        result = run_command(command, timeout=180)
        # Never echo/store child SDK diagnostics from live requests.
        report["checks"]["setup"] = {"status": "passed" if result["exit_code"] == 0 else "failed",
                                    "evidence": output.relative_to(ROOT).as_posix()}
        print("setup:", report["checks"]["setup"]["status"], flush=True)
    sources = []
    for folder in ["01-function-calling", "02-mcp-basics", "03-production",
                   "04-lab/mcp-server", "04-lab/mcp-client", "scripts", "tests"]:
        sources.extend(path for path in (ROOT / folder).rglob("*.py")
                       if ".venv" not in path.parts and "__pycache__" not in path.parts)
    report["source_hashes"] = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in sorted(sources)}
    report["passed"] = all(row["status"] != "failed" for row in report["checks"].values())
    filename = "live_checks.json" if args.live_agent or args.live_weather else "local_checks.json"
    (evidence / filename).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Evidence:", (evidence / filename).relative_to(ROOT))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
