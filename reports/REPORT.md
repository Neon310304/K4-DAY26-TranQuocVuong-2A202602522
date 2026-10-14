# Báo cáo Lab Day26 — MCP và Function Calling

**Họ tên / MSSV:** Trần Quốc Vượng — 2A202602522

**Repo:** https://github.com/Neon310304/K4-DAY26-TranQuocVuong-2A202602522

**Ngày thực nghiệm:** 14/10/2026, Asia/Bangkok. Timestamp JSON dùng UTC.

## 1. Kết quả và phạm vi

Đã chạy bốn bước: Gemini Function Calling, MCP stdio, auth/registry/versioning và ADK dùng MCP Streamable HTTP với WeatherAPI thật. Checklist chuẩn bị đạt **5/5**, bộ tests đạt **35 passed, 6 warnings**, không có failures/errors. Đã lưu ảnh từng bước và phiên ADK web thật. Các trạng thái và dữ liệu thực nghiệm được chương trình ghi lại; không điền số đo để thay kết quả chạy.

| Phần | Kết quả | Evidence / giới hạn |
|---|---|---|
| Chuẩn bị | Fork public đúng tên K4, screenshots, Python/requirements, credentials, uv | [preparation.json](evidence/preparation.json); credential presence tách khỏi API execution |
| 01 — Gemini Function Calling | Google SDK qua YesScale gọi Gemini 2.5 Flash; app thực thi get_weather cho Hà Nội/Đà Nẵng rồi gửi kết quả cho model | [function_calling_gemini.json](evidence/function_calling_gemini.json), [stdout](evidence/function_calling_gemini.txt); LLM thật, weather mock |
| 02 — MCP basics | Khám phá tên/schema/docstring và gọi ba tool requests qua stdio thật | [mcp_stdio.json](evidence/mcp_stdio.json), [weather_client.txt](evidence/weather_client.txt); weather mock |
| 03 — Auth | Token hợp lệ initialize/list/call; sai/thiếu bị 401; server đã dừng | [auth_ok.json](evidence/production/auth_ok.json), [auth_fail.json](evidence/production/auth_fail.json), [batch](evidence/production/production_results.json); static demo, chưa kiểm tra scope 403 |
| 03 — Registry | Hai matches weather; chọn get_weather_v2 active version 2.0.0 và gọi qua stdio | [registry_client.json](evidence/production/registry_client.json), [stdout](evidence/production/registry_client.txt); logic Python, không gọi LLM |
| 03 — Versioning | V1 chuỗi, v2 JSON/forecast, defaults và server://info | [versioned_client.json](evidence/production/versioned_client.json), [stdout](evidence/production/versioned_client.txt); weather mock |
| 04 — MCP HTTP/ADK discovery | Initialize/list_tools/health và ADK get_tools thật, đủ ba tools | [server8085.json](evidence/server8085.json), [local_setup.json](evidence/local_setup.json) |
| Bước 4 — Server sẵn sàng hiện tại | Sync locked/pip check đạt; MCP HTTP 8085 initialize/list_tools/health và ADK discovery đạt, key configured | [step04_server_readiness.json](evidence/step04_server_readiness.json), [stdout](evidence/step04_server_readiness.txt); không gọi lại LLM/WeatherAPI, giữ server chạy |
| 04 — WeatherAPI | Current Hanoi và forecast ba ngày thành công | checks.mcp_protocol.live_weather.outputs trong [live_setup.json](evidence/live_setup.json) |
| 04 — Native Gemini/ADK Runner | Function call → MCP response → câu trả lời tiếng Việt | checks.live_agent trong [live_setup.json](evidence/live_setup.json); Google ADK Gemini native qua YesScale |
| 04 — ADK web | Browser thực hiện cùng vòng tool bằng Gemini qua YesScale/LiteLLM | [adk_web_chat.json](evidence/adk_web_chat.json), [ảnh chat](../screenshots/04-adk-weather-success.png), [ảnh response](../screenshots/04-adk-tool-response.png) |
| Bước 5 — Setup và hai câu hỏi | Preflight đạt; current dùng session đã có, forecast chạy session browser mới | [verify](evidence/step05_verify_setup.json), [current](evidence/adk_web_chat.json), [forecast](evidence/adk_web_forecast.json); đủ ba tên ảnh Bước 5 |

