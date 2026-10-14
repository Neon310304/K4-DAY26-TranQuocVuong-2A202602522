"""MCP Client có Authentication — kết nối tới auth_server.py qua HTTP.

Client tạo HTTP client bằng create_mcp_http_client(headers=...) của MCP SDK
(đúng thư viện HTTP mà SDK dùng bên dưới, kèm timeout khuyến nghị). Header
Authorization được gắn vào mọi request HTTP (POST, GET, DELETE) tới server.

Cách chạy (cần auth_server.py đang chạy ở terminal khác):
    cd 03-production
    python auth_server.py            # terminal 1
    python auth_client.py            # terminal 2
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import os

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

SERVER_URL = os.environ.get("MCP_AUTH_SERVER_URL", "http://localhost:8000/mcp")
TOKEN = os.environ.get("MCP_AUTH_TOKEN", "dev-token-abc123")


async def main(trace: dict | None = None) -> dict:
    trace = trace if trace is not None else {}
    trace["http_statuses"] = []

    async def record_status(response):
        trace["http_statuses"].append(response.status_code)

    http_client = create_mcp_http_client(
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    http_client.event_hooks["response"].append(record_status)

    async with http_client:
        async with streamable_http_client(SERVER_URL, http_client=http_client) as (
            read,
            write,
        ):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()

                tools = await session.list_tools()
                print("Tools (có auth):")
                for t in tools.tools:
                    print(f"  - {t.name}: {t.description}")

                result = await session.call_tool("get_weather", {"city": "Hanoi"})
                if result.is_error:
                    raise RuntimeError("Authenticated MCP tool returned an error")
                print(f"\nKết quả: {result.content[0].text}")
                return {"status": "passed", "server": initialized.server_info.name,
                        "tools": [t.name for t in tools.tools], "is_error": result.is_error,
                        "result": result.content[0].text}


def safe_error(error: BaseException) -> list[dict]:
    """SDK errors can contain request details; record only type and status."""
    if isinstance(error, BaseExceptionGroup):
        return [row for child in error.exceptions for row in safe_error(child)]
    row = {"type": type(error).__name__}
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        row["http_status"] = status
    return [row]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Save evidence without tokens or raw SDK errors.")
    args = parser.parse_args()
    trace = {}
    try:
        report = asyncio.run(main(trace))
    except Exception as error:
        errors = safe_error(error)
        report = {"status": "failed", "errors": errors}
        statuses = sorted({status for status in trace.get("http_statuses", []) if status >= 400})
        print("Authentication/transport failed:", ", ".join(f"HTTP {status}" for status in statuses)
              or ", ".join(row["type"] for row in errors))
    root = Path(__file__).resolve().parents[1]
    report.update({**trace, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                   "scope": "actual_mcp_http_bearer_demo_with_mock_weather", "url": SERVER_URL,
                   "source_hashes": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                     for name in ["03-production/auth_client.py", "03-production/auth_server.py"]}})
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if report["status"] == "passed" else 1)
