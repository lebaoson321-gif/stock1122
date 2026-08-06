# Stock Intelligence — Frontend

Next.js 14 (App Router) + TypeScript + Tailwind CSS. Xem README ở thư
mục gốc dự án cho kiến trúc tổng thể và hướng dẫn tạo Supabase project.

## Cài đặt & chạy

```bash
cd apps/web
npm install
cp .env.example .env.local   # điền NEXT_PUBLIC_API_BASE_URL + Supabase URL/anon key
npm run dev
```

Mở http://localhost:3000. Cần backend (`apps/api`) đang chạy — không
có dữ liệu mô phỏng, mọi trang gọi API thật.

## Cấu trúc

```
app/
├── page.tsx                Tìm mã cổ phiếu
├── stock/[symbol]/page.tsx  Dashboard 1 mã: candlestick chart, RSI/MACD, watchlist button
├── watchlist/page.tsx        Watchlist (cần đăng nhập)
└── login/page.tsx             Đăng nhập/đăng ký (Supabase Auth, email+password)
components/
├── CandlestickChart.tsx        TradingView Lightweight Charts — xem lưu ý bên dưới
├── IndicatorPanel.tsx            RSI + MACD (cùng thư viện chart, pane riêng)
├── SearchBar.tsx, WatchlistButton.tsx
└── ScoreCard.tsx, AIPredictionCard.tsx   Placeholder "sắp ra mắt" — Analysis Engine/AI Module chưa có ở backend
lib/
├── api.ts                       Fetch client tới FastAPI (cùng pattern legacy/frontend/src/api.js)
├── types.ts                      Mirror của backend Pydantic schemas
└── supabase/{client,server}.ts    Supabase Auth (SSR helpers)
middleware.ts                      Refresh session Supabase trên mỗi request
```

## Lưu ý về `lightweight-charts`

- Version pin cứng ở `package.json` (hiện `4.2.3`) — v5 đổi hẳn cách
  tạo series (`chart.addCandlestickSeries()` → `chart.addSeries(...)`),
  nâng cấp version phải sửa lại `CandlestickChart.tsx`/`IndicatorPanel.tsx`.
- Chart dùng `autoSize: false` + tự resize bằng `ResizeObserver` — bật
  cả hai cùng lúc sẽ tự xung đột (lightweight-charts cảnh báo ra console).
- Effect tạo chart chỉ chạy 1 lần (`useEffect(..., [])`), có cleanup gọi
  `chart.remove()` để không rò rỉ canvas khi React 18 Strict Mode
  double-invoke effect lúc dev.

## Watchlist / Auth

`WatchlistButton`/trang `/watchlist` gọi `supabase.auth.getSession()`
lấy access token, gửi kèm header `Authorization: Bearer <token>` khi
gọi các endpoint `/api/watchlist/*` — backend verify token đó (xem
`apps/api/app/core/auth.py`). Cần Supabase project thật để test đăng
nhập; chưa có project thì trang `/login` vẫn render nhưng đăng nhập sẽ
lỗi (đúng như dự kiến).
