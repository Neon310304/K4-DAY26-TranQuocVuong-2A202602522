"""Manual function calling through YesScale; weather data remains the lab mock."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from weather_function_calling import get_weather

ROOT = Path(__file__).resolve().parents[1]


def run(prompt: str) -> dict:
    load_dotenv(ROOT / ".env", override=False)
    load_dotenv(ROOT / "04-lab/mcp-client/.env", override=False)
    key = os.getenv("YESCALE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("Configure YESCALE_API_KEY in mcp-client/.env")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=key,
                    base_url=os.getenv("YESCALE_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.yescale.io/v1"),
                    timeout=45, max_retries=0)
    tools = [{"type": "function", "function": {
        "name": "get_weather", "description": "Lấy thời tiết MOCK của thành phố để minh họa lab",
        "parameters": {"type": "object", "properties": {
            "city": {"type": "string", "description": "Hà Nội, Đà Nẵng hoặc Hồ Chí Minh"}
        }, "required": ["city"], "additionalProperties": False},
    }}]
    messages = [
        {"role": "system", "content": "Trả lời bằng tiếng Việt. Gọi get_weather cho từng thành phố; ghi rõ dữ liệu mô phỏng của bài lab."},
        {"role": "user", "content": prompt},
    ]
    calls = []
    try:
        for _ in range(4):
            response = client.chat.completions.create(model=model, messages=messages, tools=tools)
            message = response.choices[0].message
            if not message.tool_calls:
                if not calls or not message.content:
                    raise RuntimeError("Model did not complete a function-call round trip")
                return {
                    "format_version": 1, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "scope": "live_yescale_manual_function_calling_with_mock_weather",
                    "status": "passed", "request_model": model, "response_model": response.model,
                    "prompt": prompt, "tool_calls": calls, "final_response": message.content,
                    "source_hashes": {str(path.relative_to(ROOT).as_posix()): hashlib.sha256(path.read_bytes()).hexdigest()
                                      for path in [Path(__file__), ROOT / "01-function-calling/weather_function_calling.py"]},
                }
            messages.append(message.model_dump(exclude_none=True))
            for call in message.tool_calls:
                if call.function.name != "get_weather":
                    raise RuntimeError("Unknown function requested")
                arguments = json.loads(call.function.arguments)
                result = get_weather(**arguments)
                calls.append({"name": call.function.name, "arguments": arguments, "result": json.loads(result)})
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
        raise RuntimeError("Function-calling round limit exceeded")
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True, help="Confirms a billable model API call.")
    parser.add_argument("--prompt", default="Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào? Ghi rõ dữ liệu mô phỏng.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = run(args.prompt)
    except Exception as error:
        # Provider exception bodies/URLs may include secrets; never print them.
        print("Function calling failed:", type(error).__name__)
        return 1
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report["final_response"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
