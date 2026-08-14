"""
Kết nối Postgres riêng cho services/ai — đọc trực tiếp bảng
price_history/technical_indicators/stocks, KHÔNG dùng chung ORM model
với apps/api (services/ai là service độc lập, chỉ cần đọc dữ liệu bằng
SQL thuần qua pandas, không cần SQLAlchemy ORM đầy đủ).

psycopg (v3) tự prepare statement phía server sau vài lần chạy cùng câu
lệnh trên một connection (mặc định prepare_threshold=5). Nếu DATABASE_URL
trỏ vào transaction pooler của Supabase (cổng 6543), connection vật lý
phía server đổi giữa các transaction nên tên statement tự sinh có thể
đụng nhau -> lỗi DuplicatePreparedStatement. Đây là đúng lỗi apps/api đã
gặp và đã sửa trong app/db.py.

.env.example khuyến nghị cổng 5432 (direct/session pooler) — ở đó
prepared statement vốn an toàn — nhưng tắt hẳn vẫn là lựa chọn đúng: file
.env thật nằm trên máy người dùng, không kiểm soát được, và với script
chạy vài chục truy vấn rời rạc thì prepared statement gần như không giúp
gì về tốc độ. Tức là tắt đi mất không đáng kể, để bật thì rủi ro script
chết giữa chừng.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        load_dotenv()
        database_url = os.environ["DATABASE_URL"]
        _engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args={"prepare_threshold": None},
        )
    return _engine
