# 03 — Production (Auth, Tool Registry, Versioning)

`02-mcp-basics` chạy tốt trên máy cá nhân. Đưa vào production cần giải quyết thêm 3 vấn đề:

| Vấn đề | Demo | Production |
|---|---|---|
| **Auth** | stdio, cùng máy, ai cũng gọi | HTTP + Bearer token / OAuth |
| **Discovery** | Hard-code tool/server | Tool Registry — agent tìm tool theo task |
| **Versioning** | 1 tool duy nhất | v1 + v2 song song, deprecation notice |

## Files

| File | Vấn đề | Mô tả |
|---|---|---|
| `auth_server.py` | Auth | MCP server qua HTTP + `TokenVerifier` kiểm tra bearer token |
| `auth_client.py` | Auth | Client gửi token qua `create_mcp_http_client(headers=...)` |
| `registry.json` | Discovery | Tool Registry — danh mục tool-centric, agent tìm theo tag/keyword |
| `registry_client.py` | Discovery | Agent tra cứu registry, chọn best match, tự kết nối |
| `versioned_server.py` | Versioning | Server v2: giữ tool v1 (deprecated) + thêm v2 + resource metadata |
| `versioned_client.py` | Versioning | Client test gọi tool v1, v2 và đọc `server://info` metadata |

## Chạy toàn bộ bước 3 từ gốc repo

Không gọi LLM hoặc WeatherAPI; các weather results trong ba demo đều là mock. Dùng interpreter của virtualenv đã chuẩn bị:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/run_production.py --auth-port 8002 --output-dir reports/evidence/production
```

Linux/macOS dùng `.venv/bin/python`. Nếu không chỉ định `--auth-port`, runner chọn một cổng loopback đang trống. Lệnh dùng server/client thật, chạy auth hợp lệ/sai/thiếu token, registry, v1/v2/defaults; ghi stdout/JSON và **dừng auth server trong finally**. Trên Windows dừng cả cây tiến trình do launcher virtualenv có thể tạo Python child, sau đó kiểm tra cổng đã đóng.

Lần thực nghiệm dùng **8002** vì Docker đang giữ 8000. Không dừng Docker hoặc ADK để chiếm cổng. Cổng mặc định của auth demo vẫn là 8000 khi không cấu hình; URL thực tế nằm trong [production_results.json](../reports/evidence/production/production_results.json).

---

## 3a. Authentication

Server chạy qua **Streamable HTTP** thay vì stdio, kèm bearer token verification.

Các lệnh `python` dưới đây giả sử đã kích hoạt `.venv` và đang đứng trong `03-production/`.

```bash
# Terminal 1 — khởi động server
python auth_server.py
# Server lắng nghe tại http://localhost:8000/mcp

# Terminal 2 — client kết nối kèm token
python auth_client.py
```

Luồng:

```
Client                                Server
  │                                      │
  │── POST /mcp ──────────────────────▶  │
  │   Authorization: Bearer <token>      │
  │                                      │── TokenVerifier.verify_token()
  │                                      │   token hợp lệ → AccessToken
  │◀── 200 OK (tools, results) ────────  │
  │                                      │
  │── POST /mcp (token sai) ──────────▶  │
  │◀── 401 Unauthorized ───────────────  │
```

- Token hợp lệ → truy cập tool bình thường
- Thiếu token → `401`
- Token sai → `401`; `403` dành cho trường hợp đã xác thực nhưng thiếu quyền/scope (demo này chưa có bài thử scope)
- Logic tool không biết gì về auth — SDK xử lý ở tầng transport

**Đối chiếu codelab:** SDK 2.3.0 thực tế trả **401 cho token sai**, thay vì 403 như đoạn hướng dẫn đã ghi. Client response hook ghi status từ HTTP thật; không suy mã lỗi từ chữ trong exception. Thiếu token cũng là 401. Demo không kiểm tra scope denial nên không có evidence 403.

Nếu cần chạy hai terminal trên cổng khác, từ gốc repo:

```powershell
# Terminal 1
$env:MCP_AUTH_PORT = "8002"
.\.venv\Scripts\python.exe -X utf8 03-production/auth_server.py
```

```powershell
# Terminal 2: token mặc định, không in token hoặc header
$env:MCP_AUTH_SERVER_URL = "http://127.0.0.1:8002/mcp"
.\.venv\Scripts\python.exe -X utf8 03-production/auth_client.py --output reports/evidence/auth_ok.json

