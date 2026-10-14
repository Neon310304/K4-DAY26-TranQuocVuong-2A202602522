"""WeatherAPI tools over MCP v2. Logs go to stderr, including in stdio mode."""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Annotated, Any

import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

load_dotenv(Path(__file__).with_name(".env"), override=False)
logger = logging.getLogger(__name__)
mcp = MCPServer("weather", version="1.1.0")
WEATHERAPI_BASE = "https://api.weatherapi.com/v1"
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                            idempotentHint=True, openWorldHint=True)
City = Annotated[str, Field(min_length=1, max_length=200,
                           description="City name, e.g. Hanoi or Sydney")]
Days = Annotated[int, Field(ge=1, le=3, description="Forecast days: 1 to 3")]


def validate_city(city: str) -> str:
    if any(ord(char) < 32 for char in city):
        raise ToolError("city must not contain control characters.")
    city = city.strip()
    if not city or len(city) > 200 or any(ord(char) < 32 for char in city):
        raise ToolError("city must be a nonempty city name of at most 200 characters.")
    return city


async def make_weather_request(endpoint: str, params: dict[str, str]) -> dict[str, Any]:
    """Do not include URLs, keys, response bodies or raw exceptions in errors."""
    api_key = os.getenv("WEATHERAPI_KEY", "").strip()
    if not api_key:
        raise ToolError("WEATHERAPI_KEY is missing. Configure mcp-server/.env and restart the server.")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{WEATHERAPI_BASE}/{endpoint}",
                headers={"User-Agent": "day26-weather/1.1"},
                params={**params, "key": api_key},
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or "error" in data:
                raise ValueError("invalid weather response")
            return data
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        logger.warning("WeatherAPI HTTP status %d", status)
        raise ToolError(f"WeatherAPI returned HTTP {status}. Check city, key and account quota.") from None
    except httpx.RequestError:
        logger.warning("WeatherAPI network request failed")
        raise ToolError("WeatherAPI is unreachable or timed out. Try again later.") from None
    except (ValueError, TypeError):
        raise ToolError("WeatherAPI returned an invalid response. Try again later.") from None


@mcp.tool(annotations=READ_ONLY)
async def get_current_weather(city: City) -> str:
    """Fetch current observed weather from WeatherAPI. Raises a tool error on failure."""
    data = await make_weather_request("current.json", {"q": validate_city(city), "aqi": "no"})
    try:
        current, location = data["current"], data["location"]
        return (
            f"Current Weather for {location['name']}, {location['region']}, {location['country']}:\n"
            f"Temperature: {current['temp_c']}°C ({current['temp_f']}°F)\n"
            f"Feels like: {current['feelslike_c']}°C ({current['feelslike_f']}°F)\n"
            f"Condition: {current['condition']['text']}\nHumidity: {current['humidity']}%\n"
            f"Wind: {current['wind_kph']} km/h ({current['wind_mph']} mph) {current['wind_dir']}\n"
            f"Pressure: {current['pressure_mb']} mb\nUV Index: {current['uv']}\n"
            f"Visibility: {current['vis_km']} km\nLast updated: {current['last_updated']}"
        )
    except (KeyError, TypeError):
        raise ToolError("WeatherAPI current-weather fields are missing. Try again later.") from None


@mcp.tool(annotations=READ_ONLY)
async def get_forecast(city: City, days: Days = 3) -> str:
    """Fetch a 1–3 day forecast from WeatherAPI; days outside this range are rejected."""
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 3:
        raise ToolError("days must be an integer from 1 to 3.")
    data = await make_weather_request("forecast.json", {
        "q": validate_city(city), "days": str(days), "aqi": "no", "alerts": "no",
    })
    try:
        location = data["location"]
        forecasts = [f"Weather Forecast for {location['name']}, {location['region']}, {location['country']}:"]
        forecast_days = data["forecast"]["forecastday"]
        if len(forecast_days) != days:
            raise ValueError("incomplete forecast")
        for day in forecast_days:
            values = day["day"]
            forecasts.append(
                f"{day['date']}:\nHigh: {values['maxtemp_c']}°C ({values['maxtemp_f']}°F)\n"
                f"Low: {values['mintemp_c']}°C ({values['mintemp_f']}°F)\n"
                f"Condition: {values['condition']['text']}\n"
                f"Chance of Rain: {values['daily_chance_of_rain']}%\n"
                f"Max Wind: {values['maxwind_kph']} km/h\nUV Index: {values['uv']}"
            )
        return "\n---\n".join(forecasts)
    except (KeyError, TypeError, ValueError):
        raise ToolError("WeatherAPI forecast fields are missing or incomplete. Try again later.") from None


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                                     idempotentHint=True, openWorldHint=False))
async def health_check() -> dict[str, Any]:
    """Check MCP readiness and key presence. This does not call or validate WeatherAPI."""
    return {"status": "ok", "weather_api_configured": bool(os.getenv("WEATHERAPI_KEY", "").strip()),
            "weather_api_verified": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="streamable-http")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8085")))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logger.info("Starting weather MCP: transport=%s", args.transport)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn
        app = mcp.streamable_http_app(stateless_http=True, json_response=True, host=args.host)
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
