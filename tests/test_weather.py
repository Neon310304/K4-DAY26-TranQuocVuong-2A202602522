"""Deterministic WeatherAPI contracts. All external weather responses are mocked."""
import asyncio

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError


@pytest.mark.parametrize("city", ["", "   ", "x" * 201, "Hanoi\n"])
def test_invalid_city_never_calls_api(weather, monkeypatch, city):
    async def unexpected(*args):
        pytest.fail("Invalid city reached WeatherAPI")
    monkeypatch.setattr(weather, "make_weather_request", unexpected)
    with pytest.raises(ToolError):
        asyncio.run(weather.get_current_weather(city))


@pytest.mark.parametrize("days", [0, -1, 4, True, 1.5])
def test_forecast_days_never_silently_clamp(weather, monkeypatch, days):
    async def unexpected(*args):
        pytest.fail("Invalid days reached WeatherAPI")
    monkeypatch.setattr(weather, "make_weather_request", unexpected)
    with pytest.raises(ToolError):
        asyncio.run(weather.get_forecast("Hanoi", days))


def test_missing_key_is_tool_error(weather, monkeypatch):
    monkeypatch.delenv("WEATHERAPI_KEY", raising=False)
    with pytest.raises(ToolError, match="WEATHERAPI_KEY is missing"):
        asyncio.run(weather.make_weather_request("current.json", {"q": "Hanoi"}))
    assert asyncio.run(weather.health_check()) == {
        "status": "ok", "weather_api_configured": False, "weather_api_verified": False}


@pytest.mark.parametrize("failure", ["http403", "timeout", "invalid_json"])
def test_error_messages_and_logs_never_include_key(weather, monkeypatch, caplog, failure):
    secret = "test-weather-secret-must-never-appear"
    monkeypatch.setenv("WEATHERAPI_KEY", secret)
    params = {"q": "Hanoi"}
    original_client = httpx.AsyncClient
    def handler(request):
        assert request.url.params["key"] == secret
        if failure == "timeout":
            raise httpx.ReadTimeout(f"failure {secret}", request=request)
        if failure == "invalid_json":
            return httpx.Response(200, text=secret)
        return httpx.Response(403, text=secret)
    monkeypatch.setattr(weather.httpx, "AsyncClient",
                        lambda **kw: original_client(transport=httpx.MockTransport(handler), **kw))
    with pytest.raises(ToolError) as error:
        asyncio.run(weather.make_weather_request("current.json", params))
    assert secret not in str(error.value)
    assert secret not in caplog.text
    assert params == {"q": "Hanoi"}


def test_current_weather_formats_provider_data(weather, monkeypatch):
    async def response(endpoint, params):
        assert endpoint == "current.json" and params["q"] == "Hanoi"
        return {"location": {"name": "Hanoi", "region": "Ha Noi", "country": "Vietnam"},
                "current": {"temp_c": 25, "temp_f": 77, "feelslike_c": 26, "feelslike_f": 78.8,
                            "condition": {"text": "Cloudy"}, "humidity": 80,
                            "wind_kph": 10, "wind_mph": 6.2, "wind_dir": "NE",
                            "pressure_mb": 1010, "uv": 1, "vis_km": 10,
                            "last_updated": "2026-10-14 09:00"}}
    monkeypatch.setattr(weather, "make_weather_request", response)
    result = asyncio.run(weather.get_current_weather(" Hanoi "))
    assert "25°C (77°F)" in result and "2026-10-14 09:00" in result


def test_incomplete_provider_fields_are_tool_error(weather, monkeypatch):
    async def response(*args):
        return {"location": {}}
    monkeypatch.setattr(weather, "make_weather_request", response)
    with pytest.raises(ToolError, match="fields are missing"):
        asyncio.run(weather.get_current_weather("Hanoi"))


def test_forecast_formats_each_day(weather, monkeypatch):
    async def response(endpoint, params):
        assert endpoint == "forecast.json" and params["days"] == "2"
        day = {"maxtemp_c": 30, "maxtemp_f": 86, "mintemp_c": 20, "mintemp_f": 68,
               "condition": {"text": "Sunny"}, "daily_chance_of_rain": 5,
               "maxwind_kph": 12, "uv": 7}
        return {"location": {"name": "Hanoi", "region": "Ha Noi", "country": "Vietnam"},
                "forecast": {"forecastday": [{"date": "2026-10-14", "day": day},
                                            {"date": "2026-10-15", "day": day}]}}
    monkeypatch.setattr(weather, "make_weather_request", response)
    result = asyncio.run(weather.get_forecast("Hanoi", 2))
    assert "2026-10-14" in result and "2026-10-15" in result
    assert result.count("Chance of Rain: 5%") == 2
