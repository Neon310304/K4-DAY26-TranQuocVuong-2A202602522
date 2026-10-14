#!/usr/bin/env python3
"""Verify real MCP discovery; optionally call WeatherAPI and the configured LLM."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

PROJECT_DIR = Path(__file__).resolve().parent
REPO_DIR = PROJECT_DIR.parents[1]
REQUIRED_TOOLS = {"get_current_weather", "get_forecast", "health_check"}


def configured(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value) and not value.startswith(("your_", "replace_"))


def check_environment() -> dict:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    keys = {
        "gemini": configured("GOOGLE_API_KEY") or configured("GEMINI_API_KEY"),
        "yescale": configured("YESCALE_API_KEY") or configured("OPENAI_API_KEY"),
        "yescale-gemini": configured("YESCALE_API_KEY"),
        "openai-compatible": configured("YESCALE_API_KEY") or configured("OPENAI_API_KEY"),
    }
    return {"provider": provider, "llm_key_configured": keys.get(provider, False)}


def safe_error(exc: BaseException) -> dict:
    """Record types/status only: raw SDK exceptions may contain URLs or secrets."""
    leaves = []
    def visit(error):
        if isinstance(error, BaseExceptionGroup):
            for child in error.exceptions:
                visit(child)
        else:
            row = {"type": type(error).__name__}
            response = getattr(error, "response", None)
            if isinstance(getattr(response, "status_code", None), int):
                row["http_status"] = response.status_code
            leaves.append(row)
    visit(exc)
    return {"errors": leaves, "hint": "Check server process, /mcp path, transport, dependencies and credentials."}


def result_text(result) -> str:
    return "\n".join(item.text for item in result.content if hasattr(item, "text"))


async def verify_protocol(url: str, live_weather: bool = False) -> dict:
    from mcp import ClientSession
    from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

    async with create_mcp_http_client(timeout=30) as client:
        async with streamable_http_client(url, http_client=client) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=30) as session:
                initialized = await session.initialize()
                names = {tool.name for tool in (await session.list_tools()).tools}
                missing = REQUIRED_TOOLS - names
                if missing:
                    raise RuntimeError("Required weather tools missing")
                health = await session.call_tool("health_check", {})
                if health.is_error:
                    raise RuntimeError("health_check returned isError")
                data = health.structured_content or json.loads(result_text(health))
                if data.get("status") != "ok":
                    raise RuntimeError("MCP health is not ok")
                report = {"status": "passed", "server": initialized.server_info.name,
                          "protocol_version": initialized.protocol_version,
                          "tools": sorted(names), "health": data}
                if live_weather:
                    outputs = {}
                    for tool, arguments in [
                        ("get_current_weather", {"city": "Hanoi"}),
                        ("get_forecast", {"city": "Hanoi", "days": 3}),
                    ]:
                        result = await session.call_tool(tool, arguments)
                        if result.is_error:
                            raise RuntimeError("WeatherAPI tool failed; see server configuration")
                        outputs[tool] = result_text(result)
                    report["live_weather"] = {"status": "passed", "outputs": outputs}
                return report


async def verify_adk_discovery(url: str | None = None) -> dict:
    # Import creates a lazy toolset; get_tools is the actual network operation.
    from weather_agent.agent import root_agent, create_toolset
    weather_tools = create_toolset(url)
    try:
        tools = await weather_tools.get_tools()
        names = {tool.name for tool in tools}
        if not REQUIRED_TOOLS <= names:
            raise RuntimeError("ADK did not discover all required tools")
        return {"status": "passed", "agent": root_agent.name, "tools": sorted(names)}
    finally:
        await weather_tools.close()


async def verify_live_agent(tool: str) -> dict:
    from google.adk.agents.run_config import RunConfig
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from weather_agent.agent import root_agent, weather_tools

    # Discovery uses a separate toolset; this agent's toolset is still unused.
    sessions = InMemorySessionService()
    await sessions.create_session(app_name="weather_agent", user_id="lab-check", session_id="preflight")
    runner = Runner(agent=root_agent, app_name="weather_agent", session_service=sessions)
    prompts = {
        "health_check": "Gọi health_check để kiểm tra server. Nêu rõ API thời tiết đã được xác minh chưa.",
        "get_current_weather": "Hãy gọi get_current_weather với city Hanoi, rồi báo thời tiết hiện tại và thời điểm cập nhật.",
    }
    calls, responses, final_text = [], [], ""
    try:
        async for event in runner.run_async(
            user_id="lab-check", session_id="preflight",
            new_message=types.Content(role="user", parts=[types.Part(text=prompts[tool])]),
            run_config=RunConfig(max_llm_calls=4),
        ):
            calls.extend(call.name for call in event.get_function_calls())
            for response in event.get_function_responses():
                payload = response.response or {}
                if payload.get("isError") or payload.get("is_error") or payload.get("error"):
                    raise RuntimeError("Agent MCP tool returned an error")
                responses.append(response.name)
            if event.is_final_response() and event.content:
                final_text = "\n".join(part.text for part in event.content.parts if part.text)
        if tool not in calls or tool not in responses or not final_text:
            raise RuntimeError("LLM did not complete the requested MCP tool round trip")
        return {"status": "passed", "requested_tool": tool, "tool_calls": calls,
                "tool_responses": responses, "final_response": final_text}
    finally:
        await weather_tools.close()


def source_hashes() -> dict:
    relative_paths = [
        "04-lab/mcp-server/weather.py", "04-lab/mcp-server/pyproject.toml",
        "04-lab/mcp-server/uv.lock", "04-lab/mcp-client/verify_setup.py",
        "04-lab/mcp-client/weather_agent/gemini_gateway.py",
        "04-lab/mcp-client/weather_agent/agent.py", "04-lab/mcp-client/pyproject.toml",
        "04-lab/mcp-client/uv.lock",
    ]
    return {name: hashlib.sha256((REPO_DIR / name).read_bytes()).hexdigest() for name in relative_paths}


async def run_checks(args) -> dict:
    report = {"format_version": 1, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "configuration": check_environment(),
              "source_hashes": source_hashes(), "checks": {}}
    report["configuration"]["model"] = (
        os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
        if report["configuration"]["provider"] in {"gemini", "yescale-gemini"}
        else os.getenv("LLM_MODEL", "gpt-4o-mini")
    )
    dependencies = {}
    for module, distribution in [("mcp", "mcp"), ("google.adk", "google-adk"),
                                 ("google.genai", "google-genai"), ("dotenv", "python-dotenv"),
                                 ("httpx", "httpx"), ("litellm", "litellm")]:
        try:
            importlib.import_module(module)
            dependencies[distribution] = importlib.metadata.version(distribution)
        except ImportError:
            dependencies[distribution] = "missing"
    report["dependencies"] = dependencies
    report["checks"]["dependencies"] = {"status": "failed" if "missing" in dependencies.values() else "passed"}
    report["checks"]["llm_credentials"] = {
        "status": ("passed" if report["configuration"]["llm_key_configured"] else "failed") if args.live_agent else "not_run",
        "scope": "presence only; API execution is a separate check",
    }
    for name, operation in [
        ("mcp_protocol", lambda: verify_protocol(args.server_url, args.live_weather)),
        ("adk_discovery", lambda: verify_adk_discovery(args.server_url)),
    ]:
        try:
            report["checks"][name] = await operation()
        except Exception as exc:
            report["checks"][name] = {"status": "failed", **safe_error(exc)}
    if args.live_agent:
        if report["configuration"]["llm_key_configured"] and report["checks"]["mcp_protocol"]["status"] == "passed":
            try:
                report["checks"]["live_agent"] = await asyncio.wait_for(
                    verify_live_agent("get_current_weather" if args.live_weather else "health_check"), timeout=120)
            except Exception as exc:
                report["checks"]["live_agent"] = {"status": "failed", **safe_error(exc)}
        else:
            report["checks"]["live_agent"] = {"status": "failed", "hint": "Configure the LLM key and fix MCP first."}
    else:
        report["checks"]["live_agent"] = {"status": "not_run"}
    if not args.live_weather:
        report["checks"]["live_weather"] = {"status": "not_run"}
    else:
        report["checks"]["live_weather"] = {"status": report["checks"]["mcp_protocol"]["status"]}
    report["passed"] = all(check["status"] != "failed" for check in report["checks"].values())
    report["scope"] = "mcp_protocol_and_adk_discovery"
    if args.live_agent:
        report["scope"] += "_with_live_llm"
    if args.live_weather:
        report["scope"] += "_and_live_weatherapi"
    return report


def main() -> int:
    load_dotenv(PROJECT_DIR / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-url", default=os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8085/mcp"))
    parser.add_argument("--live-weather", action="store_true", help="Calls WeatherAPI through the server (needs WEATHERAPI_KEY there).")
    parser.add_argument("--live-agent", action="store_true", help="Calls configured Gemini/YesScale model; may incur charges.")
    parser.add_argument("--output", type=Path, help="Save evidence JSON; keys/raw exceptions are excluded.")
    args = parser.parse_args()
    os.environ["MCP_SERVER_URL"] = args.server_url
    if str(PROJECT_DIR) not in sys.path:
        sys.path.insert(0, str(PROJECT_DIR))
    report = asyncio.run(run_checks(args))
    for name, result in report["checks"].items():
        print(f"{name}: {result['status']}")
    print(f"Scope: {report['scope']}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Evidence saved: {args.output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

