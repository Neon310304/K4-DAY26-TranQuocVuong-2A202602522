"""MCP CLIENT minh hoạ — kết nối tới weather_server.py qua giao thức MCP.

Điểm mấu chốt: client KHÔNG hard-code tool. Nó hỏi server "anh có tool gì?"
(list_tools) tại runtime, rồi gọi tool (call_tool) để SERVER thực thi và trả
kết quả về qua MCP.

Ví dụ này không cần ANTHROPIC_API_KEY — nó cho thấy lớp giao thức MCP hoạt
động độc lập với model. (Trong thực tế, một LLM sẽ dùng Function Calling để
quyết định khi nào gọi tool đã khám phá được.)

Cách chạy (cùng thư mục với weather_server.py, client tự khởi động server):
    pip install -r ../requirements.txt
    python weather_client.py
"""

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def select_weather_tool(tools):
    """The demo knows city input; the callable name comes from discovery."""
    matches = []
    for tool in tools:
        schema = tool.input_schema
        required = set(schema.get("required", []))
        city = schema.get("properties", {}).get("city", {})
        if city.get("type") == "string" and required == {"city"}:
            matches.append(tool)
    if len(matches) != 1:
        raise RuntimeError("Expected one discovered tool requiring city:string; inspect list_tools metadata.")
    return matches[0]


async def main(output: Path | None = None) -> dict:
    # Dùng đúng interpreter đang chạy client (tránh lỗi "python" không tồn tại)
    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name("weather_server.py"))])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()

            # 1. KHÁM PHÁ tool mà server công bố (không hard-code)
            tools = await session.list_tools()
            print("Tools server cung cấp:")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")
            weather_tool = select_weather_tool(tools.tools)

            # 2. Gọi tool — SERVER thực thi rồi trả kết quả về qua MCP
            calls = []
            for city in ["Hanoi", "Danang", "Haiphong"]:
                result = await session.call_tool(weather_tool.name, {"city": city})
                if result.is_error:
                    raise RuntimeError(f"MCP tool failed for city={city!r}")
                text = "\n".join(item.text for item in result.content if hasattr(item, "text"))
                if not text:
                    raise RuntimeError("MCP tool returned no text")
                print(f"\ncall_tool {weather_tool.name}(city={city!r}):")
                print("  ->", text)
                calls.append({"tool": weather_tool.name, "arguments": {"city": city},
                              "is_error": result.is_error, "text": text})

    root = Path(__file__).resolve().parents[1]
    sources = ["02-mcp-basics/weather_client.py", "02-mcp-basics/weather_server.py"]
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "status": "passed",
              "scope": "actual_mcp_stdio_discovery_and_three_mock_weather_calls_no_llm",
              "server": initialized.server_info.name, "protocol_version": initialized.protocol_version,
              "tools": [{"name": t.name, "description": t.description,
                         "input_schema": t.input_schema, "output_schema": t.output_schema}
                        for t in tools.tools],
              "calls": calls, "source_hashes": {
                  name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources}}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Save discovered schemas and actual tool results.")
    asyncio.run(main(parser.parse_args().output))
