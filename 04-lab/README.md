# Lab 04 — ADK agent và Weather MCP

Luồng: user → ADK → model (YesScale hoặc Gemini) → MCP Client → Streamable HTTP → Weather MCP → WeatherAPI → kết quả tool → model tổng hợp. YesScale thay **LLM**, không thay WeatherAPI. Weather tool của lab này dùng REST thật; tests contract dùng response mock.

## Tools và readiness

| Tool | Hợp đồng |
|---|---|
| `get_current_weather(city)` | Thành phố không rỗng, tối đa 200 ký tự; trả điều kiện hiện tại và thời điểm cập nhật |
| `get_forecast(city, days=3)` | 1–3 ngày; không âm thầm clamp tham số sai |
| `health_check()` | MCP ready + key có được cấu hình không; **không xác minh key hoặc gọi WeatherAPI** |

Lỗi key, mạng, provider hoặc dữ liệu thiếu trở thành MCP tool error. Agent được hướng dẫn báo thiếu dữ liệu và không tự bịa thời tiết. Import agent chỉ tạo toolset lazy; `verify_setup.py` gọi discovery thật để kiểm tra kết nối.

## Cài đặt từ gốc repo

Yêu cầu Python ≥ 3.12, uv. Cả hai lệnh cài sử dụng lockfile đã commit:

```bash
uv sync --locked --project 04-lab/mcp-server --python 3.12
uv sync --locked --project 04-lab/mcp-client --python 3.12
```

Tạo env **một lần**, không ghi đè file đã có. PowerShell:

```powershell
if (!(Test-Path 04-lab/mcp-server/.env)) { Copy-Item 04-lab/mcp-server/.env.example 04-lab/mcp-server/.env }
if (!(Test-Path 04-lab/mcp-client/.env)) { Copy-Item 04-lab/mcp-client/.env.example 04-lab/mcp-client/.env }
```

Bash:

```bash
test -f 04-lab/mcp-server/.env || cp 04-lab/mcp-server/.env.example 04-lab/mcp-server/.env
test -f 04-lab/mcp-client/.env || cp 04-lab/mcp-client/.env.example 04-lab/mcp-client/.env
```

