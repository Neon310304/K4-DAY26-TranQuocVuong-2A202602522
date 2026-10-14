# 01 — Function Calling thuần (Google Gemini SDK)

Tool `get_weather` được **định nghĩa schema thủ công** và **thực thi ngay trong app**.
Model chỉ quyết định gọi tool nào — app mới là nơi chạy.

```
User hỏi  →  Model quyết định gọi get_weather(city="Hà Nội")
                     │
                     ▼
              App TỰ THỰC THI hàm get_weather
                     │
                     ▼
              Model tổng hợp câu trả lời
```

## Cách chạy

Các lệnh cũ bên dưới chạy trong thư mục phần 01. Từ **gốc repo**, dùng:

```bash
uv run --project 04-lab/mcp-client python 01-function-calling/weather_function_calling.py --output reports/evidence/function_calling_gemini.json
```

Gemini SDK đọc `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY` trong `.env` ở gốc repo; dùng [.env.example](../.env.example). Model là API thật, dữ liệu của hàm weather là mock.

**YesScale chạy được ngay bằng Google SDK:** đặt `GEMINI_API_KEY` bằng key YesScale, `GEMINI_BASE_URL=https://api.yescale.io`, `GOOGLE_MODEL=gemini-2.5-flash`. Để gọi Google trực tiếp, dùng Google key và để `GEMINI_BASE_URL` trống. Đã chạy native SDK thành công qua YesScale: [JSON](../reports/evidence/function_calling_gemini.json), [stdout](../reports/evidence/function_calling_gemini.txt), [ảnh](../screenshots/01-function-calling-gemini.png).

Code tắt automatic function calling của SDK để nhìn rõ app tự chạy `get_weather`, gửi function response, rồi model tổng hợp. Vòng lặp tối đa bốn lượt và từ chối tên hàm ngoài whitelist.

### Đối chiếu ba phần của codelab

| Phần | Vị trí trong source hiện tại | Vai trò |
|---|---|---|
| Schema viết tay | `get_weather_declaration = types.FunctionDeclaration(...)` | Tool get_weather, city kiểu string và bắt buộc |
| Hàm thực thi | `def get_weather(city: str) -> str` | JSON mock của Hà Nội, Hồ Chí Minh, Đà Nẵng |
| Vòng lặp | `run()`: `for _ in range(4)` và `if not resp.function_calls` | App đọc yêu cầu, chạy hàm, gửi function responses rồi nhận câu trả lời cuối |

Starter minh họa bằng `while resp.function_calls`; bản hiện tại giữ cùng luồng nhưng giới hạn bốn lượt để tránh lặp vô hạn. `result = get_weather(**fc.args)` là dòng **app thực thi**, còn `genai.Client(...).models.generate_content(...)` chỉ trả yêu cầu/kết quả của model.

### Chạy trên Windows bằng virtualenv gốc

Env ở gốc repo đã được cấu hình Gemini qua YesScale; không cần in hoặc nhập key trong terminal. Từ gốc repo:

```powershell
.\.venv\Scripts\python.exe 01-function-calling/weather_function_calling.py --output reports/evidence/function_calling_gemini.json
```

Hoặc từ thư mục của bước 01:

```powershell
Set-Location 01-function-calling
..\.venv\Scripts\python.exe weather_function_calling.py --output ../reports/evidence/function_calling_gemini.json
```

Lệnh này gọi Gemini thật và có thể phát sinh chi phí. Chụp cửa sổ terminal sao cho thấy `[model yêu cầu]`, `[app thực thi]` và `Trả lời:`, lưu `screenshots/01-function-calling.png`.

### Checkpoint đã đối chiếu

- [x] Google SDK gọi Gemini 2.5 Flash thật qua YesScale, đúng câu hỏi cố định.
- [x] Hai cặp model yêu cầu/app thực thi cho Hà Nội và Đà Nẵng, JSON mock 29°C/30°C.
- [x] Có câu trả lời cuối dựa trên kết quả tool; [JSON](../reports/evidence/function_calling_gemini.json) và [stdout](../reports/evidence/function_calling_gemini.txt) được giữ.
- [x] Có [01-function-calling.png](../screenshots/01-function-calling.png) đúng tên yêu cầu, hiển thị stdout thật trong trình duyệt.
- [ ] Ảnh cửa sổ terminal gốc: chưa chụp trong phiên này. Ảnh hiện có là bản chụp stdout đang xem trong trình duyệt; đổi tên không biến nó thành ảnh terminal.