Toàn bộ ảnh có chú thích và nguồn tại [screenshots/README.md](../screenshots/README.md). Ảnh CLI là trình duyệt hiển thị stdout đã lưu từ chương trình; ảnh ADK là ứng dụng đang chạy. Bước 1 yêu cầu chụp terminal: [01-function-calling.png](../screenshots/01-function-calling.png) đã đúng tên và chứa output thật, nhưng **chưa phải ảnh cửa sổ terminal gốc**.

Bước 2 có [02-mcp-client.png](../screenshots/02-mcp-client.png) đúng tên; đây cũng là ảnh stdout trong trình duyệt. Yêu cầu ảnh cửa sổ terminal gốc của cả hai bước còn thiếu.

Bước 3 có đủ tên ảnh 03a-auth-ok/fail, 03b-registry, 03c-versioning. Chúng chụp stdout và access log thật trong trình duyệt; yêu cầu ảnh cửa sổ terminal gốc của bước này cũng còn thiếu.

## 2. Môi trường và cấu hình

Windows, Python **3.12.6**, uv **0.11.21**. Bước 01–03 có `.venv` ở gốc, đã cài `requirements.txt` và chạy pip check. Lab 04 có hai virtualenv/lockfiles riêng; pip check và lock check đạt. Evidence: [environment_checks.json](evidence/environment_checks.json), [preparation.json](evidence/preparation.json).

| Dependency client | Phiên bản |
|---|---|
| MCP | 2.3.0 |
| Google ADK | 2.12.0 |
| google-genai | 2.30.1 |
| LiteLLM | 1.105.1 |
| httpx | 0.28.1 |
| python-dotenv | 1.2.2 |

Ba cấu hình LLM được phân biệt:

- **Bước 01:** Google SDK, GEMINI_API_KEY là key YesScale, GEMINI_BASE_URL=https://api.yescale.io, model gemini-2.5-flash. Google API native /v1beta; không dùng OpenAI SDK ở phép thử này.
- **ADK Runner native:** LLM_PROVIDER=yescale-gemini, YESCALE_API_KEY, cùng host/model Gemini; GEMINI_STREAMING=0. Không cần Google key riêng.
- **ADK web đã thành công và env client hiện tại:** LLM_PROVIDER=yescale, LLM_MODEL=gemini-2.5-flash, YESCALE_BASE_URL=https://api.yescale.io/v1; LiteLLM adapter openai/gemini-2.5-flash. Model ID trong events cũng là gemini-2.5-flash.

Đây là IDs do request/response khai báo, không tự xác minh snapshot backend của provider. YesScale cung cấp LLM; server dùng WEATHERAPI_KEY riêng ở `04-lab/mcp-server/.env`. Secrets không được đưa vào examples, ảnh hoặc báo cáo.

MCP thực nghiệm chạy http://127.0.0.1:8085/mcp. Docker chiếm cổng 8000 nên ADK web chạy **8001**; không dừng Docker để chiếm cổng. Auth test chạy process/cổng local tạm. Đổi cổng ADK không đổi URL MCP.

## 3. Những điểm đã hoàn thiện

- Hướng dẫn có danh tính, phân biệt MCP/Function Calling, lệnh từ gốc repo, env Windows/Bash, checklist và nguồn evidence.
- Gemini SDK tắt automatic function calling: app whitelist tool, thực thi và gửi function responses; giới hạn bốn lượt. Test xác minh app thực thi thay vì SDK tự gọi hàm.
- Dependencies/locks tương thích MCP v2/ADK; bỏ dependency google-generativeai cũ ở client.
- Server chọn transport tường minh: HTTP loopback mặc định; stdio chỉ xuất giao thức ở stdout và log ở stderr. HTTP stateless JSON; PORT/host có thể cấu hình, không suy transport từ TTY.
- Schema/validation từ chối city rỗng/quá dài và forecast ngoài 1–3 ngày. Key/provider/mạng/schema lỗi trả MCP tool error, loại raw URL/body có thể chứa secrets.
- Health phân biệt MCP readiness, key presence và API verification. weather_api_verified=false là đúng vì health không gọi WeatherAPI; checks live mới xác minh API.
- Checker dùng MCP initialize → list_tools → health, không coi GET/HTTP 200 là đủ. Regression kiểm tra 404, unreachable, thiếu tools, health error và auth.
- ADK discovery bằng get_tools thật; không ghi kết nối thành công sau constructor hoặc âm thầm dùng agent không có tools.
- Native YesScale adapter có tùy chọn tắt provider streaming, nhưng không coi đó là cách đã sửa mọi lỗi 503. Cấu hình web dùng adapter đã chạy thành công, ghi provenance riêng.
- GitHub Actions local checks đã có source; chưa có evidence workflow GitHub thực thi. Docker image local đã build trước khi người dùng chọn bỏ qua phần tùy chọn; chưa kiểm tra container runtime hoặc deploy Cloud Run. [Evidence build](evidence/container_preparation.json) chỉ chứng minh build.

