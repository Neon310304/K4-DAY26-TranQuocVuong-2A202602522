"""Step 02: real subprocess protocol and selection by discovered metadata."""
import ast
import asyncio
import json
from types import SimpleNamespace

import pytest

from conftest import ROOT, load_module


def test_actual_stdio_description_schema_and_three_results(tmp_path):
    client = load_module("basics_stdio_client", "02-mcp-basics/weather_client.py")
    output = tmp_path / "stdio.json"
    report = asyncio.run(client.main(output))
    assert json.loads(output.read_text(encoding="utf-8")) == report
    tree = ast.parse((ROOT / "02-mcp-basics/weather_server.py").read_text(encoding="utf-8"))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "get_weather")
    tool = report["tools"][0]
    assert report["server"] == "weather"
    assert tool["description"] == ast.get_docstring(function)
    assert tool["input_schema"]["properties"]["city"]["type"] == "string"
    assert tool["input_schema"]["required"] == ["city"]
    assert [(row["arguments"]["city"], row["text"]) for row in report["calls"]] == [
        ("Hanoi", "Hanoi: 29°C, trời mưa"),
        ("Danang", "Danang: 30°C, nhiều mây"),
        ("Haiphong", "Haiphong: 33°C, mưa rào"),
    ]
    assert all(not row["is_error"] for row in report["calls"])


def test_remote_name_is_selected_and_ambiguous_discovery_is_rejected():
    client = load_module("basics_discovery_client", "02-mcp-basics/weather_client.py")
    weather = SimpleNamespace(name="renamed_remote_weather", input_schema={
        "properties": {"city": {"type": "string"}}, "required": ["city"],
    })
    unrelated = SimpleNamespace(name="get_weather", input_schema={
        "properties": {"latitude": {"type": "number"}}, "required": ["latitude"],
    })
    assert client.select_weather_tool([unrelated, weather]).name == "renamed_remote_weather"
    with pytest.raises(RuntimeError):
        client.select_weather_tool([unrelated])
    with pytest.raises(RuntimeError):
        client.select_weather_tool([weather, weather])
