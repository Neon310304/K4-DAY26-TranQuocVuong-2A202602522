# Weather Agent — Google ADK + MCP

Agent dùng `McpToolset` qua Streamable HTTP. ADK điều phối khám phá schema, model chọn tool, gọi MCP và đưa kết quả trở lại model. LLM có thể là **Gemini native qua YesScale**, Google trực tiếp hoặc model tương thích OpenAI qua LiteLLM; WeatherAPI là dịch vụ thời tiết riêng ở server.

## Chạy từ gốc repo

```bash
uv sync --locked --project 04-lab/mcp-client --python 3.12
```

Tạo `04-lab/mcp-client/.env` từ [.env.example](.env.example) nếu chưa có; giữ key ở file được Git ignore.

| Biến | Giá trị / ý nghĩa |
|---|---|
| `LLM_PROVIDER` | `yescale` (mẫu mặc định), `yescale-gemini`, `openai-compatible` hoặc `gemini` |
| `LLM_MODEL` | ID model tương thích OpenAI; mẫu dùng `gemini-2.5-flash`, code fallback khi không đặt biến là `gpt-4o-mini` |
| `YESCALE_API_KEY` | Key YesScale; có thể dùng `OPENAI_API_KEY` khi cấu hình endpoint riêng |
| `YESCALE_BASE_URL` | Endpoint YesScale, mặc định `https://api.yescale.io/v1` |
| `GOOGLE_API_KEY` | Chỉ cần khi dùng Google trực tiếp (`gemini`) |
| `GOOGLE_MODEL` | Mặc định `gemini-2.5-flash` |
| `GEMINI_BASE_URL` | Host Gemini gateway, mặc định mẫu `https://api.yescale.io`; không thêm `/v1` |
| `GEMINI_STREAMING` | `0`: gateway trả response đầy đủ; `1`: bật provider token streaming |
| `MCP_SERVER_URL` | Mặc định `http://127.0.0.1:8085/mcp` |

Không cần cùng lúc key Google và YesScale. Với `yescale-gemini`, Google SDK dùng `YESCALE_API_KEY` và Gemini endpoint `/v1beta`; không cần `GOOGLE_API_KEY`. Server cần `WEATHERAPI_KEY` riêng để current/forecast trả dữ liệu thật. Env được load theo thư mục project, shell env được ưu tiên.

Cấu hình mẫu dùng Gemini qua endpoint tương thích OpenAI của YesScale và LiteLLM vì phiên native trên web gặp 503. Native Gemini qua YesScale vẫn có evidence thành công từ Runner; [browser evidence](../../reports/evidence/adk_web_chat.json) ghi rõ adapter, function calls/responses và model ID trả về.

Sau khi bật server ở terminal khác theo [hướng dẫn lab](../README.md):

```bash
# MCP initialize → list_tools → health_check và ADK get_tools; không gọi LLM
uv run --project 04-lab/mcp-client python 04-lab/mcp-client/verify_setup.py

# LLM thật chọn health_check → MCP → LLM trả lời; có chi phí API
uv run --project 04-lab/mcp-client python 04-lab/mcp-client/verify_setup.py --live-agent

# Cần cả LLM key và WeatherAPI key; gọi current/forecast thật
uv run --project 04-lab/mcp-client python 04-lab/mcp-client/verify_setup.py --live-agent --live-weather

# Chạy web ở thư mục client
uv run --directory 04-lab/mcp-client adk web
```

Mở `http://localhost:8000` và chọn `weather_agent`. Các lệnh checker trên có `--output PATH` để lưu evidence JSON; lệnh tổng ở gốc `scripts/check_lab.py` tự quản lý server tạm và evidence.

Nếu cổng 8000 bận, chạy `uv run --directory 04-lab/mcp-client adk web --port 8001` rồi mở `http://127.0.0.1:8001`. Đây là cấu hình đã dùng cho ảnh browser của bài; MCP server vẫn dùng 8085.

## Bước 5 — hai phiên chat với thời tiết thật

Giữ server 8085 chạy. Env client đã có key YesScale thì dùng tiếp, không ghi đè bằng `echo ... > .env`. Cấu hình của các ảnh browser là `LLM_PROVIDER=yescale`, `LLM_MODEL=gemini-2.5-flash`, endpoint tương thích OpenAI qua LiteLLM; response events cũng ghi `gemini-2.5-flash`. Đây vẫn là Google ADK điều phối MCP, nhưng adapter model khác constructor Gemini native trong starter.

Từ gốc repo:

```powershell
uv sync --locked --project 04-lab/mcp-client --python 3.12
uv run --project 04-lab/mcp-client python 04-lab/mcp-client/verify_setup.py --server-url http://127.0.0.1:8085/mcp --output reports/evidence/step05_verify_setup.json
uv run --directory 04-lab/mcp-client adk web --port 8001
```

Nếu ADK 8001 đã chạy thì mở phiên hiện có, không khởi động thêm process trên cùng cổng. Chọn weather_agent, tạo hai sessions riêng và hỏi:

