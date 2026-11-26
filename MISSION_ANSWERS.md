# Day 14 Lab — Câu trả lời nhiệm vụ

## Part 1: Từ Localhost đến Production

### Exercise 1.1: Các anti-pattern trong bản develop

1. **Secret bị ghi cứng trong mã nguồn:** `OPENAI_API_KEY` và `DATABASE_URL` được khai báo trực tiếp trong `develop/app.py`. Giá trị trong bài là mẫu giả, nhưng nếu áp dụng cách này với thông tin thật rồi đẩy mã lên repo công khai thì credentials có thể bị lộ.
2. **Ghi API key ra log:** endpoint `/ask` in `OPENAI_API_KEY` ra terminal. Dù key mẫu trong bài là giả, log trong ứng dụng thật có thể bị lưu hoặc gửi đến hệ thống giám sát, làm lộ secret.
3. **Cấu hình bị cố định:** `DEBUG` và `MAX_TOKENS` được đặt trong code, không thuận tiện để đổi theo môi trường chạy.
4. **Cố định địa chỉ và cổng:** server chỉ bind `localhost` và cổng `8000`. Nền tảng cloud/container thường cần ứng dụng đọc `PORT` từ biến môi trường và nhận kết nối từ bên ngoài.
5. **Luôn bật tự tải lại:** `reload=True` phù hợp khi phát triển, nhưng không nên mặc định bật trong production.
6. **Thiếu health check:** không có `/health` hoặc `/ready` để nền tảng kiểm tra ứng dụng còn sống và đã sẵn sàng nhận yêu cầu.
7. **Dùng `print()` thay cho logging có cấu trúc:** log khó lọc, phân tích; nội dung debug còn có nguy cơ tiết lộ dữ liệu nhạy cảm.
8. **Thiếu quản lý vòng đời ứng dụng:** bản develop không khai báo xử lý khởi động/dừng ứng dụng để dọn dẹp tài nguyên theo trình tự.

### Exercise 1.2: Chạy thử bản develop

- Khởi động ứng dụng bằng `python app.py`.
- Gửi `POST /ask?question=Hello`: ứng dụng trả về câu trả lời từ mock LLM.
- Gọi `GET /health`: nhận mã `404`, vì bản develop không có endpoint health check.
- Ghi chú trên Windows: đặt `PYTHONIOENCODING=utf-8` trước khi chạy để tránh lỗi in ký tự tiếng Việt trong terminal.
- Repo K5 dùng `question` qua query parameter cho bản develop; không gửi JSON body theo ví dụ chung trong `CODE_LAB.md`.

### Exercise 1.3: So sánh develop và production

| Nội dung | Develop (Basic) | Production (Advanced) | Vì sao quan trọng? |
|---|---|---|---|
| Cấu hình | Một số giá trị được ghi cố định trong code | Đọc `HOST`, `PORT`, `DEBUG` và cấu hình khác từ biến môi trường | Có thể đổi cấu hình theo môi trường mà không sửa mã |
| Bí mật | Có secret ghi trong code và in ra log | Đọc API key từ biến môi trường; không ghi key vào log request | Hạn chế lộ thông tin và hỗ trợ thay/thu hồi key |
| Địa chỉ/cổng | Chỉ nghe trên `localhost:8000` | Đọc host và cổng từ cấu hình; mặc định host là `0.0.0.0` | Cho phép nhận traffic từ bên ngoài container và dùng cổng nền tảng cấp |
| Chế độ debug | Luôn bật `reload=True` | Tự tải lại theo `DEBUG` | Tránh chạy chế độ phát triển ngoài production |
| Health/readiness | Không có endpoint tương ứng | `GET /health` kiểm tra process còn sống; `GET /ready` báo ứng dụng sẵn sàng nhận traffic (503 nếu chưa sẵn sàng) | Nền tảng dùng health để quyết định restart, readiness để quyết định có gửi traffic vào ứng dụng |
| Logging | Dùng `print()`, có thể in cả secret | Dùng logging với định dạng JSON và ghi sự kiện request/response | Log dễ thu thập, lọc và phân tích hơn |
| Vòng đời | Không có FastAPI lifespan riêng | Có lifespan startup/shutdown; Uvicorn quản lý tín hiệu dừng | Dừng có trật tự giúp tránh ngắt request đang xử lý và cho phép dọn tài nguyên trước khi thoát |
| Cách gửi câu hỏi | `question` là query parameter | `question` nằm trong JSON body | Cần dùng đúng định dạng request của từng ứng dụng |