Ví dụ bổ sung cho API **tương thích OpenAI** giữ cùng cơ chế manual function calling. Nó đọc key ở `04-lab/mcp-client/.env`:

```bash
uv run --project 04-lab/mcp-client python 01-function-calling/weather_openai_compatible.py --live --output reports/evidence/function_calling_yescale.json
```

Đây là adapter khác với Google SDK. Evidence gpt-4o-mini cũ được giữ để đối chiếu lịch sử; không dùng nó thay evidence native Gemini ở trên. Mọi lệnh generation đều dùng API và có thể phát sinh chi phí; dữ liệu thời tiết phần này vẫn là mock.

```bash
pip install -r ../requirements.txt
export GEMINI_API_KEY=...
python weather_function_calling.py
```

## File

| File | Mô tả |
|---|---|
| `weather_function_calling.py` | Định nghĩa schema, thực thi tool, gọi model Gemini, xử lý vòng lặp function calling |

---

## Function Calling là gì? Giải thích đơn giản

Hình dung bạn có một **trợ lý ảo** rất giỏi ngôn ngữ, nhưng **không biết gì về thế giới thật** — không biết thời tiết, không truy cập được database, không gọi được API.

Function Calling là cách bạn **dạy trợ lý ảo sử dụng công cụ**:

```
Không có Function Calling:                 Có Function Calling:

User: "Thời tiết HN?"                     User: "Thời tiết HN?"
       │                                         │
       ▼                                         ▼
   ┌────────┐                                ┌────────┐
   │ Model  │                                │ Model  │
   │        │                                │        │ ← biết có tool get_weather
   │ "Tôi   │                                │ "Hãy   │
   │ không  │                                │  gọi   │
   │ biết"  │                                │ get_   │
   │        │                                │ weather│
   └────────┘                                │("HN")  │
                                             └───┬────┘
   Model bó tay vì                               │
   không có dữ liệu                              ▼
                                             App chạy hàm
                                                  │
                                                  ▼
                                             ┌────────┐
                                             │ Model  │
                                             │ "HN:   │
                                             │ 29°C,  │
                                             │ mưa"   │
                                             └────────┘
```

**Điểm mấu chốt:** Model **KHÔNG chạy** hàm. Nó chỉ nói *"hãy gọi hàm X với tham số Y"*.

---

## Minh hoạ từng bước chi tiết

User hỏi: **"Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"**

```
Bước 1 — App chuẩn bị "hộp công cụ" cho model
═══════════════════════════════════════════════

    App định nghĩa schema THỦ CÔNG:
    ┌────────────────────────────────────────┐
    │  Tool: get_weather                     │
    │  Mô tả: "Lấy thời tiết thành phố"      │
    │  Tham số:                              │
    │    city: string (bắt buộc)             │
    │                                        │
    │   Schema viết TAY - 15 dòng code       │
    │     phải khớp với hàm thật             │
    └────────────────────────────────────────┘

Bước 2 — Gửi prompt + schema cho model
═══════════════════════════════════════

    App ──────────────────────────────────────────▶ Gemini
    │  "Thời tiết HN và ĐN?"                      │
    │  + schema get_weather                       │
    │                                             │
    │  Model hiểu: "À, có tool get_weather,       │
    │   tôi cần gọi nó 2 lần cho HN và ĐN"        │

Bước 3 — Model TRẢ VỀ yêu cầu gọi tool (không tự chạy!)
═════════════════════════════════════════════════════════

    Gemini ──────────────────────────────────────▶ App
    │  function_calls:                             │
    │    [                                         │
    │      get_weather(city="Hà Nội"),             │
    │      get_weather(city="Đà Nẵng")             │
    │    ]                                         │
    │                                              │
    │    Model CHỈ sinh JSON — không hề chạy       │

Bước 4 — App TỰ THI HÀNH hàm get_weather
═════════════════════════════════════════

    App nhận yêu cầu → CHẠY hàm Python:
    ┌──────────────────────────────────────────┐
    │  get_weather("Hà Nội")   → "29°C, mưa"   │ ← App chạy
    │  get_weather("Đà Nẵng")  → "30°C, mây"   │ ← App chạy
    └──────────────────────────────────────────┘

Bước 5 — Gửi kết quả lại cho model tổng hợp
════════════════════════════════════════════

    App ──────────────────────────────────────────▶ Gemini
    │  Kết quả: HN 29°C mưa, ĐN 30°C mây         │
    │                                            │
    │  Gemini: "Hà Nội 29°C, mưa nhẹ 🌧️          │
    │           nhớ mang ô nhé!                  │
    │           Đà Nẵng 30°C, nhiều mây 🌤️       │
    │           thời tiết dễ chịu!"              │
```

