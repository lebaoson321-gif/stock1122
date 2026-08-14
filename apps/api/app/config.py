"""
Cấu hình ứng dụng, đọc từ biến môi trường (.env khi chạy local).
Xem .env.example để biết đầy đủ danh sách biến và ý nghĩa từng biến
(đặc biệt là DATABASE_URL vs DIRECT_URL — xem README phần Supabase).
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database -----------------------------------------------------
    # DATABASE_URL: connection pooled qua Supavisor/PgBouncer (port 6543,
    # transaction mode) — dùng cho mọi truy vấn runtime của app.
    # DIRECT_URL: connection trực tiếp hoặc qua Session Pooler (port 5432)
    # — chỉ dùng cho Alembic migrations, không dùng cho runtime.
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/stock_intelligence"
    direct_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/stock_intelligence"

    # --- Supabase Auth ---------------------------------------------------
    supabase_url: str = ""
    supabase_jwt_secret: str = ""  # fallback HS256 nếu project không dùng JWKS

    # --- CORS ------------------------------------------------------------
    cors_allow_origins: List[str] = ["http://localhost:3000"]
    # Regex cho Vercel preview deployments, ví dụ: https://stock-web-.*\.vercel\.app
    cors_allow_origin_regex: str = ""

    # --- Data collection ---------------------------------------------------
    market_data_provider: str = "vnstock"
    # Nguồn RIÊNG cho chỉ số tài chính doanh nghiệp (P/E, EPS, ROE, ROA...).
    # Tách khỏi market_data_provider vì giá vẫn nên đi qua vnstock trong
    # khi chỉ số tài chính đổi sang fireant (VCI tính sai P/E/EPS ~1,9
    # lần — cơ sở lợi nhuận chỉ bằng nửa TTM thật, xem fireant_adapter.py).
    fundamentals_provider: str = "vnstock"  # "vnstock" hoặc "fireant"
    # Bearer token của tài khoản fireant.vn đã đăng nhập — lấy qua F12 >
    # Network > header Authorization của request tới restv2.fireant.vn.
    # Rỗng hoặc fundamentals_provider != "fireant" thì lùi về vnstock.
    fireant_token: str = ""
    historical_sync_cron: str = "0 18 * * 1-5"  # 18:00 giờ VN, T2-T6 (sau giờ đóng cửa HOSE)
    realtime_poll_interval_seconds: int = 60
    realtime_quote_retention_days: int = 30

    # --- Scheduler ---------------------------------------------------------
    # Chỉ bật scheduler ở đúng 1 instance (worker service) — xem README
    # phần "Deploy" để biết vì sao không nên bật ở service api có thể
    # scale nhiều instance.
    run_scheduler: bool = False

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_allow_origins if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