Điền `WEATHERAPI_KEY` ở server từ [WeatherAPI](https://www.weatherapi.com/). Ở client chọn:

| Provider | Biến cần thiết |
|---|---|
| Gemini qua YesScale native (Runner đã chạy) | `LLM_PROVIDER=yescale-gemini`, `YESCALE_API_KEY`, `GEMINI_BASE_URL=https://api.yescale.io`, `GOOGLE_MODEL=gemini-2.5-flash`, `GEMINI_STREAMING=0` |
| Gemini qua YesScale/LiteLLM (web đã chạy, mẫu mặc định) | `LLM_PROVIDER=yescale`, `YESCALE_API_KEY`, `YESCALE_BASE_URL=https://api.yescale.io/v1`, `LLM_MODEL=gemini-2.5-flash` |
| Gemini | `LLM_PROVIDER=gemini`, `GOOGLE_API_KEY` từ [Google AI Studio](https://aistudio.google.com/apikey), `GOOGLE_MODEL=gemini-2.5-flash` |

`yescale-gemini` dùng Google ADK/Gemini native, không dùng LiteLLM. Key YesScale thay Google key ở cấu hình này. `GEMINI_STREAMING=0` tắt token streaming tại gateway; ADK vẫn stream các events về web. Adapter này đã hoàn tất tool round trip qua Runner; kết quả browser được ghi riêng trong báo cáo, không bảo đảm mọi request provider đều thành công.

Browser native gặp 503 sau response tool, kể cả khi tắt provider streaming. Phiên browser thành công dùng LiteLLM và vẫn yêu cầu `gemini-2.5-flash`; events cũng ghi model ID này. Xem [adk_web_chat.json](../reports/evidence/adk_web_chat.json) và [ảnh response tool](../screenshots/04-adk-tool-response.png). Không cần Google key riêng để dùng Gemini qua YesScale.

Tên model là ID gửi cho provider; không coi alias là snapshot đã được xác minh. Biến môi trường được ưu tiên hơn file env; dotenv đọc theo đường dẫn project, không phụ thuộc thư mục terminal. Không gửi key trong chat hoặc commit. File examples không chứa key thật.

## Chạy bằng hai terminal

Bước 4 dựng server trước; xem [hướng dẫn server](mcp-server/README.md) để đối chiếu transport/logging của bản repo hiện tại với starter. Server 8085 đã có [readiness check hiện hành](../reports/evidence/step04_server_readiness.json); health không thay một lời gọi WeatherAPI thật.

Terminal 1, từ gốc repo:

```bash
uv run --project 04-lab/mcp-server python 04-lab/mcp-server/weather.py --transport streamable-http
```

Server mặc định `http://127.0.0.1:8085/mcp`. Không suy transport từ TTY; muốn stdio phải truyền `--transport stdio`. Streamable HTTP dùng stateless JSON. Đặt `PORT` ở server và `MCP_SERVER_URL` ở client nếu đổi cổng.

Terminal 2, từ gốc repo:

```bash
uv run --project 04-lab/mcp-client python 04-lab/mcp-client/verify_setup.py
# Sau khi preflight đạt:
uv run --directory 04-lab/mcp-client adk web
```

Mở `http://localhost:8000`, chọn `weather_agent`; hỏi “Thời tiết Hà Nội hiện tại?” hoặc “Dự báo Sydney 3 ngày”. Dừng auth demo phần 03 trước khi chạy web vì cùng cổng 8000. Không coi import/preflight là evidence đã chat qua trình duyệt.

Trong lần thực nghiệm này, Docker đang giữ cổng 8000. ADK chạy bằng `uv run --directory 04-lab/mcp-client adk web --port 8001`; mở `http://127.0.0.1:8001`. MCP vẫn ở `http://127.0.0.1:8085/mcp`; đổi cổng web không đổi `MCP_SERVER_URL`.

Bước 5 đã có [ảnh verify_setup](../screenshots/04-verify-setup.png), [current](../screenshots/04-adk-current.png) và [forecast](../screenshots/04-adk-forecast.png). Hai phiên browser có functionCall/response và final answer thật; [hướng dẫn client](mcp-client/README.md#bước-5--hai-phiên-chat-với-thời-tiết-thật) ghi sources và khác biệt so với starter. Ảnh verify là stdout trong trình duyệt, còn hai ảnh chat là ứng dụng ADK thật.

## Kiểm tra và evidence

Không cần key để kiểm tra giao thức MCP và ADK discovery:

```bash
uv run --project 04-lab/mcp-client python scripts/check_lab.py
```

Lệnh này tự chạy server tạm trên loopback, chạy tests + ba demos và ghi `reports/evidence/`. Response thời tiết trong contract tests là mock; MCP stdio/HTTP và ADK discovery dùng SDK/network thật trên máy.

Khi key LLM đã có, kiểm tra tool round trip với `health_check` (không cần WeatherAPI key):

```bash
uv run --project 04-lab/mcp-client python scripts/check_lab.py --live-agent
```

Khi đã có **cả hai key**, kiểm tra current/forecast qua WeatherAPI và hỏi agent thời tiết thật:

```bash
uv run --project 04-lab/mcp-client python scripts/check_lab.py --live-agent --live-weather
```

Các cờ live có thể phát sinh chi phí. Local/live JSON có tên riêng, timestamp, versions, source hashes và trạng thái từng check. `--skip-tests` chỉ dùng khi đã chạy tests trên cùng source; báo cáo sẽ ghi `not_run`, không tự nhận tests pass.

## Docker và triển khai

`mcp-server/Dockerfile` chạy HTTP explicit, bind `0.0.0.0`, dùng biến `PORT` (mặc định container 8080). `.dockerignore` loại env và virtualenv. Image local đã [build thành công](../reports/evidence/container_preparation.json); chưa kiểm tra runtime container. Phần Cloud Run tùy chọn được bỏ qua theo yêu cầu, không có deployment hoặc ảnh 05-cloud-run.

Server local mặc định loopback. Muốn public cần authentication, HTTPS và quản lý secrets ở nền tảng deploy; auth demo phần 03 chỉ dùng static token để minh họa. Không mở server weather chưa auth ra Internet.

Xem [báo cáo](../reports/REPORT.md) để biết các bước đã chạy và phần còn thiếu.