1. “Hãy gọi get_current_weather với city Hanoi, rồi báo thời tiết hiện tại và thời điểm cập nhật.”
2. “Hãy gọi get_forecast với city Hanoi và days 3. Trả lời bằng tiếng Việt, liệt kê đúng từng ngày, nhiệt độ cao nhất/thấp nhất, khả năng mưa và UV theo dữ liệu tool.”

Đối chiếu functionCall → functionResponse `isError=false` → final answer. Một câu trả lời trôi chảy hoặc tên tool trong text chưa chứng minh tool đã chạy.

| Evidence Bước 5 | Kết quả và phạm vi |
|---|---|
| [04-verify-setup.png](../../screenshots/04-verify-setup.png), [JSON](../../reports/evidence/step05_verify_setup.json), [stdout](../../reports/evidence/step05_verify_setup.txt) | Dependencies, MCP handshake/health và ADK discovery đạt. Không gọi LLM/WeatherAPI ở preflight; ảnh là output thật trong trình duyệt, chưa phải cửa sổ terminal |
| [04-adk-current.png](../../screenshots/04-adk-current.png), [events](../../reports/evidence/adk_web_chat.json) | Phiên current thành công đã có: 33.9°C, feels-like 35.9°C, humidity 42%, UV 1.0, Last updated 2026-10-14 16:30. Chụp lại cùng session, không gọi API current thêm |
| [04-adk-forecast.png](../../screenshots/04-adk-forecast.png), [events](../../reports/evidence/adk_web_forecast.json), [SSE gốc](../../reports/evidence/adk_web_forecast.sse.txt) | Phiên browser mới gọi get_forecast(Hanoi, 3), trả ba ngày 14/15/16-10; cao/thấp, khả năng mưa và UV của final answer khớp tool response |

Forecast bao gồm hôm nay và hai ngày tiếp theo, không phải ba ngày bắt đầu từ ngày mai. Output tool forecast hiện không có Last updated; không suy timestamp cập nhật từ ngày dự báo hoặc giờ chụp ảnh. Các con số trên là kết quả đã lưu, không ép lần chạy sau trùng chúng.

### Khác biệt của bản repo so với hướng dẫn starter

| Hướng dẫn starter | Code đang dùng |
|---|---|
| `.env` chứa GOOGLE_API_KEY | Cấu hình YesScale đã chạy dùng YESCALE_API_KEY; Google key chỉ cần khi chọn provider gemini trực tiếp |
| GET `/mcp` có mã dưới 500 được coi là đạt | verify_setup thực hiện MCP initialize/list_tools/health và ADK get_tools thật; GET không đủ |
| In `All checks passed!` | In trạng thái từng check và Scope. `mcp_protocol: passed` cùng `adk_discovery: passed` là kết quả thực tế |
| Constructor lỗi thì tạo fallback agent không có tool | Không âm thầm tạo agent thiếu tool; discovery phải đạt và runtime tool lỗi phải được báo |
| ADK web 8000 | Thực nghiệm dùng 8001 vì Docker đang giữ 8000; MCP vẫn ở 8085 |

`llm_credentials: not_run`, `live_agent: not_run`, `live_weather: not_run` trong preflight là đúng phạm vi không gọi API ngoài. Hai artifacts browser riêng mới chứng minh LLM/MCP/WeatherAPI execution. Không chỉnh các trạng thái not_run thành passed để làm preflight giống một lần live test.

## Cách đọc lỗi

- **404:** sai route `/mcp` hoặc đang gọi app khác; checker phải fail.
- **GET trả 400/405/406:** chưa đủ để kết luận MCP tốt/xấu. MCP cần handshake đúng; dùng checker.
- **Connection refused / timeout:** kiểm tra process, port và URL ở hai phía.
- **Thiếu tool / health isError:** checker fail; không coi HTTP 200 là đạt.
- **Missing WEATHERAPI_KEY:** health có thể vẫn ready, nhưng current/forecast trả tool error.
- **LLM 401/403/429:** kiểm tra key, quyền/model và quota ở provider; không in key vào logs.
- **LLM 503 sau tool response:** provider chưa tổng hợp được câu trả lời; không phải bằng chứng WeatherAPI/MCP lỗi nếu tool đã trả `isError=false`. Giữ phiên lỗi, thử phiên mới có giới hạn; không coi dòng chữ mô phỏng tool call là function call thật.
- **Import thành công:** chỉ chứng minh cấu hình lazy được tạo; `get_tools()` mới thử kết nối.

Agent không âm thầm chuyển sang mode không có tools khi constructor lỗi. Khi tool runtime lỗi, instruction yêu cầu báo chưa có dữ liệu; mức tuân thủ của model cần xem evidence live, không thể chứng minh chỉ từ instruction.

ADK 2.12.0 hiện có warnings về MCP experimental/deprecated trong chính SDK; đây là dependency warning, không thay thế trạng thái pass/fail của thực nghiệm.

Dependencies và lockfile: [pyproject.toml](pyproject.toml), [uv.lock](uv.lock). SDK v2 dùng snake_case ở Python (`is_error`, `input_schema`, `structured_content`); JSON wire vẫn theo MCP schema.
