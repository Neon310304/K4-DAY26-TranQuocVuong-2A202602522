"""Minh hoạ FUNCTION CALLING thuần với Google Gemini SDK.

Tool `get_weather` được định nghĩa schema thủ công VÀ thực thi ngay trong
chính file app này. Model chỉ QUYẾT ĐỊNH gọi tool nào; app mới là nơi chạy.

Cách chạy:
    pip install -r ../requirements.txt
    export GEMINI_API_KEY=...
    python weather_function_calling.py
"""

from google import genai
from google.genai import types
import os
from pathlib import Path
from dotenv import load_dotenv
import argparse
import hashlib
import json
from datetime import datetime, timezone

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thân thiện, trả lời bằng tiếng Việt tự nhiên. "
    "Dùng emoji phù hợp (🌧️ 🌤️ 💨 💧). "
    "Tóm tắt ngắn gọn, dễ hiểu, và đưa ra lời khuyên thực tế "
    "(ví dụ: mang ô, mặc áo mỏng, ...)."
)

# 1. App tự định nghĩa schema của tool
get_weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Lấy thời tiết hiện tại của một thành phố",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING, description="Tên thành phố"
            )
        },
        required=["city"],
    ),
)

TOOLS = [types.Tool(function_declarations=[get_weather_declaration])]


# 2. App tự thực thi tool (trong thực tế sẽ gọi API thời tiết thật)
def get_weather(city: str) -> str:
    """Trả về thời tiết (mock) của *city*. Dùng làm tool cho model."""
    mock_data = {
        "Hà Nội": {
            "nhiệt_độ": "29°C",
            "thời_tiết": "trời mưa nhẹ",
            "độ_ẩm": "82%",
            "gió": {"hướng": "Đông Nam", "tốc_độ": "12 km/h"},
        },
        "Hồ Chí Minh": {
            "nhiệt_độ": "33°C",
            "thời_tiết": "mưa rào",
            "độ_ẩm": "75%",
            "gió": {"hướng": "Tây Nam", "tốc_độ": "15 km/h"},
        },
        "Đà Nẵng": {
            "nhiệt_độ": "30°C",
            "thời_tiết": "nhiều mây",
            "độ_ẩm": "78%",
            "gió": {"hướng": "Đông", "tốc_độ": "10 km/h"},
        },
    }
    import json

    default = {"nhiệt_độ": "28°C", "thời_tiết": "không có dữ liệu chi tiết"}
    return json.dumps({"city": city, **mock_data.get(city, default)}, ensure_ascii=False)


def run(prompt: str, trace: dict | None = None) -> str:
    """Model chọn tool; app thực thi. GEMINI_BASE_URL hỗ trợ gateway như YesScale."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    base_url = os.getenv("GEMINI_BASE_URL") or None
    options = types.HttpOptions(base_url=base_url, timeout=60000)
    config = types.GenerateContentConfig(
        tools=TOOLS, system_instruction=SYSTEM_INSTRUCTION + " Dữ liệu tool là mock của lab; ghi rõ khi trả lời.",
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
    calls = []
    with genai.Client(api_key=key, http_options=options) as client:
        for _ in range(4):
            resp = client.models.generate_content(model=MODEL, contents=contents, config=config)
            if not resp.function_calls:
                if not calls or not resp.text:
                    raise RuntimeError("Gemini did not complete a function-call round trip")
                if trace is not None:
                    trace.update({"format_version": 1, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                  "status": "passed", "scope": "live_google_genai_manual_function_calling_with_mock_weather",
                                  "gateway": "yescale" if base_url and "yescale" in base_url else "configured_or_google_default",
                                  "request_model": MODEL, "response_model": resp.model_version,
                                  "tool_calls": calls, "final_response": resp.text,
                                  "source_hashes": {"01-function-calling/weather_function_calling.py":
                                      hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}})
                return resp.text
            contents.append(resp.candidates[0].content)
            function_responses = []
            for fc in resp.function_calls:
                if fc.name != "get_weather":
                    raise ValueError("Unknown function requested by Gemini")
                print(f"  [model yêu cầu] {fc.name}({fc.args})")
                result = get_weather(**fc.args)  # APP thực thi tool ngay tại đây.
                print(f"  [app thực thi]  -> {result}")
                calls.append({"name": fc.name, "arguments": dict(fc.args), "result": json.loads(result)})
                function_responses.append(types.Part.from_function_response(name=fc.name, response={"result": result}))
            contents.append(types.Content(role="user", parts=function_responses))
    raise RuntimeError("Gemini function-call round limit exceeded")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Save evidence without credentials.")
    args = parser.parse_args()
    question = "Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"
    print(f"User: {question}\n")
    trace = {}
    try:
        print("Trả lời:", run(question, trace))
    except Exception as error:
        print("Function calling failed:", type(error).__name__)
        raise SystemExit(1)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
