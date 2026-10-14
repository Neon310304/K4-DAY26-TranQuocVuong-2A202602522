# Ảnh bằng chứng Day26

Ảnh chụp ngày 14/10/2026. Repo và ADK là trang/ứng dụng thật. Các ảnh CLI chụp trình duyệt đang mở **stdout đã lưu từ lần chạy thật** trong `reports/evidence/`, không phải cửa sổ terminal. Không dựng lại nội dung hoặc dùng ảnh thay cho JSON/evidence nguồn.

| Phần | Ảnh | Nguồn và phạm vi |
|---|---|---|
| Chuẩn bị | [00-repo-fork.png](00-repo-fork.png) | GitHub public, fork từ starter, tên đúng; [5/5 checklist](../reports/evidence/preparation.json) |
| 01 | [01-function-calling.png](01-function-calling.png) | [stdout](../reports/evidence/function_calling_gemini.txt), [JSON](../reports/evidence/function_calling_gemini.json): Google SDK/Gemini thật qua YesScale, app tự chạy hai weather tools mock. Ảnh hiển thị stdout trong trình duyệt; chưa có ảnh cửa sổ terminal gốc |
| 02 | [02-mcp-client.png](02-mcp-client.png) | [stdout](../reports/evidence/weather_client.txt), [metadata/schema/results](../reports/evidence/mcp_stdio.json): list_tools/call_tool qua MCP stdio thật, weather mock. Ảnh stdout trong trình duyệt; chưa có ảnh terminal gốc |
| 03a Auth hợp lệ | [03a-auth-ok.png](03a-auth-ok.png) | [stdout](../reports/evidence/production/auth-ok.txt), [JSON](../reports/evidence/production/auth_ok.json): Tools có auth và kết quả Hanoi 29°C |
| 03a Auth bị từ chối | [03a-auth-fail.png](03a-auth-fail.png) | [stdout + server access log](../reports/evidence/production/auth-fail.txt), [JSON](../reports/evidence/production/auth_fail.json): HTTP 401, không list/call tool |
| 03b Registry | [03b-registry.png](03b-registry.png) | [stdout](../reports/evidence/production/registry_client.txt), [JSON](../reports/evidence/production/registry_client.json): hai weather matches, chọn v2 active bằng Python |
| 03c Versioning | [03c-versioning.png](03c-versioning.png) | [stdout](../reports/evidence/production/versioned_client.txt), [JSON](../reports/evidence/production/versioned_client.json): v1/v2 và resource metadata |
| 04 MCP | [04-mcp-server-8085.png](04-mcp-server-8085.png) | [stdout](../reports/evidence/server8085.txt), [JSON](../reports/evidence/server8085.json): handshake + ADK discovery trên endpoint 8085; không gọi LLM ở check này |
| Bước 5 Setup | [04-verify-setup.png](04-verify-setup.png) | [stdout](../reports/evidence/step05_verify_setup.txt), [JSON](../reports/evidence/step05_verify_setup.json): preflight protocol/discovery thật, không gọi API ngoài. Ảnh stdout trong trình duyệt, không phải cửa sổ terminal |
| Bước 5 Current | [04-adk-current.png](04-adk-current.png) | ADK web thật, chụp lại session current đã đạt trong [events](../reports/evidence/adk_web_chat.json). Có câu hỏi, tool call/response, 33.9°C và cập nhật 16:30; không chạy current API thêm |
| Bước 5 Forecast | [04-adk-forecast.png](04-adk-forecast.png) | Phiên ADK web mới, [events](../reports/evidence/adk_web_forecast.json), [SSE gốc](../reports/evidence/adk_web_forecast.sse.txt): get_forecast(Hanoi, 3), ba ngày có cao/thấp, khả năng mưa và UV |
| 04 Agent | [04-adk-weather-success.png](04-adk-weather-success.png) | ADK web 8001, tool call/response và câu trả lời thời tiết thật; [events](../reports/evidence/adk_web_chat.json). Gemini qua YesScale/LiteLLM |
| 04 Tool response | [04-adk-tool-response.png](04-adk-tool-response.png) | Response MCP thật: isError=false, Hanoi 33.9°C, cập nhật 2026-10-14 16:30 |
| Phiên lỗi được giữ | [04-adk-provider-503.png](04-adk-provider-503.png) | YesScale native Gemini 503 sau tool response; không phải evidence phiên chat thành công |

MCP server dùng 8085. ADK dùng 8001 vì Docker giữ cổng 8000. Ảnh không chứa key, nội dung env hoặc Authorization header.

`01-function-calling-gemini.png` được giữ dưới tên cũ để không làm mất liên kết trước đó; `01-function-calling.png` có cùng nội dung và đúng tên codelab yêu cầu. Yêu cầu **ảnh terminal** vẫn cần một ảnh chụp cửa sổ terminal thực; việc đổi tên không thay đổi loại bằng chứng.

`02-mcp-stdio.png` giữ ảnh lần chạy trước. `02-mcp-client.png` là ảnh output sau khi cập nhật discovery của client, dùng tên đúng codelab. Cả hai là ảnh stdout trong trình duyệt, không phải ảnh cửa sổ terminal.

Bốn ảnh bước 3 cũng chụp stdout/access log thật trong trình duyệt, chưa phải ảnh cửa sổ terminal gốc. [production_results.json](../reports/evidence/production/production_results.json) ghi auth server đã dừng và URL 8002; 8000 vẫn do Docker giữ. Các ảnh 03-auth/03-registry/03-versioning dưới tên cũ được giữ từ lần thực nghiệm trước, không dùng thay bốn ảnh mới.

Hai ảnh Bước 5 current/forecast là giao diện ADK đang chạy. Ba tên ảnh Bước 5 đã đủ; ảnh verify_setup có đúng output thực tế, nhưng chưa phải ảnh cửa sổ terminal gốc. Script hiện dùng handshake/discovery thay GET và in trạng thái từng check thay dòng `All checks passed!` của starter.