## 4. Diễn giải thực nghiệm

### Function Calling

[function_calling_gemini.json](evidence/function_calling_gemini.json), timestamp **2026-10-14T09:24:00.378097+00:00**, ghi model request/response gemini-2.5-flash. Model yêu cầu get_weather với Hà Nội và Đà Nẵng. App tự chạy hàm trả **29°C/30°C** từ bảng mock, gửi function responses rồi model trả lời và ghi rõ mock. Không có MCP trong luồng này.

Ba phần theo codelab là `get_weather_declaration` (schema), `get_weather(city)` (hàm mock), và vòng lặp trong `run()`. Bản hiện tại dùng `for _ in range(4)` để giới hạn số lượt thay cho `while resp.function_calls` không giới hạn. Trong mỗi lượt, `if not resp.function_calls` kết thúc bằng câu trả lời cuối; nếu có yêu cầu, **`result = get_weather(**fc.args)` mới thực thi hàm**. Đây vẫn là cùng luồng model yêu cầu → app chạy → gửi function response → model tổng hợp.

[function_calling_yescale.json](evidence/function_calling_yescale.json) là thí nghiệm **gpt-4o-mini/OpenAI-compatible** trước đó. Hash của file Gemini trong artifact lịch sử này không còn khớp source hiện tại sau khi bổ sung Gemini native. Giữ nó để đối chiếu lịch sử, không dùng thay evidence hiện hành bước 01.

### MCP và API thật

Ở bước 2, client khởi động weather_server.py bằng cùng interpreter qua stdio, initialize rồi đọc tên/mô tả/schema bằng list_tools. Description khớp docstring, city là string bắt buộc. Hàm thực thi ở server trả Hanoi 29°C, Danang 30°C, Haiphong 33°C. Đây là mock và không có model/API. Client lấy tên tool từ metadata; ba cities và tham số city là dữ liệu thử cố định, không phải khả năng tự chọn ý định.

Sau khi sửa client bước 2, [live_checks.json](evidence/live_checks.json) vẫn giữ hash của bản client cũ và bộ 32 tests trước đó. Đây là batch tổng hợp lịch sử; không sửa hash để làm nó giống code mới. API evidence trong live_setup.json và function_calling_gemini.json giữ source hashes riêng, không có thay đổi source LLM/server tương ứng và không chạy lại API chỉ để cập nhật batch tổng hợp. Local checks hiện hành được chạy lại offline.

### Auth, registry và versioning

[Batch bước 3](evidence/production/production_results.json) chạy MCP thật trên loopback **8002**, vì Docker giữ cổng 8000. Auth client hợp lệ in Tools và Hanoi 29°C. Token sai exit 1, không có tool list và HTTP response hook ghi **401**; request không token cũng 401. Đây khác dòng hướng dẫn nói token sai 403, nhưng đúng kết quả SDK 2.3.0. Không có thực nghiệm scope denial/403.

Registry tìm hai weather matches, chọn get_weather_v2 active 2.0.0 bằng semantic version comparison rồi gọi server weather-v2 qua stdio. Không gọi email/database hoặc model. Versioning đọc version/deprecation/migration từ resource, gọi v1 trả chuỗi và v2 trả api_version 2.0 với hai forecast rows; gọi thêm v2 chỉ với city để xác minh units celsius và không forecast mặc định.

Auth server được dừng trong finally, kiểm tra process exit và socket đóng; batch ghi auth_server_stopped=true. Windows launcher được dừng cùng cây tiến trình, nên exit code 1 sau forced stop là trạng thái dừng chủ động, không phải auth demo khởi động thất bại. Source hashes/outputs của batch bước 3 được giữ riêng trong evidence/production để checker không ghi đè stdout của cùng lần chạy.

