"""ADK weather agent. Construction is lazy; verify_setup performs real discovery."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8085/mcp")
REQUIRED_TOOLS = {"get_current_weather", "get_forecast", "health_check"}


def create_model():
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "gemini":
        return os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
    if provider == "yescale-gemini":
        from google.adk.models import Gemini
        from .gemini_gateway import GatewayGemini
        model_class = Gemini if os.getenv("GEMINI_STREAMING", "0").lower() in {"1", "true"} else GatewayGemini
        return model_class(
            model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
            base_url=os.getenv("GEMINI_BASE_URL", "https://api.yescale.io"),
            client_kwargs={"api_key": os.getenv("YESCALE_API_KEY", ""), "vertexai": False},
        )
    if provider in {"yescale", "openai-compatible"}:
        os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
        from google.adk.models.lite_llm import LiteLlm
        return LiteLlm(
            model="openai/" + os.getenv("LLM_MODEL", "gpt-4o-mini"),
            api_base=os.getenv("YESCALE_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.yescale.io/v1"),
            api_key=os.getenv("YESCALE_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
            timeout=45, num_retries=0,
        )
    raise ValueError("LLM_PROVIDER must be gemini, yescale-gemini, yescale or openai-compatible")


def create_toolset(url: str | None = None) -> McpToolset:
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=url or MCP_SERVER_URL, timeout=30.0),
        tool_filter=sorted(REQUIRED_TOOLS),
    )


weather_tools = create_toolset()
root_agent = Agent(
    name="weather_agent",
    model=create_model(),
    instruction=(
        "Bạn là trợ lý thời tiết. Luôn gọi get_current_weather cho thời tiết hiện tại, "
        "get_forecast cho dự báo (chỉ 1–3 ngày), health_check cho tình trạng server. "
        "Trả lời bằng tiếng Việt, dựa trên kết quả tool và ghi thời điểm dữ liệu nếu có. "
        "Nếu tool lỗi hoặc mất kết nối, nói rõ chưa lấy được dữ liệu và hướng khắc phục. "
        "Không tự bịa nhiệt độ, dự báo hay coi lỗi tool là dữ liệu thời tiết."
    ),
    tools=[weather_tools],
)

