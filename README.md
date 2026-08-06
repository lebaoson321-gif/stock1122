# Stock Intelligence & Analysis Platform — Full-stack

Backend FastAPI + Frontend React (Vite), theo đúng kiến trúc trong tài liệu
gốc (mục 9, Giai đoạn 2–3).

```
.
├── backend/            FastAPI — API dữ liệu, chỉ báo kỹ thuật
├── frontend/           React (Vite) — dashboard giao diện
├── run.sh              Chạy đồng thời cả 2 bằng một lệnh (không cần Docker)
└── docker-compose.yml  Chạy đồng thời cả 2 bằng Docker
```

## Chạy nhanh — 1 lệnh (khuyên dùng)

```bash
./run.sh
```

Script này tự tạo virtualenv backend, cài `requirements.txt`, cài
`node_modules` (npm install) nếu chưa có, rồi chạy song song:
- Backend: http://localhost:8000 (Swagger docs tại `/docs`)
- Frontend: http://localhost:5173

Nhấn `Ctrl+C` để dừng cả hai.

## Chạy bằng Docker Compose

```bash
docker compose up --build
```

Chạy cả backend (uvicorn, có `--reload`) và frontend (vite dev server) trong
container, mount code từ máy vào container nên sửa code vẫn tự reload như
chạy trực tiếp. Cùng địa chỉ như trên: backend `:8000`, frontend `:5173`.
`Ctrl+C` để dừng, hoặc `docker compose down`.

Database SQLite của backend (`backend/app/stock_data.db`) được mount từ
`backend/app/` trên máy nên dữ liệu vẫn còn sau khi tắt container.

## Chạy thủ công (2 terminal)

```bash
# Terminal 1 — backend
cd backend
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Frontend chạy sẵn với dữ liệu mô phỏng nên bạn xem được giao diện đầy đủ
ngay cả khi chưa bật backend. Xem `frontend/README.md` để nối dữ liệu thật.

## Trạng thái từng phần (đã kiểm tra lại)

| Phần | Trạng thái |
|---|---|
| Backend — cài dependency, khởi động server, DB SQLite | Đã chạy thử thành công (`/api/health`, `/api/stocks`) |
| Backend — tính chỉ báo kỹ thuật (MA/RSI/MACD) | Đã test kỹ bằng dữ liệu giả lập, logic đúng |
| Backend — fetch dữ liệu HOSE (vnstock) | Đã sửa 1 lỗi (xem bên dưới); fetch giá đã chạy được, cần bạn tự xác nhận trên máy có internet thật |
| Frontend — cài dependency, `npm run dev` / `npm run build` | Đã chạy thử thành công |
| Frontend — giao diện dashboard | Hoàn chỉnh, chạy được ngay với dữ liệu mô phỏng |
| Frontend — nối API thật | Đã chuẩn bị sẵn `api.js`, cần bạn nối tay theo hướng dẫn |
| AI Prediction (Module 5) | Chưa làm — hiện là công thức giả lập, không phải model thật |

### Lỗi đã sửa

`backend/app/data_fetcher.py::fetch_company_info()` gọi `vnstock` với
`source="TCBS"`, nhưng bản `vnstock` mới nhất (4.x, được cài từ
`requirements.txt` ghi `>=3.2.0`) đã bỏ nguồn `TCBS` cho phần thông tin
công ty — chỉ còn hỗ trợ `KBS, VCI, MSN, FMP`, khiến `POST /sync` luôn lỗi
502. Đã đổi sang `source="VCI"` (cùng nguồn đang dùng cho giá) và cập nhật
lại tên cột cho đúng schema mới (`organ_short_name`, `sector`).

Môi trường chạy việc kiểm tra này bị chặn mạng ra ngoài tới các host dữ
liệu chứng khoán (proxy trả 403), nên chưa xác nhận được dữ liệu giá thật
kéo về đúng — bạn cần chạy `POST /api/stocks/FPT/sync` trên máy mình (có
internet bình thường) để xác nhận bước cuối này.

## Việc tiếp theo hợp lý

1. Chạy thử `POST /api/stocks/FPT/sync` trên máy bạn — xác nhận `vnstock`
   hoạt động đúng với môi trường của bạn (thư viện này đôi khi đổi cấu
   trúc dữ liệu trả về).
2. Nối frontend với API thật theo hướng dẫn trong `frontend/README.md`.
3. Khi ổn định 2 phần trên, mới nên bắt đầu Module AI Prediction (Level 1:
   Random Forest/XGBoost trước, chưa cần LSTM).
4. `docker-compose.yml` hiện chạy dev server cho cả 2 phía (có hot-reload);
   khi cần deploy thật, nên tách thêm bản build production cho frontend
   (build tĩnh + nginx) thay vì chạy `vite dev` trong container.