### Câu hỏi thảo luận

1. **Nếu đẩy API key lên GitHub công khai thì sao?** Người khác có thể dùng key để truy cập dịch vụ hoặc phát sinh chi phí. Xóa key khỏi file sau đó không đảm bảo key biến mất khỏi lịch sử Git; cần thu hồi/thay key và kiểm tra hoạt động bất thường.
2. **Vì sao stateless quan trọng khi scale?** Nếu session chỉ nằm trong RAM của một instance, request tiếp theo chuyển sang instance khác sẽ không thấy session đó. Lưu state ở nơi dùng chung như Redis giúp nhiều instance cùng đọc/ghi và cho phép scale ngang.
3. **Dev/prod parity là gì?** Làm cho môi trường phát triển gần với production về phiên bản runtime, dependencies và cách chạy để giảm lỗi chỉ xuất hiện sau deploy. Cấu hình riêng và secret vẫn nên được cấp qua environment, không ghi vào code.

## CP1 — Tự kiểm tra

### Ví dụ anti-pattern được production khắc phục (kèm dòng mã)

- **Hardcode API key:** bản develop gán trực tiếp `OPENAI_API_KEY` ở [develop/app.py, dòng 17](01-localhost-vs-production/develop/app.py#L17), rồi còn in key ra log ở [develop/app.py, dòng 34](01-localhost-vs-production/develop/app.py#L34). Bản production đọc key từ biến môi trường tại [production/config.py, dòng 27](01-localhost-vs-production/production/config.py#L27); log request chỉ ghi event, độ dài câu hỏi và IP, không ghi key ở [production/app.py, dòng 111](01-localhost-vs-production/production/app.py#L111).
- **Cổng và debug cố định:** develop bind `localhost`, cố định cổng `8000` và luôn bật `reload=True` tại [develop/app.py, dòng 51](01-localhost-vs-production/develop/app.py#L51), [dòng 52](01-localhost-vs-production/develop/app.py#L52) và [dòng 53](01-localhost-vs-production/develop/app.py#L53). Production lấy host, port và debug từ cấu hình tại [production/app.py, dòng 196](01-localhost-vs-production/production/app.py#L196) đến [dòng 198](01-localhost-vs-production/production/app.py#L198); port được đọc từ biến môi trường `PORT` tại [production/config.py, dòng 18](01-localhost-vs-production/production/config.py#L18).
- **Thiếu health check:** develop không khai báo endpoint `/health`, còn production có `GET /health` tại [production/app.py, dòng 135](01-localhost-vs-production/production/app.py#L135) và `GET /ready` tại [dòng 152](01-localhost-vs-production/production/app.py#L152).

**Đối chiếu CP1:** đã nêu hơn 5 anti-pattern, ghi nhận kết quả chạy bản develop (`/ask` trả lời và `/health` trả 404), có bảng so sánh kèm lý do, và có các ví dụ đối chiếu mã nguồn cụ thể ở trên. Như vậy các sản phẩm CP1 trong checkpoint đã có đủ.

- **Hardcode secret nguy hiểm:** secret có thể bị lộ trong mã nguồn, Git history hoặc log; nếu là key thật cần thu hồi/thay key.
- **Biến môi trường:** production lấy `OPENAI_API_KEY` từ environment ở `config.py:27` và `PORT` ở `config.py:18`, giúp đổi cấu hình mà không sửa code.
- **Health và readiness:** `/health` trả lời “process còn sống không?”; `/ready` trả lời “đã sẵn sàng nhận traffic chưa?” và có thể trả 503 khi chưa sẵn sàng.
- **Graceful shutdown:** dừng nhận công việc mới, để request đang xử lý hoàn tất, dọn tài nguyên rồi mới thoát. Ví dụ production có FastAPI lifespan để chạy logic startup/shutdown; bản mẫu không có bộ đếm request đang xử lý riêng.
- **Ví dụ anti-pattern đã đối chiếu:** develop cố định port `8000` ở dòng 52; production đọc `PORT` trong `config.py:18`.

## Part 2: Docker

### Exercise 2.1: Đọc Dockerfile cơ bản

1. **Base image:** `python:3.11`, bản Python đầy đủ; thuận tiện để học nhưng image lớn.
2. **Working directory:** `/app` bên trong container, được đặt bằng `WORKDIR /app`.
3. **Vì sao chép `requirements.txt` trước mã nguồn?** Docker cache từng layer. Khi chỉ sửa mã nguồn, layer cài dependencies vẫn được dùng lại; chỉ khi requirements đổi thì bước cài package mới cần chạy lại.
4. **`CMD` và `ENTRYPOINT`:** `CMD` đặt lệnh/đối số mặc định và có thể bị thay thế khi chạy container. `ENTRYPOINT` xác định chương trình chính sẽ chạy; đối số truyền lúc `docker run` thường được nối vào nó. Trong Dockerfile basic, `CMD ["python", "app.py"]` là lệnh mặc định để khởi động ứng dụng.

### Exercise 2.2–2.3: Build, chạy và so sánh image

- Đã build image bằng Dockerfile develop và chạy container `agent-develop`; `GET /health` trả `status: ok`, `POST /ask?question=Hello` trả về trường `answer`.
- Đã build và chạy Dockerfile production theo hai stage. Stage `builder` cài dependencies và công cụ build; stage `runtime` bắt đầu từ `python:3.11-slim`, chỉ chép các package/mã cần chạy, chạy bằng user không phải root và khai báo `HEALTHCHECK`.
- Số đo từ `docker image ls` trên máy làm bài:

| Image | Kích thước hiển thị |
|---|---:|
| `agent-develop:latest` | 1.67 GB |
| `agent-production:latest` | 240 MB |



- Bản production giảm xấp xỉ **86%** so với bản develop. Tỉ lệ ước tính từ số đã làm tròn mà Docker hiển thị: `(1.67 GB - 240 MB) / 1.67 GB × 100%`.

### Exercise 2.4: Compose stack và kiểm tra qua Nginx

Sơ đồ dịch vụ trong `02-docker/production/docker-compose.yml`:

```text
Client
  │ HTTP :80
  ▼
Nginx (reverse proxy)
  │
  ▼
Agent (FastAPI, cổng nội bộ 8000)

Redis ── volume redis_data
Qdrant ── volume qdrant_data
```

- Đã khởi động stack bằng Docker Compose; các service `agent`, `redis`, `qdrant` và `nginx` đều chạy, health check của agent/Redis/Qdrant ở trạng thái healthy.
- Đã kiểm tra qua Nginx: `GET http://localhost/health` trả `status: ok`; `POST http://localhost/ask` với JSON `{"question":"What is Docker?"}` trả về câu trả lời.
- Nginx nhận traffic ngoài ở cổng 80 rồi chuyển tiếp vào agent trong network nội bộ. Redis và Qdrant được khai báo như các service hạ tầng trong stack, không publish cổng trực tiếp ra host; bản `main.py` demo chưa gọi trực tiếp các dịch vụ này.
- Ghi chú: Docker Compose hiện cảnh báo thuộc tính `version` trong file YAML đã cũ và bị bỏ qua; cảnh báo không ngăn stack chạy.


## Part 4: API Security

### Exercise 4.1: Dùng API key

Với bản develop, client gửi API key trong header `X-API-Key` khi gọi `POST /ask`. Ứng dụng đọc key từ biến `AGENT_API_KEY`; nếu biến chưa đặt thì code dùng key demo mặc định ([develop/app.py, dòng 35](04-api-gateway/develop/app.py#L35)). Phần kiểm tra key nằm ở [dòng 39](04-api-gateway/develop/app.py#L39), và được áp dụng cho `/ask` ở [dòng 67](04-api-gateway/develop/app.py#L67).

Kết quả thử nghiệm:

- Không gửi key: **401 Unauthorized**.
- Gửi key sai: **403 Forbidden**.
- Gửi key đúng: **200 OK**.

Nếu key bị lộ, hãy thay key trong cấu hình môi trường rồi khởi động lại ứng dụng. Không nên dùng key thật trong source code hoặc báo cáo. Lưu ý: bản develop còn in key lúc khởi động, nên đây chỉ là ví dụ học tập, không nên mang nguyên trạng lên dịch vụ thật.

### Exercise 4.2: Đăng nhập bằng JWT

Ở bản production, client gửi username và password đến `POST /auth/token` để nhận JWT. Theo hướng dẫn riêng của lớp K5, dùng tài khoản demo `student` / `demo123`; không dùng đường dẫn `/token` hay tài khoản `admin` / `secret` trong ví dụ cũ của CODE_LAB. Sau khi đăng nhập, gửi token trong header `Authorization: Bearer <token>` khi gọi `/ask`. Token có hạn 60 phút. Luồng đăng nhập nằm ở [production/app.py, dòng 105](04-api-gateway/production/app.py#L105); kiểm tra token ở [production/auth.py, dòng 45](04-api-gateway/production/auth.py#L45).

Mình đã kiểm tra: gọi `/ask` không có token trả **401**; dùng token hợp lệ trả **200**. Không chép JWT thật vào bài nộp.

### Exercise 4.3: Giới hạn số request

Rate limit giúp một tài khoản không gửi quá nhiều request trong thời gian ngắn. Bản này lưu thời điểm của từng request trong 60 giây gần nhất rồi đếm chúng — cách hoạt động gần với sliding-window log (dù chú thích trong file gọi là “Sliding Window Counter”).

- User được tối đa **10 request/phút**.
- Admin được tối đa **100 request/phút**; admin không được bỏ giới hạn, chỉ có hạn mức cao hơn.
- Các con số được khai báo trong [production/rate_limiter.py, dòng 86](04-api-gateway/production/rate_limiter.py#L86) và [dòng 87](04-api-gateway/production/rate_limiter.py#L87).

Mình đã gọi 10 request hợp lệ bằng user `student`; cả 10 trả **200**. Request thứ 11 trả **429 Too Many Requests**, kèm `Retry-After` để báo client chờ trước khi thử lại. Bộ đếm mẫu nằm trong RAM nên sẽ không dùng chung giữa nhiều process và không bền sau khi ứng dụng khởi động lại.

**Một phần output `curl -i` đã kiểm tra** (đã bỏ ngày giờ và không ghi JWT):

```text
# Không gửi JWT
HTTP/1.1 401 Unauthorized
{"detail":"Authentication required. Include: Authorization: Bearer <token>"}

# JWT hợp lệ
HTTP/1.1 200 OK
{"question":"what is docker?","answer":"..."}

# Request thứ 11 trong một phút
HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
retry-after: 59
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```


### Exercise 4.4: Cost guard

- Rate limit giới hạn **tốc độ gọi**; cost guard giới hạn **tiền được phép tiêu**. Hai lớp này bảo vệ hai rủi ro khác nhau.
- Ứng dụng kiểm tra ngân sách trước khi gọi LLM ([production/app.py, dòng 145](04-api-gateway/production/app.py#L145)) và ghi nhận token/chi phí sau khi gọi ([dòng 153](04-api-gateway/production/app.py#L153)).
- Bản demo đặt hạn mức **$1/ngày cho mỗi user**, cảnh báo khi đã dùng 80%, và **$10/ngày cho toàn hệ thống** ([production/cost_guard.py, dòng 43](04-api-gateway/production/cost_guard.py#L43), [dòng 128](04-api-gateway/production/cost_guard.py#L128)). Vượt hạn mức user trả 402; vượt hạn mức chung trả 503.
- Đây vẫn là bản minh họa: số liệu chỉ giữ trong RAM, không lưu vào Redis. Hạn mức từng user được làm mới theo ngày, nhưng bộ đếm tổng chưa tự reset theo ngày. Vì vậy chưa nên xem đây là giải pháp production hoàn chỉnh.
- Một điểm chưa khớp trong response: `budget_remaining_usd` tại [production/app.py, dòng 160](04-api-gateway/production/app.py#L160) đang nhận chi phí đã dùng (`usage.total_cost_usd`), không phải số tiền còn lại. Mình ghi nhận điểm này, không sửa code vì CP3 yêu cầu phân tích và kiểm tra.

### Tự kiểm tra CP3

- [x] Thiếu xác thực bị từ chối, xác thực hợp lệ gọi được API.
- [x] Gửi quá 10 request trong một phút thì thấy mã 429.
- [x] Hiểu rằng rate limit hạn chế tốc độ gọi, còn cost guard hạn chế chi phí.

## Part 5 — Mở rộng và vận hành tin cậy

### Kiểm tra tình trạng và dừng an toàn

- `GET /health` cho biết ứng dụng còn hoạt động hay không. `GET /ready` cho biết ứng dụng đã sẵn sàng nhận yêu cầu chưa; khi đang khởi động hoặc dừng, endpoint này trả 503. Hai phần này nằm trong [develop/app.py](05-scaling-reliability/develop/app.py#L104) và [dòng 147](05-scaling-reliability/develop/app.py#L147).
- Ứng dụng đếm số yêu cầu đang xử lý. Khi nhận tín hiệu dừng, ứng dụng ngừng báo sẵn sàng và chờ các yêu cầu đó hoàn tất, tối đa 30 giây ([develop/app.py](05-scaling-reliability/develop/app.py#L38), [dòng 42](05-scaling-reliability/develop/app.py#L42)).
- Đã kiểm tra trong WSL: `/health` và `/ready` đều trả **200**. Khi gửi tín hiệu SIGTERM trong lúc `POST /ask` đang chạy, yêu cầu vẫn trả **200**; Uvicorn kết thúc với mã **0** và ghi nhận quá trình dừng hoàn tất.

### Chạy nhiều bản và giữ lịch sử hội thoại

- Nếu lưu lịch sử trong bộ nhớ của từng ứng dụng, yêu cầu tiếp theo có thể đến ứng dụng khác và không tìm thấy hội thoại cũ. Bản production lưu dữ liệu trong Redis để mọi ứng dụng cùng đọc, ghi được; dữ liệu hết hạn sau một giờ. Cách lưu và đọc nằm trong [production/app.py](05-scaling-reliability/production/app.py#L59); mỗi hội thoại giữ tối đa 20 tin nhắn ([dòng 76](05-scaling-reliability/production/app.py#L76)).
- Tệp Compose khởi chạy 3 ứng dụng, Redis và Nginx. Nginx chia yêu cầu giữa các ứng dụng; cổng truy cập từ máy cá nhân là **8080**. Có thể xem ứng dụng nào đã xử lý yêu cầu trong `X-Served-By` tại [nginx.conf](05-scaling-reliability/production/nginx.conf#L9) và [dòng 17](05-scaling-reliability/production/nginx.conf#L17).
- Đã chạy [`test_stateless.py`](05-scaling-reliability/production/test_stateless.py). Kết quả chính:

  ```text
  Session ID: 3963d9bb-da2a-41a5-b625-6aef0973fefb
  Request 1: instance-7f857e
  Request 2: instance-e99614
  Request 3: instance-f176ec
  Request 4: instance-7f857e
  Request 5: instance-e99614
  Total requests: 5
  Instances used: {'instance-e99614', 'instance-7f857e', 'instance-f176ec'}
  Total messages: 10
  ✅ All requests served despite different instances!
  ✅ Session history preserved across all instances via Redis!
  ```

  Năm câu hỏi được chuyển đến **cả ba ứng dụng** khác nhau, nhưng vẫn dùng chung một mã phiên. Lịch sử có đủ 10 tin nhắn — mỗi câu hỏi và câu trả lời được ghi lại — chứng minh Redis giữ dữ liệu dùng chung thay vì chỉ lưu trong bộ nhớ của một ứng dụng. Câu trả lời là dữ liệu mô phỏng nên nội dung có thể thay đổi giữa các lần chạy. Tệp thử này không tự dừng ứng dụng; để kiểm tra tình huống một ứng dụng gặp lỗi, mình đã dừng riêng một ứng dụng.
- Sau khi một ứng dụng dừng, **12/12 yêu cầu** tiếp theo vẫn thành công qua hai ứng dụng còn lại; lịch sử hội thoại vẫn đọc được từ Redis. Kết quả trả về 20 tin nhắn vì ứng dụng chỉ giữ 20 tin nhắn gần nhất. Sau thử nghiệm, mình khởi động lại ứng dụng đó rồi dừng riêng cụm Part 5; các container CP2 vẫn chạy.

Lệnh chạy lại từ `05-scaling-reliability/production/`:

```bash
docker compose -p k5-day14-scaling up -d --build --scale agent=3
python test_stateless.py
docker compose -p k5-day14-scaling down
```

## Part 6 — Dự án cuối: Trợ lý AI sẵn sàng vận hành

Đối chiếu yêu cầu CP5 trong [CHECKPOINTS.md](CHECKPOINTS.md): phần mã đã đạt **12/12**. Phần còn thiếu trong báo cáo là danh sách đầy đủ các mục bàn giao theo kết quả chấm; danh sách đó được bổ sung bên dưới.

### Những phần đã hoàn thành

- **Cấu hình:** ứng dụng đọc `AGENT_API_KEY`, `REDIS_URL`, `RATE_LIMIT_PER_MINUTE`, `DAILY_BUDGET_USD`, `PORT` và `ENVIRONMENT` từ biến môi trường; tên và giá trị mẫu được ghi trong [.env.example](06-lab-complete/.env.example). Khóa API sai hoặc bị thiếu bị từ chối bằng mã 401 tại [auth.py](06-lab-complete/app/auth.py#L19).
- **Kiểm tra tình trạng:** `GET /health` luôn trả 200 khi tiến trình còn chạy. `GET /ready` trả 503 nếu Redis chưa sẵn sàng; mã xử lý nằm ở [main.py](06-lab-complete/app/main.py#L82) và [redis_client.py](06-lab-complete/app/redis_client.py#L22).
- **Bảo vệ `/ask`:** ứng dụng kiểm tra khóa API, giới hạn số lần gọi trong 60 giây bằng Redis, rồi kiểm tra ngân sách trước khi gọi mô hình giả lập. Vượt giới hạn trả 429 kèm `Retry-After` tại [rate_limiter.py](06-lab-complete/app/rate_limiter.py#L40); hết ngân sách trả 402 tại [cost_guard.py](06-lab-complete/app/cost_guard.py#L25).
- **Ghi nhật ký và dừng an toàn:** mỗi dòng nhật ký của ứng dụng là một đối tượng JSON. Khi nhận SIGTERM, Uvicorn chờ yêu cầu đang xử lý hoàn tất; phần quản lý khởi động và dừng nằm trong [main.py](06-lab-complete/app/main.py#L26) và lệnh chạy trong [Dockerfile](06-lab-complete/Dockerfile#L26).
- **Đóng gói và đưa lên máy chủ:** Dockerfile dùng nhiều giai đoạn, ảnh nền `python:3.11-slim`, tài khoản không phải root và có kiểm tra tình trạng. Tệp Compose chạy ứng dụng cùng Redis tại [docker-compose.yml](06-lab-complete/docker-compose.yml); [railway.toml](06-lab-complete/railway.toml) cấu hình kiểm tra `/health`.

### Danh sách bàn giao — đủ 12/12

- [x] Dockerfile nhiều giai đoạn; ảnh Docker nhỏ hơn 500 MB.
- [x] Tệp Compose chạy ứng dụng và Redis.
- [x] `.dockerignore` loại trừ tệp bí mật và bộ nhớ đệm Python.
- [x] `GET /health` báo tiến trình còn hoạt động.
- [x] `GET /ready` báo ứng dụng đã sẵn sàng.
- [x] Xác thực khóa API; thiếu hoặc sai khóa trả 401.
- [x] Giới hạn số lần gọi; vượt mức trả 429.
- [x] Giới hạn ngân sách; hết ngân sách trả 402.
- [x] Đọc cấu hình từ biến môi trường và liệt kê trong `.env.example`.
- [x] Ghi nhật ký theo định dạng JSON.
- [x] Dừng an toàn, không cắt ngang yêu cầu đang xử lý.
- [x] Có cấu hình Railway và kiểm tra tình trạng tại `/health`.

### Kết quả chạy bài kiểm tra

Đã chạy đầy đủ [`check_production_ready.py`](06-lab-complete/check_production_ready.py) từ WSL với Docker Desktop:

- **PASS 12/12 tiêu chí, 41/41 lượt kiểm tra.**
- Ảnh Docker tạo thành công, kích thước **56 MB** (giới hạn: 500 MB).
- `/health` trả 200; `/ready` trả 200 khi Redis hoạt động và 503 khi Redis mất kết nối.
- Thiếu hoặc sai khóa API trả 401; khóa đúng trả 200.
- Với giới hạn 5 lượt/phút, lượt vượt mức trả 429; bộ đếm vẫn còn sau khi khởi động lại ứng dụng.
- Khi ngân sách gần bằng 0, yêu cầu trả 402.
- Nhật ký đều là JSON hợp lệ. Yêu cầu đang chạy vẫn trả 200 khi nhận SIGTERM; tiến trình thoát mã 0. Lệnh `docker stop` hoàn tất trong dưới một giây.

### Chạy lại để đạt đủ 12/12

Trên PowerShell của Windows, bộ chấm không thể gửi SIGTERM nên mục dừng an toàn bị bỏ qua; thường sẽ hiện **11/12**, dù đó không phải lỗi ứng dụng. Để kiểm tra đủ 12 tiêu chí:

1. Trong Docker Desktop, bật **Settings → Resources → WSL Integration → Ubuntu**, chọn **Apply & Restart**. Mở Ubuntu/WSL và chạy `docker version`; cần thấy cả thông tin Client và Server.
2. Tạo môi trường Python riêng trong Ubuntu/WSL, rồi chạy bộ chấm:

```bash
cd /mnt/d/AI20K/Lab14/K5-L3B-DAY14-HoangNgocHieu-2A202603976-Deployment-Benchmark-Observability/06-lab-complete
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn redis
python check_production_ready.py
```

Không cài các gói này vào môi trường Python dùng chung `(base)`: các phiên bản có thể xung đột với những gói khác trên máy. Docker image vẫn được dựng bằng các phiên bản đã ghim trong `requirements.txt`.
