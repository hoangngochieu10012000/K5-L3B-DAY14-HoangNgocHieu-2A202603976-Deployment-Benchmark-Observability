# Báo cáo kiểm thử hiệu năng và giám sát — Ngày 14

> Kết quả CP7 được đo trực tiếp và lưu trong `06-lab-complete/benchmark-observability/develop/reports/`.
> Phần chạy production bên dưới để dành cho CP8; chưa điền số liệu khi chưa đo.

**Họ tên:** Hoang Ngoc Hieu
**Ngày chạy:** 2026-11-26
**Môi trường:** Windows 11 Home, Python 3.13.17, Intel Core i7-14650HX (16 lõi / 24 luồng), RAM 15.7 GB; một tiến trình Uvicorn cho mỗi phiên bản. `MOCK_ERROR_RATE=0` để đo độ trễ mà không bị nhiễu bởi lỗi giả lập.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Ngưỡng mặc định của `load_test.py`, đại diện cho độ trễ mà phần lớn người dùng gặp. |
| Error rate `/ask` | ≤ 2% | Ngưỡng mặc định của `load_test.py`; lỗi cần đủ thấp để dịch vụ đáng tin cậy. |
| Accuracy trên golden dataset | ≥ 85% | Ngưỡng quality gate của bài CI; bản sửa KB cuối đạt 100%. |

---

### 1.1 Metrics (Exercise 7.1)

`GET /metrics` có Counter `http_requests_total`, Gauge `agent_in_flight_requests` và Histogram `http_request_duration_seconds`. Đã thêm Histogram `agent_question_length_chars` với các bucket 20, 50, 100, 200, 500, 1000 và 2000 ký tự; kiểm tra endpoint ghi nhận câu hỏi sau khi gọi `/ask`.

Middleware dùng đường dẫn mẫu của route, ví dụ `/ask`, thay vì URL thực. Nhờ vậy, các URL ngẫu nhiên hoặc có mã định danh không tạo vô số chuỗi thời gian trong Prometheus. Độ dài câu hỏi cũng được đo bằng Histogram, không đưa từng độ dài thành label.

## 2. Kiểm thử hiệu năng (develop, `load_test.py`)

### 2.1 Số request đồng thời và độ trễ (agent v2)

| Request đồng thời | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Tỷ lệ lỗi | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.24 | 207.1 | 244.3 | 1703.9 | 0.00% | Đạt |
| 10 | 35.13 | 202.1 | 239.5 | 1700.4 | 0.00% | Đạt |
| 50 | 98.26 | 227.6 | 329.9 | 1741.0 | 0.00% | Đạt |
| 100 | 118.98 | 325.4 | 470.7 | 1782.3 | 0.00% | Đạt |

**Nhận xét:** RPS tăng khi concurrency tăng nhưng không tuyến tính: từ 50 lên 100 chỉ tăng khoảng 21%. Ở mức 100, p95 lên 470.7 ms, gần ngưỡng 500 ms. Tài nguyên máy và chi phí lập lịch/kết nối của một tiến trình đơn không tăng theo số request song song.

Trong các lượt này `MOCK_ERROR_RATE=0`, nên error rate đo được là 0%; đây là phép đo độ trễ, không phải kiểm tra khả năng chịu lỗi upstream.

### 2.2 Độ trễ đuôi

| `MOCK_SLOW_RATE` | Trung bình (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 205.8 | 234.1 | 243.5 |
| 0.03 (mặc định) | 242.5 | 238.5 | 1706.5 |
| 0.1 | 367.1 | 1712.7 | 1734.5 |

**Nhận xét:** p99 nhạy với một tỷ lệ nhỏ request chậm; ở mức 3%, p99 tăng lên 1706.5 ms trong khi p95 vẫn dưới ngưỡng vì phần request chậm chưa chiếm 5%. Khi tăng tỷ lệ chậm lên 10%, cả p95 và p99 tăng mạnh và SLO p95 không đạt. Không nên dùng average làm SLO vì nó che khuất trải nghiệm của nhóm người dùng gặp request chậm.

---

## 3. Đánh giá chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa kho tri thức) |
|---|---|---|---|
| Độ chính xác | 4.35% (1/23) | 91.30% (21/23) | 100% (23/23) |
| Token trung bình / câu | 57.2 | 109.0 | 112.9 |
| Tổng chi phí (USD) | 0.000405 | 0.000760 | 0.000784 |
| Chi phí / câu đúng (USD) | 0.00040515 | 0.00003619 | 0.00003407 |
| Cổng chất lượng | Không đạt | Đạt | Đạt |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| `security-02` | `token`, `hết hạn`, `chữ ký` | Thêm tài liệu KB giải thích JWT là token có chữ ký số và có thời điểm hết hạn. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Thêm tài liệu KB về Kubernetes HPA và các chỉ số dùng để scale pod. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:** v2 dùng nhiều token hơn và tổng chi phí cao hơn, nhưng accuracy tăng từ 4.35% lên 91.30%; sau khi sửa KB đạt 100%. Chi phí cho mỗi câu đúng giảm từ 0.00040515 USD ở v1 xuống 0.00003407 USD ở v2 sau sửa. Độ trễ có yếu tố ngẫu nhiên do mô phỏng request chậm, nên không kết luận v2 luôn nhanh hơn chỉ từ một lượt eval.

**Cổng chất lượng trong CI:** chạy `python eval/run_eval.py --url http://localhost:8002 --min-accuracy 0.85`. Script trả mã thoát 1 nếu accuracy thấp hơn 85%. Nếu thêm `--baseline <tệp-kết-quả-cũ.json>`, script cũng trả mã 1 khi có câu bị regression. CI coi mã khác 0 là bước thất bại và chặn gộp thay đổi. Checkpoint chấp nhận phần giải thích này; không thêm workflow mới.

---

## 4. Hệ thống giám sát (production)

> Phần CP8; chưa chạy trong CP7 nên chưa có ảnh hoặc số liệu production.

### 4.1 Ảnh chụp màn hình

- [ ] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals)
- [ ] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian)
- [ ] Một trace lỗi trong Jaeger (có event `exception`)
- [ ] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing**

### 4.2 Thử nghiệm gây lỗi

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | | | |
| B | `MOCK_SLOW_RATE=0.3` | | | |
| C | `LLM_MODEL=mock-llm-large` | | | |
| D | `docker pause` 1 instance | | | |
| E | `AGENT_VERSION=v1` | | | |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

...

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: ...
- Tổng thời gian: ... ms
- Span chiếm nhiều thời gian nhất: ... (... ms, ...%)
- Dòng log tương ứng (grep theo `trace_id`):

```json

```

---

## 5. Kiểm thử mở rộng quy mô (production, Locust chạy nền, 100 người dùng, 2 phút)

> Phần CP8; chưa chạy Locust hoặc Docker stack trong CP7.

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Lỗi |
|---|---|---|---|---|---|
| 1 | | | | | |
| 3 | | | | | |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

...

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. Tăng concurrency giúp tăng RPS nhưng không bảo đảm tăng tuyến tính; cần theo dõi p95 khi tải cao.
  2. p95/p99 cho thấy tail latency mà average có thể che khuất.
  3. Golden dataset và quality gate giúp phát hiện câu trả lời thiếu kiến thức; sửa KB đã nâng kết quả lên 23/23.
- Nếu đưa agent này lên production thật, cần bổ sung cảnh báo cho p95, tỷ lệ lỗi, tình trạng Redis và ngân sách LLM; CP8 sẽ kiểm tra qua Prometheus, Grafana và Jaeger.

