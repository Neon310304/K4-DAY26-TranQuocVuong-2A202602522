"""Actual local MCP stdio/HTTP and ADK discovery, with no external APIs."""
import asyncio
import json
import sys

import httpx
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from conftest import ROOT, load_module
from lab_support import local_server


def error_leaves(error):
    if isinstance(error, BaseExceptionGroup):
        return [leaf for child in error.exceptions for leaf in error_leaves(child)]
    return [error]


def test_real_http_handshake_and_health(verify, server_url):
    report = asyncio.run(verify.verify_protocol(server_url))
    assert report["status"] == "passed"
    assert report["tools"] == sorted(verify.REQUIRED_TOOLS)
    assert report["health"]["weather_api_configured"] is False
    assert report["health"]["weather_api_verified"] is False


def test_http_404_is_not_a_pass(verify, server_url):
    with pytest.raises(Exception):
        asyncio.run(verify.verify_protocol(server_url + "/wrong-path"))


def test_unreachable_server_is_not_a_pass(verify):
    with pytest.raises(Exception):
        asyncio.run(verify.verify_protocol("http://127.0.0.1:1/mcp"))


def test_missing_tools_rejected(verify):
    code = '''from mcp.server.mcpserver import MCPServer
import uvicorn
server = MCPServer("unrelated")
uvicorn.run(server.streamable_http_app(stateless_http=True, json_response=True),
            host="127.0.0.1", port={PORT})
'''
    with local_server(code=code) as url:
        with pytest.raises(Exception) as caught:
            asyncio.run(verify.verify_protocol(url))
        assert any(isinstance(e, RuntimeError) and "weather tools missing" in str(e)
                   for e in error_leaves(caught.value))


def test_health_tool_is_error_rejected(verify):
    code = '''from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
import uvicorn
server = MCPServer("bad-health")
@server.tool()
def get_current_weather(city: str) -> str: return "unused"
@server.tool()
def get_forecast(city: str, days: int = 3) -> str: return "unused"
@server.tool()
def health_check() -> str: raise ToolError("unhealthy")
uvicorn.run(server.streamable_http_app(stateless_http=True, json_response=True),
            host="127.0.0.1", port={PORT})
'''
    with local_server(code=code) as url:
        with pytest.raises(Exception) as caught:
            asyncio.run(verify.verify_protocol(url))
        assert any(isinstance(e, RuntimeError) and "isError" in str(e)
                   for e in error_leaves(caught.value))


def test_adk_performs_actual_discovery(verify, server_url):
    report = asyncio.run(verify.verify_adk_discovery(server_url))
    assert report["tools"] == sorted(verify.REQUIRED_TOOLS)


def test_adk_import_is_not_connection_evidence(verify):
    from weather_agent.agent import root_agent
    assert root_agent.name == "weather_agent"
    with pytest.raises(Exception):
        asyncio.run(verify.verify_adk_discovery("http://127.0.0.1:1/mcp"))


def test_stdio_schema_and_errors():
    async def check():
        params = StdioServerParameters(command=sys.executable,
                                      args=[str(ROOT / "04-lab/mcp-server/weather.py"), "--transport", "stdio"],
                                      env={"WEATHERAPI_KEY": ""})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = {t.name: t for t in (await session.list_tools()).tools}
                days = tools["get_forecast"].input_schema["properties"]["days"]
                assert days["minimum"] == 1 and days["maximum"] == 3
                assert tools["get_forecast"].annotations.read_only_hint
                assert not (await session.call_tool("health_check", {})).is_error
                assert (await session.call_tool("get_forecast", {"city": "Hanoi", "days": 0})).is_error
                assert (await session.call_tool("get_current_weather", {"city": "Hanoi"})).is_error
    asyncio.run(check())


def test_auth_missing_invalid_valid():
    code = '''import sys
sys.path.insert(0, "03-production")
from auth_server import mcp
import uvicorn
uvicorn.run(mcp.streamable_http_app(stateless_http=True, json_response=True),
            host="127.0.0.1", port={PORT})
'''
    async def authorized(url):
        async with create_mcp_http_client(headers={"Authorization": "Bearer lab-auth-test"}) as client:
            async with streamable_http_client(url, http_client=client) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("get_weather", {"city": "Hanoi"})
                    assert not result.is_error and "29°C" in result.content[0].text
    with local_server(code=code, env={"MCP_AUTH_TOKEN": "lab-auth-test"}) as url:
        body = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                           "clientInfo": {"name": "auth-test", "version": "1"}}}
        headers = {"Accept": "application/json, text/event-stream"}
        assert httpx.post(url, json=body, headers=headers).status_code == 401
        assert httpx.post(url, json=body,
                          headers={**headers, "Authorization": "Bearer invalid-test"}).status_code == 401
        asyncio.run(authorized(url))


def test_safe_evidence_error_redacts_raw_exception(verify):
    error = httpx.ConnectError("URL has secret=test-do-not-save")
    report = verify.safe_error(ExceptionGroup("raw-secret", [error]))
    assert "secret" not in json.dumps(report)
    assert report["errors"][0]["type"] == "ConnectError"


def test_registry_selects_active_latest():
    registry = load_module("lab_registry", "03-production/registry_client.py")
    match = registry.ToolRegistry().best_match(tag="weather")
    assert match["tool"] == "get_weather_v2"
    assert match["version"] == "2.0.0" and not match["deprecated"]