---

## Nhìn vào code thật

3 phần quan trọng trong `weather_function_calling.py`:

**Phần 1 — Schema viết tay** (model cần biết tool trông như thế nào):

```python
# App phải TỰ MÔ TẢ tool cho model — viết tay, dễ sai
get_weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Lấy thời tiết hiện tại của một thành phố",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(type=types.Type.STRING, description="Tên thành phố")
        },
        required=["city"],
    ),
)
```

**Phần 2 — Hàm thực thi** (app tự chạy khi model yêu cầu):

```python
# App phải CÓ hàm thật để chạy — model không chạy hàm này
def get_weather(city: str) -> str:
    return json.dumps({"city": city, "nhiệt_độ": "29°C", ...})
```

**Phần 3 — Vòng lặp** (nhận yêu cầu → chạy → trả lại):

```python
for _ in range(4):
    resp = client.models.generate_content(model=MODEL, contents=contents, config=config)
    if not resp.function_calls:
        return resp.text
    contents.append(resp.candidates[0].content)
    function_responses = []
    for fc in resp.function_calls:
        result = get_weather(**fc.args)   # ← APP chạy, không phải model
        function_responses.append(types.Part.from_function_response(
            name=fc.name, response={"result": result}
        ))
    contents.append(types.Content(role="user", parts=function_responses))
```

---

## Luồng hoạt động

1. App định nghĩa `FunctionDeclaration` với schema viết tay (tên, tham số, kiểu)
2. App gửi prompt + danh sách tool tới Gemini
3. Model trả về `function_calls` — yêu cầu gọi `get_weather`
4. App **tự chạy** hàm `get_weather()` và đưa kết quả trả lại model
5. Model tổng hợp câu trả lời cuối cho user

## Nhược điểm

```
┌─────────────────────────────────────────────────────────────┐
│  ❌ Schema viết tay                                         │
│     FunctionDeclaration(name=..., parameters=...)           │
│     → 15+ dòng boilerplate, dễ lệch với hàm thật            │
│                                                             │
│  ❌ Tool gắn chặt trong app                                 │
│     App A có get_weather → App B muốn dùng?                 │
│     → Copy schema + hàm sang App B                          │
│     → Sửa hàm ở A? Phải nhớ sửa cả B                        │
│                                                             │
│  ❌ Mỗi provider 1 format                                   │
│     Google: FunctionDeclaration(...)                        │
│     OpenAI: {"type": "function", "function": {...}}         │
│     Anthropic: {"name": ..., "input_schema": {...}}         │
│     → Đổi model = viết lại schema                           │
└─────────────────────────────────────────────────────────────┘
```

**MCP tách tool khỏi app và chuẩn hóa khám phá/gọi tool giữa client–server.** Server sinh schema từ type hints; adapter phía agent vẫn chuyển schema/kết quả sang định dạng mà model provider dùng. Xem [02-mcp-basics/](../02-mcp-basics/).

Bước tiếp theo: [02-mcp-basics/](../02-mcp-basics/) — tách tool ra MCP server độc lập.