MCP thương lượng protocol **2025-11-25**, công bố get_current_weather, get_forecast, health_check. Discovery local không gọi LLM/WeatherAPI. Batch native live tại **2026-10-14T09:35:12.383147+00:00** lấy current Hanoi **33.9°C**, feels-like **35.9°C**, humidity **42%**, cập nhật **2026-10-14 16:15**. Forecast có 14/15/16-10, nhiệt độ cao nhất **34.3/33.6/33.4°C**. Runner ghi đúng tool call/response rồi trả lời từ dữ liệu này.

Checkpoint Bước 4 đã kiểm tra lại server đang chạy ở 8085 bằng [readiness](evidence/step04_server_readiness.json), không tạo server khác hoặc chạy lại API ngoài. Bản hiện tại dùng MCPServer của SDK v2, transport HTTP tường minh và bind loopback; không chọn theo stdin.isatty() hoặc in ba dòng biểu tượng như starter. Thiếu key trả MCP tool error; health trả object và không xác minh provider. Các khác biệt đã ghi trong [README server](../04-lab/mcp-server/README.md).

### ADK web và lỗi provider

Các phiên browser native gặp **503** từ YesScale sau khi MCP tool trả dữ liệu. Tắt provider token streaming vẫn có 503; một phiên còn trả chuỗi `<<<call:...>>>` dưới dạng text, không thực thi tool. Những phiên này không được đánh dấu hoàn tất. [Ảnh lỗi](../screenshots/04-adk-provider-503.png) được giữ; chưa đủ dữ liệu xác định nguyên nhân nội bộ gateway.

Sau khi đổi sang LiteLLM/OpenAI-compatible **vẫn dùng Gemini 2.5 Flash**, browser đã hoàn tất. [adk_web_chat.json](evidence/adk_web_chat.json) được trích từ response SSE thật: functionCall get_current_weather(city=Hanoi), functionResponse isError=false, rồi final text. Dữ liệu cập nhật **2026-10-14 16:30**, **33.9°C**, **42%**. Hai model events khai báo gemini-2.5-flash. Đây là một phiên thành công, không chứng minh provider luôn sẵn sàng hoặc adapter chắc chắn là nguyên nhân khiến phiên đạt.

Bước 5 giữ phiên current đó và chụp lại thành [04-adk-current.png](../screenshots/04-adk-current.png), không chạy thêm current API. Phiên forecast mới tại [adk_web_forecast.json](evidence/adk_web_forecast.json) có functionCall get_forecast(city=Hanoi, days=3), response isError=false và final answer tiếng Việt. [SSE gốc](evidence/adk_web_forecast.sse.txt) được lưu từ browser POST /run_sse; ba ngày 14/15/16-10 có cao/thấp **34.3/24.9**, **33.6/24.8**, **33.4/24.2°C**, khả năng mưa **5/10/17%**, UV **7.6/7.4/8.3**. Các giá trị và ngày trong final khớp tool response; [ảnh forecast](../screenshots/04-adk-forecast.png) thấy cả câu hỏi, hai tool events và trả lời. Forecast gồm hôm nay và hai ngày sau; tool hiện không công bố Last updated cho forecast.

[Preflight Bước 5](evidence/step05_verify_setup.json) xác nhận dependencies, MCP và ADK discovery; các mục live giữ not_run vì script không gọi API ngoài. [Ảnh verify_setup](../screenshots/04-verify-setup.png) chụp stdout thật trong trình duyệt, chưa phải cửa sổ terminal. Bản hiện tại dùng MCP handshake thay GET dưới 500, in từng trạng thái thay All checks passed và không âm thầm tạo fallback agent không có tools. [README client](../04-lab/mcp-client/README.md) ghi các khác biệt này cùng cấu hình YesScale và cổng 8001.

### Tests và provenance

[pytest.txt](evidence/pytest.txt)/[pytest.xml](evidence/pytest.xml) ghi **35 passed, 6 warnings**. Warnings experimental/deprecated từ Google ADK; không có failures. WeatherAPI contract dùng mocks (success, timeout, HTTP 403, invalid JSON, thiếu key/dữ liệu). MCP/auth/ADK discovery integration chạy SDK/network/process local thật. Tests Gemini gateway dùng SDK mocks; API execution được chứng minh bởi artifacts live riêng. Hai tests bước 2 kiểm tra schema/docstring/kết quả qua process thật và tên remote thay đổi/ambiguity. Test production mới chạy cả ba demo bằng process thật, kiểm tra token sai không liệt kê được tool, không lộ token trong outputs và auth server được dừng sau batch.