# Token sai: client phải exit 1 và không in Tools/Kết quả
$step3PreviousToken = $env:MCP_AUTH_TOKEN
$env:MCP_AUTH_TOKEN = "wrong-token"
.\.venv\Scripts\python.exe -X utf8 03-production/auth_client.py --output reports/evidence/auth_fail.json
if ($null -eq $step3PreviousToken) { Remove-Item Env:MCP_AUTH_TOKEN } else { $env:MCP_AUTH_TOKEN = $step3PreviousToken }
```

Dừng terminal 1 bằng Ctrl+C sau demo. `MCP_AUTH_PORT` đồng thời cập nhật issuer/resource URL của server; `MCP_AUTH_SERVER_URL` chọn endpoint phía client. Server mặc định bind loopback, có thể đổi bằng `MCP_AUTH_HOST`. Static tokens là dữ liệu demo của starter, không phải hệ thống auth production đã triển khai.

Evidence hiện hành: [auth_ok.json](../reports/evidence/production/auth_ok.json), [auth_fail.json](../reports/evidence/production/auth_fail.json), [stdout hợp lệ](../reports/evidence/production/auth-ok.txt), [stdout bị từ chối + access log](../reports/evidence/production/auth-fail.txt). Không lưu token, Authorization header hoặc raw SDK exception vào artifact.

---

## 3b. Tool Registry & Discovery

Agent **không hard-code** tool nào. Nó hỏi Tool Registry theo yêu cầu task:

```bash
python registry_client.py
```

Kết quả mong đợi:

```
=== Tool Registry ===

  get_weather v1.0.0
    Lấy thời tiết hiện tại của một thành phố
    tags: ['weather', 'current', 'vietnam']  →  server: weather
  get_weather_v2 v2.0.0
    Lấy thời tiết chi tiết — JSON, hỗ trợ forecast và đơn vị đo
    tags: ['weather', 'forecast', 'detailed', 'vietnam']  →  server: weather-v2
  ...

--- Agent cần tool có tag "weather" ---
Tìm thấy 2 tool(s):
  • get_weather v1.0.0 (server: weather)
  • get_weather_v2 v2.0.0 (server: weather-v2)

Best match: get_weather_v2 v2.0.0
Kết nối tới server [weather-v2]...
Kết quả: ...
```

Luồng:

```
Agent nhận task
   │
   ▼
ToolRegistry.search(tag="weather")  ← tìm tool theo capability
   │
   ├── get_weather v1.0 → server: weather
   └── get_weather_v2 v2.0 → server: weather-v2
   │
   ▼
ToolRegistry.best_match()  ← chọn version cao nhất, không deprecated
   │
   ▼
connect_and_call()  ← tự kết nối đúng transport (stdio/HTTP) + auth
```

`registry.json` là **tool-centric** — đơn vị khám phá là tool (tag, description, parameters), không phải server. Production thay JSON bằng DB/API với semantic search.

Trong demo, tag weather, keyword forecast và city Hanoi là dữ liệu cố định; **logic Python** tìm/chọn/gọi tool, không có LLM tham gia. `best_match` dùng `packaging.version.Version`, ưu tiên các tool active. Nếu không còn tool active, code starter cho phép chọn từ nhóm deprecated; demo hiện tại chọn v2 active, không chứng minh một policy từ chối mọi tool deprecated.

Registry có entries email/database minh họa; chúng không được gọi trong thực nghiệm này. Chỉ weather-v2 qua stdio đã được gọi bởi demo registry, không coi danh mục URL là bằng chứng đã kết nối mọi server/transport.

Từ gốc repo:

```powershell
.\.venv\Scripts\python.exe -X utf8 03-production/registry_client.py --output reports/evidence/registry_client.json
```

Evidence: [registry_client.json](../reports/evidence/production/registry_client.json) và [stdout](../reports/evidence/production/registry_client.txt): hai matches weather, best match get_weather_v2 2.0.0 và kết quả api_version 2.0.

---

## 3c. Versioning & Backward Compatibility

Server v2 dùng 3 kỹ thuật để thêm tính năng mà không break client cũ:

```bash
# Server chạy qua stdio — client tự spawn
python versioned_client.py
```

| Kỹ thuật | Mô tả |
|---|---|
| **Tool mới song song** | `get_weather_v2` tồn tại bên cạnh `get_weather` — không xoá tool cũ |
| **Tham số optional** | `include_forecast`, `units` có default → client cũ gọi `get_weather_v2(city="Hanoi")` vẫn đúng |
| **Server metadata** | Resource `server://info` công bố version, deprecated tools, migration guide |

