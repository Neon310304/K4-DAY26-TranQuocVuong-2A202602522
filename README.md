# K4 Day26 — MCP và Function Calling

**Họ tên / MSSV:** Trần Quốc Vượng — 2A202602522

**Repo:** [K4-DAY26-TranQuocVuong-2A202602522](https://github.com/Neon310304/K4-DAY26-TranQuocVuong-2A202602522)

Lab gồm bốn phần: function calling thuần, MCP stdio, auth/registry/versioning và agent ADK dùng MCP HTTP. Xem [báo cáo hoàn thiện](reports/REPORT.md) và [evidence](reports/evidence/) để phân biệt kiểm tra local, dữ liệu mock và lời gọi API thật. Repo không có rubric/chương trình chấm điểm; test pass chỉ xác nhận phạm vi được kiểm tra.

## Phân biệt MCP và Function Calling

Đây là hai khái niệm hay bị nhầm lẫn nhưng thực ra ở **hai tầng khác nhau**, và **bổ sung cho nhau** chứ không thay thế.

## Cấu trúc repo

```
K4-DAY26-TranQuocVuong-2A202602522/
├── README.md                ← Bạn đang đọc file này
├── requirements.txt         ← pip install -r requirements.txt
│
├── 01-function-calling/     ← Bước 1: Function Calling thuần (Gemini SDK)
│   ├── README.md
│   └── weather_function_calling.py
│
├── 02-mcp-basics/           ← Bước 2: MCP server + client (không cần API key)
│   ├── README.md
│   ├── weather_server.py
│   └── weather_client.py
│
├── 03-production/           ← Bước 3: Auth, Tool Registry, Versioning
    ├── README.md
    ├── auth_server.py
    ├── auth_client.py
    ├── registry.json
    ├── registry_client.py
    ├── versioned_server.py
    └── versioned_client.py
│
└── 04-lab/                  ← Bước 4: Agent Google ADK + MCP server thật (WeatherAPI)
    ├── README.md
    ├── mcp-server/          ← MCPServer (Streamable HTTP, Dockerfile cho Cloud Run)
    └── mcp-client/          ← ADK agent dùng McpToolset
```

> Bước 01–03 dùng **MCP Python SDK v2** (`mcp>=2.0`, xem `requirements.txt`).
> Lab 04 yêu cầu Python ≥ 3.12, có hai môi trường và `uv.lock` riêng. Đã kiểm tra Python 3.12.6, MCP 2.3.0 và ADK 2.12.0. Các lệnh dưới đây chạy từ **gốc repo**; cần cài [uv](https://docs.astral.sh/uv/getting-started/installation/).

## Quick start

### Chuẩn bị bước 01–03

Python ≥ 3.12. Các lệnh chạy từ gốc repo; không cần kích hoạt virtualenv nếu dùng interpreter trực tiếp.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Linux/macOS:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
test -f .env || cp .env.example .env
```

Đã xác nhận **5/5 mục chuẩn bị**: fork public đúng tên, thư mục screenshots, cài requirements và pip check, hai credentials, uv. Xem [preparation.json](reports/evidence/preparation.json) và [ảnh repo](screenshots/00-repo-fork.png). Gemini dùng key YesScale qua API tương thích Gemini; WeatherAPI cần key riêng. Không cần tạo thêm Google key cho cấu hình YesScale này.

### Lab 04 và kiểm tra local

```bash
uv sync --locked --project 04-lab/mcp-client --python 3.12
uv sync --locked --project 04-lab/mcp-server --python 3.12
uv pip check --python 04-lab/mcp-client/.venv/Scripts/python.exe # Windows
# Linux/macOS: thay Scripts/python.exe bằng bin/python

# MCP stdio, registry, versioning: dữ liệu mock, không gọi LLM
uv run --project 04-lab/mcp-client python 02-mcp-basics/weather_client.py
uv run --project 04-lab/mcp-client python 03-production/registry_client.py
uv run --project 04-lab/mcp-client python 03-production/versioned_client.py

# Batch bước 3: auth hợp lệ/sai/thiếu token, registry và versioning;
# tự chọn cổng trống và dừng auth server sau khi chạy
uv run --project 04-lab/mcp-client python scripts/run_production.py --output-dir reports/evidence/production

# Kiểm tra local + lưu evidence (tự bật/tắt server tạm; không gọi API ngoài)
uv run --project 04-lab/mcp-client python scripts/check_lab.py
```

Nếu không dùng uv: `python -m venv .venv`, rồi cài `python -m pip install -r requirements-lab.txt` bằng interpreter của virtualenv. Windows có thể chạy trực tiếp `.venv\Scripts\python.exe`; Linux/macOS dùng `.venv/bin/python`.

Auth cần **hai terminal**, đều đứng tại gốc repo:

| Terminal | Lệnh |
|---|---|
| 1 | `uv run --project 04-lab/mcp-client python 03-production/auth_server.py` |
| 2 | `uv run --project 04-lab/mcp-client python 03-production/auth_client.py` |

Token mặc định chỉ là token demo. Để đổi token, đặt cùng `MCP_AUTH_TOKEN` ở cả hai terminal. Auth demo dùng cổng 8000; dừng nó trước khi bật ADK web cũng dùng cổng 8000. Nếu cổng đang bận, xem [lệnh cấu hình cổng 8002](03-production/README.md#3a-authentication); không dừng dịch vụ khác để chiếm cổng.

Batch bước 3 đã đạt **10/10 checks**: auth hợp lệ gọi được tool, sai/thiếu token bị **401**, registry chọn v2 active, v1/v2 và defaults hoạt động, auth server đã dừng. [Evidence](reports/evidence/production/production_results.json) ghi cổng 8002 và source hashes. Bốn ảnh đúng tên có tại [screenshots](screenshots/README.md); đây là ảnh stdout/access log thật trong trình duyệt, yêu cầu ảnh cửa sổ terminal gốc còn thiếu.

Phần 01 đọc `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY` trong [mẫu .env](.env.example) ở gốc repo. Với YesScale, đặt key của bạn ở `GEMINI_API_KEY`, `GEMINI_BASE_URL=https://api.yescale.io`, `GOOGLE_MODEL=gemini-2.5-flash`. Endpoint Gemini dùng host gốc; endpoint tương thích OpenAI dùng `/v1`.

```bash
uv run --project 04-lab/mcp-client python 01-function-calling/weather_function_calling.py --output reports/evidence/function_calling_gemini.json
```

Đã chạy **Google Gemini SDK → YesScale → Gemini 2.5 Flash** thật, app tự thực thi hai tool calls; weather của phần 01 là mock. Xem [JSON](reports/evidence/function_calling_gemini.json). Lab 04 hỗ trợ Gemini native qua YesScale, Google trực tiếp hoặc model tương thích OpenAI qua LiteLLM; xem [hướng dẫn cấu hình](04-lab/README.md).

Đã thêm ví dụ manual function calling tương đương cho YesScale, đọc cấu hình client của Lab 04:

```bash
uv run --project 04-lab/mcp-client python 01-function-calling/weather_openai_compatible.py --live --output reports/evidence/function_calling_yescale.json
```

App tự chạy `get_weather` và trả kết quả cho model; không có MCP ở ví dụ này. [function_calling_yescale.json](reports/evidence/function_calling_yescale.json) là thí nghiệm gpt-4o-mini trước khi bổ sung Gemini native; hash của file Gemini trong artifact lịch sử này không còn khớp source hiện tại.

## Checklist và giới hạn bằng chứng

- [x] MCP stdio, HTTP handshake, tool discovery và health check local.
- [x] Auth: thiếu/sai token bị 401, token hợp lệ gọi được tool.
- [x] Registry chọn v2 đang hoạt động; versioning giữ v1 và resource metadata.
- [x] Server weather có schema 1–3 ngày, lỗi MCP rõ ràng, log không chứa key.
- [x] ADK thực hiện discovery thật; import agent không được tính là kết nối thành công.
- [x] Hai lockfile được cập nhật; mẫu env và checker có lệnh chạy từ gốc repo.
- [x] 35/35 tests đạt; ADK web khởi động và công bố weather_agent qua HTTP.
- [x] Gemini SDK native qua YesScale: hai function calls Hà Nội/Đà Nẵng, app thực thi weather mock.
- [x] Gemini 2.5 Flash qua YesScale → ADK Runner → MCP → WeatherAPI; current/forecast thật.
- [x] ADK web 8001 → Gemini 2.5 Flash qua YesScale/LiteLLM → MCP server 8085 → WeatherAPI: [phiên chat thật](reports/evidence/adk_web_chat.json), [ảnh](screenshots/04-adk-weather-success.png).
- [x] Bước 5: đủ tên ảnh [verify_setup](screenshots/04-verify-setup.png), [current](screenshots/04-adk-current.png), [forecast](screenshots/04-adk-forecast.png); [forecast events/SSE](reports/evidence/adk_web_forecast.json) ghi get_forecast(Hanoi, 3) và final answer khớp ba ngày từ tool. Ảnh verify là stdout thật trong trình duyệt; hai ảnh chat là ADK web thật.
- [ ] Cloud Run: bỏ qua phần tùy chọn theo yêu cầu; không có deployment hoặc ảnh 05-cloud-run. Image Docker local đã build trước khi bỏ qua, chưa kiểm tra runtime container.

Kết quả chi tiết nằm trong [báo cáo](reports/REPORT.md). Checker mặc định không gọi LLM/WeatherAPI; tùy chọn `--live-agent`/`--live-weather` gọi dịch vụ và có thể phát sinh chi phí. Không commit `.env`.

Source hashes dùng byte thật của file. `.gitattributes` giữ nguyên xuống dòng khi commit/checkout để evidence từ Windows vẫn đối chiếu được trên máy khác. Bản nộp gồm source, reports/evidence và screenshots trên nhánh main; ảnh CLI trong trình duyệt vẫn được ghi rõ phạm vi tại [screenshots/README.md](screenshots/README.md).

Ảnh cho từng bước nằm trong [screenshots/README.md](screenshots/README.md). Gemini native qua YesScale đã đạt ở phần 01 và ADK Runner; browser native gặp 503 nên phiên browser thành công dùng adapter LiteLLM với cùng model. Đây là hai thực nghiệm riêng, không phải kết luận rằng provider đã hết lỗi.

---

## Định nghĩa ngắn gọn

**Function Calling** là một *khả năng của model* (capability). Model được huấn luyện để khi bạn đưa cho nó danh sách các "công cụ" (kèm schema mô tả tham số), nó có thể tự quyết định gọi công cụ nào và sinh ra JSON tham số phù hợp. Bản thân model **không chạy** function — nó chỉ nói "hãy gọi `get_weather(city='Hanoi')`". App mới là nơi chạy tool.

**MCP (Model Context Protocol)** là một *giao thức chuẩn* (protocol) — giống như USB-C hay HTTP cho thế giới AI. Nó định nghĩa cách một **MCP Client** (như Claude Code, Claude Desktop) kết nối tới các **MCP Server** để khám phá và sử dụng tools, resources, prompts một cách thống nhất.

---

## So sánh trực tiếp

| Tiêu chí | Function Calling | Model Context Protocol (MCP) |
|---|---|---|
| **Bản chất** | Tính năng của mô hình (Model capability) | Giao thức giao tiếp client–server |
| **Ai định nghĩa tool?** | Bạn hard-code trong từng app | Server tự công bố (self-describe) tool |
| **Tái sử dụng** | Phải viết lại cho mỗi app/model | Viết 1 lần, mọi MCP client dùng được |
| **Thực thi** | App của bạn tự chạy | MCP Server chạy, client điều phối |
| **Tính chuẩn hóa** | Mỗi nhà cung cấp 1 kiểu (OpenAI, Anthropic khác nhau) | Một chuẩn chung do Anthropic đề xuất |
| **Hệ sinh thái** | Khó chia sẻ dạng module đóng gói sẵn | Dễ dàng chia sẻ và tải về các "MCP Servers" mã nguồn mở |

## Quan hệ giữa chúng

**MCP hoạt động độc lập với Function Calling của model**: client có thể gọi tool mà không có LLM, như phần 02. Trong agent, app thường dùng Function Calling để model chọn tool, rồi chuyển yêu cầu sang MCP. Hai cơ chế bổ sung cho nhau.

```
User hỏi
   │
   ▼
LLM (dùng Function Calling để quyết định gọi tool nào)
   │
   ▼
MCP Client  ──[giao thức MCP]──►  MCP Server (thực thi tool thật)
   │                                   │
   ◄───────────── kết quả ─────────────┘
   ▼
LLM tổng hợp câu trả lời
```

## Khi nào dùng cái nào?

- **Function Calling thuần**: app đơn giản, tool gắn chặt với 1 ứng dụng, không cần chia sẻ.
- **MCP**: muốn tool/tích hợp dùng lại được trên nhiều AI client, muốn tách biệt logic tool khỏi app, hoặc xây hệ sinh thái tích hợp (DB, file, API nội bộ...).

---

## Minh hoạ bằng mã nguồn

Cùng một tool `get_weather`, dưới đây là hai cách triển khai để thấy rõ sự khác biệt.

### [Cách 1 — Function Calling thuần (Google Gemini SDK)](01-function-calling/)

Tool được **định nghĩa và thực thi ngay trong app**. Model chỉ quyết định gọi tool nào, app tự chạy và đưa kết quả trở lại.

```
User hỏi → Model quyết định gọi get_weather("Hà Nội")
                    │
                    ▼
             App TỰ THỰC THI hàm get_weather
                    │
                    ▼
             Model tổng hợp câu trả lời
```

> Nhược điểm: schema viết tay, tool gắn chặt trong app — muốn dùng lại ở app khác phải copy cả schema lẫn hàm.

Chi tiết + code: xem [`01-function-calling/README.md`](01-function-calling/README.md)

### [Cách 2 — MCP (server tự công bố tool, mọi client dùng chung)](02-mcp-basics/)

Tool được tách ra **một MCP server độc lập**. Server tự "khai báo" nó có tool gì; bất kỳ MCP client nào (Claude Code, Claude Desktop, Cursor...) cũng cắm vào dùng được mà không cần biết code bên trong.

```
weather_client.py                       weather_server.py
┌─────────────┐    giao thức MCP    ┌─────────────────┐
│  list_tools │ ──────────────────▶ │ @mcp.tool()     │
│  call_tool  │ ◀────────────────── │ get_weather()   │
└─────────────┘     stdio           └─────────────────┘
```

Chi tiết + code: xem [`02-mcp-basics/README.md`](02-mcp-basics/README.md)

### Điểm khác biệt rút ra từ code

| | Function Calling thuần | MCP |
|---|---|---|
| Khai báo schema | Tự viết tay trong app | `@mcp.tool()` tự sinh từ type hints |
| Nơi thực thi tool | Trong app gọi model | Trong MCP server riêng |
| Khám phá tool | Hard-code danh sách `tools` | `session.list_tools()` tại runtime |
| Dùng lại ở app khác | Copy code | Cắm thêm client, không sửa server |
| Vai trò Function Calling | Model chọn hàm, app thực thi | Có thể dùng ở phía agent; không phải yêu cầu của giao thức MCP |

---

## [MCP trong Production](03-production/)

Các ví dụ trên chạy tốt trên máy cá nhân, nhưng đưa vào **hệ thống production** cần giải quyết thêm ba vấn đề:

```
┌─────────────────────────────────────────────────────┐
│                  Production MCP                     │
│                                                     │
│  ┌──────────┐   ┌───────────┐   ┌───────────────┐   │
│  │ Security │   │ Registry  │   │  Versioning   │   │
│  │          │   │           │   │               │   │
│  │ • Auth   │   │ • Discover│   │ • v1 compat   │   │
│  │ • Token  │   │ • Connect │   │ • v2 features │   │
│  │ • Scopes │   │ • Health  │   │ • Deprecation │   │
│  └──────────┘   └───────────┘   └───────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 1. Security — Authentication & Authorization

MCP server phục vụ qua **HTTP** cho nhiều client → cần xác thực. MCP SDK hỗ trợ sẵn **Bearer Token** verification:

- Server: cấu hình `AuthSettings` + implement `TokenVerifier` protocol
- Client: gửi header `Authorization: Bearer <token>` qua `create_mcp_http_client(headers=...)` của MCP SDK
- Không có token hoặc token sai → 401. Đã xác thực nhưng thiếu quyền/scope → 403 (demo chưa kiểm tra scope). Logic tool không biết gì về auth.

| Tầng | Demo (stdio) | Production (HTTP) |
|---|---|---|
| Transport | stdio (cùng máy) | Streamable HTTP (qua mạng) |
| Auth | Không cần | Bearer token / OAuth / mTLS |
| Phạm vi truy cập | Toàn bộ | Scopes giới hạn từng client |

### 2. Tool Registry & Discovery

Agent **không hard-code** tool nào. Nó hỏi **Tool Registry** — danh mục trung tâm liệt kê tất cả tool từ mọi server — theo yêu cầu task:

```
Agent nhận task "lấy thời tiết Hà Nội"
   │
   ▼
Tool Registry: "tool nào có tag 'weather'?"
   │
   ├── get_weather v1.0 → server: weather (stdio)
   └── get_weather_v2 v2.0 → server: weather-v2 (stdio)
   │
   ▼
Agent chọn best match (v2.0, không deprecated)
   │
   ▼
Kết nối tới server weather-v2, gọi get_weather_v2(city="Hanoi")
```

Registry là **tool-centric** — đơn vị khám phá là **tool** (tag, description, parameters), không phải server.

| | Hard-code (demo) | Tool Registry (production) |
|---|---|---|
| Agent biết tool nào? | Chỉ tool được code sẵn | Tất cả tool trong registry |
| Tìm tool | Theo tên cố định | Theo tag, keyword, capability |
| Thêm tool mới | Sửa code agent | Thêm entry vào registry |
| Chọn tool | Developer quyết định | Agent tự chọn best match |

### 3. Versioning & Backward Compatibility

Server v1 có `get_weather(city)` trả chuỗi đơn giản. V2 muốn trả JSON chi tiết, thêm `include_forecast`. Nếu đổi trực tiếp → mọi client cũ break. Giải pháp — 3 kỹ thuật kết hợp:

| Kỹ thuật | Mô tả |
|---|---|
| **Tool mới song song** | `get_weather_v2` tồn tại bên cạnh `get_weather` — không xoá tool cũ |
| **Tham số optional** | `include_forecast`, `units` có default → client cũ gọi vẫn đúng |
| **Server metadata** | Resource `server://info` công bố version + deprecation notice |

Chi tiết + code cho cả 3 phần: xem [`03-production/README.md`](03-production/README.md)

### Tổng kết Production Checklist

| Khía cạnh | Dev/Demo | Production |
|---|---|---|
| **Transport** | stdio (cùng máy) | Streamable HTTP (SSE transport cũ) |
| **Auth** | Không | Bearer token, OAuth, mTLS |
| **Discovery** | Hard-code tool/server | Tool Registry — agent tìm tool theo task |
| **Versioning** | 1 tool duy nhất | Tool v1 + v2 song song, deprecation notice |
| **Health** | Không | Health check, retry, circuit breaker |
| **Logging** | `print()` | Structured logging, tracing (OpenTelemetry) |

---

Function Calling cho model đề xuất tên hàm và tham số; MCP chuẩn hóa khám phá và gọi tools giữa client/server. App/agent nối hai tầng khi cần model điều phối.
