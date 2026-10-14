"""Production CLI integration: authenticate/reject, select v2, retain v1, clean up."""
import json
import os
import subprocess
import sys

from conftest import ROOT


def test_real_production_clients_and_auth_process_cleanup(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_production.py"), "--output-dir", str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=90,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert result.returncode == 0, result.stdout
    report = json.loads((tmp_path / "production_results.json").read_text(encoding="utf-8"))
    assert report["passed"] and report["auth_server_stopped"]
    assert report["invalid_token_http_statuses"] == [401]
    rejected = json.loads((tmp_path / "auth_fail.json").read_text(encoding="utf-8"))
    assert rejected["status"] == "failed" and "tools" not in rejected
    for filename in ["auth_ok.json", "auth_fail.json", "auth-ok.txt", "auth-fail.txt"]:
        text = (tmp_path / filename).read_text(encoding="utf-8-sig")
        assert "dev-token-abc123" not in text and "wrong-token" not in text and "Authorization" not in text
