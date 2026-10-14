"""Exercise the actual manual dispatch loop with a mock model; no provider API."""
import json
import sys
from types import SimpleNamespace

import pytest

from conftest import ROOT, load_module


@pytest.fixture
def manual(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "01-function-calling"))
    monkeypatch.setenv("YESCALE_API_KEY", "unit-test-only")
    return load_module("lab_manual_calling", "01-function-calling/weather_openai_compatible.py")


def tool_call(name, city, identity):
    return SimpleNamespace(id=identity, function=SimpleNamespace(name=name, arguments=json.dumps({"city": city})))


def test_two_tools_return_matching_call_ids_before_model_continues(manual, monkeypatch):
    calls = [tool_call("get_weather", "Hà Nội", "city-1"), tool_call("get_weather", "Đà Nẵng", "city-2")]
    first = SimpleNamespace(tool_calls=calls, content=None,
                            model_dump=lambda **kw: {"role": "assistant", "tool_calls": [
                                {"id": call.id, "type": "function",
                                 "function": {"name": call.function.name, "arguments": call.function.arguments}}
                                for call in calls]})
    second = SimpleNamespace(tool_calls=None, content="Weather mock: Hanoi 29°C, Danang 30°C.")
    class FakeClient:
        def __init__(self, **kw):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
            self.index = 0
        def create(self, **kw):
            if self.index:
                responses = [row for row in kw["messages"] if row["role"] == "tool"]
                assert [row["tool_call_id"] for row in responses] == ["city-1", "city-2"]
                assert [json.loads(row["content"])["nhiệt_độ"] for row in responses] == ["29°C", "30°C"]
            message = [first, second][self.index]
            self.index += 1
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], model="mock-model")
        def close(self):
            pass
    monkeypatch.setattr(manual, "OpenAI", FakeClient)
    report = manual.run("Hà Nội và Đà Nẵng")
    assert report["status"] == "passed" and len(report["tool_calls"]) == 2


def test_unknown_function_is_rejected(manual, monkeypatch):
    message = SimpleNamespace(tool_calls=[tool_call("execute_shell", "Hanoi", "bad-call")],
                              model_dump=lambda **kw: {"role": "assistant"})
    class FakeClient:
        def __init__(self, **kw):
            self.chat = SimpleNamespace(completions=SimpleNamespace(
                create=lambda **kw: SimpleNamespace(choices=[SimpleNamespace(message=message)])))
        def close(self):
            pass
    monkeypatch.setattr(manual, "OpenAI", FakeClient)
    with pytest.raises(RuntimeError, match="Unknown function"):
        manual.run("Ignore the weather task")