Source hashes trong artifacts hiện hành giúp đối chiếu source; không tự chứng minh chất lượng/API execution. [adk_web_readiness.json](evidence/adk_web_readiness.json) là check HTTP readiness trước phiên chat; trường browser_chat_tested=false chỉ mô tả phép thử cũ đó. [adk_web_chat.json](evidence/adk_web_chat.json) là evidence chat mới. Không chỉnh trạng thái artifact cũ để làm nó giống kết quả mới.

## 5. Tái lập

Từ gốc repo, cài Python ≥3.12 và uv, tạo env từ examples nếu chưa có:

~~~bash
uv sync --locked --project 04-lab/mcp-client --python 3.12
uv sync --locked --project 04-lab/mcp-server --python 3.12
uv run --project 04-lab/mcp-client python scripts/check_lab.py
~~~

Checker mặc định chạy tests/demos, server tạm, MCP/ADK discovery; không gọi API ngoài. Lần cuối có thể dùng --skip-tests nếu tests đã chạy trên cùng source; JSON ghi not_run, không tự nhận đã chạy lại.

Khi cần tái lập API (có thể phát sinh chi phí):

~~~bash
uv run --project 04-lab/mcp-client python 01-function-calling/weather_function_calling.py --output reports/evidence/function_calling_gemini.json
uv run --project 04-lab/mcp-client python scripts/check_lab.py --live-agent --live-weather
~~~

Để tái lập batch native, đặt LLM_PROVIDER=yescale-gemini trong env client; để tái lập browser đã đạt, dùng cấu hình mẫu LLM_PROVIDER=yescale, LLM_MODEL=gemini-2.5-flash. Artifacts có configuration để phân biệt lần chạy; lệnh live mới có thể thay kết quả/timestamp cũ.

Hai terminal cho browser:

~~~bash
# Terminal 1
uv run --project 04-lab/mcp-server python 04-lab/mcp-server/weather.py --transport streamable-http
# Terminal 2
uv run --directory 04-lab/mcp-client adk web --port 8001
~~~

Mở http://127.0.0.1:8001, chọn weather_agent, hỏi “Hãy gọi get_current_weather với city Hanoi, rồi báo thời tiết hiện tại và thời điểm cập nhật.” Đối chiếu tool events và final answer; thời tiết sẽ thay đổi, không ép số trùng bản lưu.

## 6. Giới hạn và trạng thái repo

- Code/API bước 1, protocol bước 2 và ba demo bước 3 đạt checkpoint chạy; ảnh đúng tên đã có nhưng là stdout/access log xem trong trình duyệt. Yêu cầu ảnh cửa sổ terminal gốc của codelab còn thiếu.
- Local lab và hai phiên ADK web đã có. Cloud Run được bỏ qua theo yêu cầu vì không bắt buộc; không có URL remote hoặc ảnh 05-cloud-run. Docker image local đã build, chưa kiểm tra runtime container; chưa benchmark chịu tải hoặc kiểm tra scope enforcement.
- Auth static token là demo, không thay xác thực/HTTPS/secrets management khi mở dịch vụ public.
- Gemini trực tiếp tới Google chưa chạy; **Google SDK tới Gemini qua YesScale đã chạy**. Không cần thêm key cho cấu hình hiện tại.
- Không tự quy đổi tests pass thành điểm tối đa. Grader/giảng viên còn đối chiếu nội dung và phạm vi evidence.
- Fork public đã xác nhận bằng GitHub API không xác thực. Bản nộp dùng nhánh main, lưu source/reports/screenshots cùng nhau; đối chiếu commit trên [GitHub](https://github.com/Neon310304/K4-DAY26-TranQuocVuong-2A202602522/commits/main). `.gitattributes` giữ byte source/evidence qua checkout Windows/Linux để hashes không đổi vì tự chuyển xuống dòng.

## 7. Công việc và evidence đóng góp

Trần Quốc Vượng — 2A202602522: tích hợp SDK/ADK/providers, chuẩn hóa transport/schema/lỗi/key, bổ sung checker/tests, chạy local/live/browser experiments, lưu ảnh và hoàn thiện hướng dẫn/báo cáo. Evidence nằm trong source, tests, reports/evidence và screenshots.
