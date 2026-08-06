# Stock Intelligence — Backend API

FastAPI + SQLAlchemy + Alembic, dữ liệu lưu trên Supabase Postgres. Xem
README ở thư mục gốc dự án để biết hướng dẫn tạo Supabase project và
kiến trúc tổng thể — file này chỉ nói về cách chạy/phát triển `apps/api`.

## Cài đặt & chạy

```bash
cd apps/api
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # rồi điền DATABASE_URL/DIRECT_URL/SUPABASE_URL...

alembic upgrade head   # tạo schema
uvicorn app.main:app --reload --port 8000
```

Swagger docs: http://localhost:8000/docs

## Cấu trúc

```
app/
├── main.py            FastAPI app, CORS, lifespan (bật scheduler nếu RUN_SCHEDULER=true)
├── config.py           Settings đọc từ .env (pydantic-settings)
├── db.py                SQLAlchemy engine/session (NullPool — xem README gốc phần Supabase)
├── models/               SQLAlchemy ORM models — 1 nguồn sự thật cho schema, Alembic autogenerate từ đây
├── schemas/               Pydantic request/response schemas
├── routers/                 stocks, history, sync, analysis, predictions, watchlist, health, internal
├── collectors/               MarketDataProvider interface + adapter vnstock DUY NHẤT nơi import vnstock
├── processing/                normalize (làm sạch OHLCV) + indicators (MA/EMA/RSI/MACD/Bollinger)
├── analysis/                   PHASE 2 — scaffold Analysis Engine (trend/liquidity/volatility scoring), chưa có logic
├── scheduler.py                  APScheduler: sync lịch sử hằng ngày + poll realtime theo interval
└── core/auth.py                   Xác thực JWT Supabase + wiring RLS (SET LOCAL app.current_user_id)
alembic/versions/                    Migrations — bao gồm cả role app_backend, RLS policies (raw SQL, không tự động diff)
```

## Luồng sử dụng

1. **Đồng bộ dữ liệu cho một mã** (lần đầu hoặc muốn cập nhật):
   ```
   POST /api/stocks/FPT/sync?years=5
   ```
2. **Lấy lịch sử giá + chỉ báo**: `GET /api/stocks/FPT/history`
3. **Lấy phân tích kỹ thuật mới nhất**: `GET /api/stocks/FPT/analysis`
4. **Danh sách/tìm mã đã có trong hệ thống**: `GET /api/stocks?q=FP`
5. **Watchlist** (cần header `Authorization: Bearer <supabase access token>`):
   `GET/POST /api/watchlist`, `POST /api/watchlist/items`, `DELETE /api/watchlist/items/{stock_id}`
6. `GET /api/stocks/{symbol}/score` và `/prediction` trả placeholder tĩnh
   — Analysis Engine và AI Module chưa triển khai (xem `app/analysis/` và
   `services/ai/`).
7. `GET /internal/scheduler/status` — theo dõi lần sync/poll thành công
   gần nhất, gắn uptime monitor bên ngoài vào đây để phát hiện scheduler
   "chết âm thầm".

## Vì sao có `app_backend` role riêng (migration `0002`)

Postgres KHÔNG áp dụng Row Level Security cho superuser hay chủ sở hữu
bảng, bất kể policy có bật hay không. `postgres` (role Supabase cấp mặc
định) sở hữu các bảng do Alembic tạo — nếu app dùng role đó để kết nối,
policy RLS trên `watchlists`/`watchlist_items` sẽ trông như đang chạy
đúng nhưng thực ra vô tác dụng. `DATABASE_URL` **phải** dùng role
`app_backend` (tạo ở migration `319166c41e7d`), không phải `postgres`.
Sau khi chạy `alembic upgrade head`, đặt password cho role này qua
Supabase SQL editor:

```sql
ALTER ROLE app_backend WITH PASSWORD '<mật khẩu mạnh>';
```

rồi dùng role đó trong `DATABASE_URL` (không phải `DIRECT_URL` — migration
vẫn chạy bằng `postgres`/owner để có đủ quyền tạo bảng/role).

Đã tự kiểm chứng cục bộ: dùng role `postgres` để test RLS cho kết quả
"đang hoạt động" giả — chỉ khi chuyển sang role không sở hữu bảng thì
policy mới thực sự chặn được truy vấn không có `WHERE user_id = ...`.

## Testing

```bash
pytest tests/           # unit tests
pytest tests/ -m integration   # có gọi vnstock thật, cần mạng, không chạy trong CI mặc định
```
