"""Native Gemini SDK dispatch and ADK gateway setup; mocks never call a provider."""
import asyncio
import sys
from types import SimpleNamespace

import pytest
from google.genai import types

from conftest import ROOT, load_module


def test_gemini_sdk_keeps_tool_execution_in_app(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-only")
    monkeypatch.setenv("GEMINI_BASE_URL", "https://gateway.example")
    module = load_module("lab_native_gemini", "01-function-calling/weather_function_calling.py")
    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["api_key"] == "unit-test-only"
            assert kwargs["http_options"].base_url == "https://gateway.example"
            self.models = SimpleNamespace(generate_content=self.generate)
            self.calls = 0
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def generate(self, **kwargs):
            assert kwargs["config"].automatic_function_calling.disable
            self.calls += 1
            if self.calls == 1:
                part = types.Part(function_call=types.FunctionCall(name="get_weather", args={"city": "Hà Nội"}))
                return SimpleNamespace(function_calls=[part.function_call], candidates=[
                    SimpleNamespace(content=types.Content(role="model", parts=[part]))])
            result = kwargs["contents"][-1].parts[0].function_response
            assert result.name == "get_weather" and "29°C" in result.response["result"]
            return SimpleNamespace(function_calls=None, text="Mock Hanoi 29°C", model_version="mock-gemini")
    monkeypatch.setattr(module.genai, "Client", FakeClient)
    trace = {}
    assert module.run("Hà Nội", trace) == "Mock Hanoi 29°C"
    assert trace["tool_calls"][0]["name"] == "get_weather"


def test_adk_gemini_gateway_uses_yescale_key_without_google_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "yescale-gemini")
    monkeypatch.setenv("YESCALE_API_KEY", "unit-test-only")
    monkeypatch.setenv("GEMINI_BASE_URL", "https://gateway.example")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from weather_agent.agent import create_model
    model = create_model()
    assert model.base_url == "https://gateway.example"
    assert model.client_kwargs["api_key"] == "unit-test-only"
    assert model.client_kwargs["vertexai"] is False


def test_gateway_disables_provider_streaming_for_adk_web(monkeypatch):
    from google.adk.models import Gemini
    from weather_agent.gemini_gateway import GatewayGemini
    async def fake_generate(self, request, stream=False):
        assert stream is False
        yield "complete-response"
    monkeypatch.setattr(Gemini, "generate_content_async", fake_generate)
    async def check():
        return [item async for item in GatewayGemini().generate_content_async(None, stream=True)]
    assert asyncio.run(check()) == ["complete-response"]
