# Thông tin triển khai

## URL công khai

https://k5-day14-agent-5ss8.onrender.com

Mở URL trên trong trình duyệt để dùng giao diện hỏi đáp; nhập API key hiện tại trên Render rồi gửi câu hỏi. Giao diện không lưu key vào `localStorage` hoặc cookie.

## Nền tảng và cấu hình

- **Nền tảng:** Render Blueprint.
- **Tệp cấu hình:** [`06-lab-complete/render.yaml`](06-lab-complete/render.yaml).
- **Ứng dụng:** Docker service, thư mục gốc `06-lab-complete/`, vùng Singapore, kiểm tra tình trạng tại `/health`.
- **Redis:** Render Key Value; `REDIS_URL` được nối tự động từ dịch vụ Redis.
- **Biến môi trường:** `AGENT_API_KEY` do Render tạo; `ENVIRONMENT`, `RATE_LIMIT_PER_MINUTE`, `DAILY_BUDGET_USD` và `REDIS_URL` được cấu hình trên Render. Không lưu giá trị bí mật trong repository.

## Kiểm tra dịch vụ

Lấy `AGENT_API_KEY` tại Render Dashboard → dịch vụ → **Environment**. Đặt URL và nhập khóa vào terminal trước khi gọi API; không ghi khóa trực tiếp vào lệnh, tệp hoặc ảnh chụp màn hình:

```bash
BASE="https://k5-day14-agent-5ss8.onrender.com"
read -rsp 'Nhập AGENT_API_KEY lấy từ Render: ' AGENT_API_KEY
printf '\n'
export BASE AGENT_API_KEY
```

| Lệnh | Kết quả mong đợi | Đã kiểm tra |
|---|---:|---:|
| `curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"` | 200 | 200 |
| `curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"` | 200 | 200 |
| Gửi `POST /ask` với JSON hợp lệ nhưng không có `X-API-Key` | 401 | 401 |
| Gửi `POST /ask` với khóa API đúng | 200 | 200 |

Lệnh kiểm tra thiếu khóa:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Kiểm tra thiếu khóa"}'
```

Lệnh kiểm tra yêu cầu có khóa đúng:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Kiểm tra dịch vụ"}'
```

Các kết quả kiểm tra chỉ in mã HTTP; không in câu trả lời hay giá trị khóa. Trên gói miễn phí, dịch vụ web có thể ngủ khi không có traffic; yêu cầu đầu tiên sau đó có thể mất khoảng 50 giây hoặc hơn. Redis miễn phí không có bảo đảm lưu trữ lâu dài, vì vậy chỉ phù hợp cho bài thực hành.