```
Server v2
├── get_weather(city)              ← v1, deprecated nhưng vẫn hoạt động
├── get_weather_v2(city, ...)      ← v2, thêm forecast + units
└── resource server://info         ← version + migration guide cho client
```

Kết quả mong đợi:

```
Server: weather-v2 v2.0.0
Deprecated tools: ['get_weather']
Migration: Chuyển từ get_weather sang get_weather_v2. Tham số 'city' giữ nguyên, thêm include_forecast và units.

Tools:
  - get_weather: [v1] Lấy thời tiết hiện tại — trả chuỗi đơn giản. Deprecated, dùng get_weather_v2.
  - get_weather_v2: [v2] Lấy thời tiết chi tiết — JSON, hỗ trợ forecast và đơn vị đo.

[v1] get_weather('Hanoi'):
  Hanoi: 29°C, trời mưa

[v2] get_weather_v2('Hanoi', forecast=True):
  { "api_version": "2.0", "city": "Hanoi", "temp": 29, ... }
```

Luồng:

```
versioned_client.py                     versioned_server.py
       │                                        │
       │── read_resource("server://info") ────▶ │  ← đọc metadata trước
       │◀── version, deprecated_tools ────────  │
       │                                        │
       │── list_tools() ─────────────────────▶  │  ← khám phá tool
       │◀── [get_weather, get_weather_v2] ────  │
       │                                        │
       │── call_tool("get_weather") ──────────▶ │  ← v1 deprecated, vẫn chạy
       │── call_tool("get_weather_v2") ───────▶ │  ← v2 đầy đủ tính năng
```

Client thông minh đọc `server://info` để biết tool nào deprecated, tự chọn dùng v2 nếu có, fallback v1 nếu không.

Client của lab đọc metadata rồi **chủ động gọi cả v1 và v2 để đối chiếu**; chưa triển khai policy tự fallback theo metadata. Nó kiểm tra thêm `get_weather_v2(city="Hanoi")` để xác minh defaults celsius/không forecast, ghi vào JSON mà không cần đổi output mẫu.

Từ gốc repo:

```powershell
.\.venv\Scripts\python.exe -X utf8 03-production/versioned_client.py --output reports/evidence/versioned_client.json
```

Evidence: [versioned_client.json](../reports/evidence/production/versioned_client.json) và [stdout](../reports/evidence/production/versioned_client.txt). Timestamp của v2 là thời điểm gọi tool mock, không phải thời điểm đo thời tiết thật.

## Checkpoint bước 3

- [x] Auth HTTP: token hợp lệ initialize/list_tools/call_tool; token sai và thiếu bị 401.
- [x] Registry tìm hai weather tools và chọn v2 active qua version comparison.
- [x] V1 chuỗi, v2 JSON/forecast, optional defaults và resource server://info hoạt động.
- [x] Auth server đã dừng và cổng 8002 đã đóng sau batch; [evidence](../reports/evidence/production/production_results.json).
- [x] Có bốn ảnh đúng tên: [03a-auth-ok](../screenshots/03a-auth-ok.png), [03a-auth-fail](../screenshots/03a-auth-fail.png), [03b-registry](../screenshots/03b-registry.png), [03c-versioning](../screenshots/03c-versioning.png).
- [ ] Ảnh cửa sổ terminal gốc: công cụ hiện tại chụp stdout/access log thật đang xem trong trình duyệt. Các ảnh trên có đủ nội dung nhưng chưa phải ảnh terminal gốc; xem [chú thích](../screenshots/README.md).
