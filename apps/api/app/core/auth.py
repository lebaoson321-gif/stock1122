"""
Xác thực JWT của Supabase Auth + wiring RLS.

Supabase project mới ký JWT bất đối xứng (khám phá key qua JWKS endpoint);
project cũ hơn có thể vẫn dùng HS256 với 1 secret tĩnh. Ưu tiên JWKS
(PyJWKClient), fallback sang SUPABASE_JWT_SECRET (HS256) nếu JWKS không
khả dụng hoặc không cấu hình — xem README phần Supabase để biết cách
kiểm tra project của bạn đang dùng kiểu nào.

RLS thật sự có tác dụng: FastAPI dùng chung 1 role SQLAlchemy để query
(không qua PostgREST), nên `auth.uid()` trong policy sẽ luôn NULL nếu
không có bước này. `get_authed_db()` verify JWT rồi chạy
`SET LOCAL app.current_user_id = '<uid>'` đầu transaction — khớp với
điều kiện trong policy RLS ở migration 0001 (xem alembic/versions/).
Đây là lớp bảo vệ thứ 2; lớp chính vẫn là kiểm tra ownership trong code
router (routers/watchlist.py).
"""
import uuid
from collections.abc import Generator

import jwt
from fastapi import Depends, HTTPException, Request, status
from jwt import PyJWKClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db

settings = get_settings()

_jwk_client: PyJWKClient | None = None
if settings.supabase_url:
    _jwk_client = PyJWKClient(f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")


def _decode_token(token: str) -> dict:
    last_error: Exception | None = None

    if _jwk_client is not None:
        try:
            signing_key = _jwk_client.get_signing_key_from_jwt(token)
            return jwt.decode(token, signing_key.key, algorithms=["ES256", "RS256"], audience="authenticated")
        except Exception as e:  # noqa: BLE001 — thử fallback bên dưới trước khi báo lỗi
            last_error = e

    if settings.supabase_jwt_secret:
        try:
            return jwt.decode(
                token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated"
            )
        except Exception as e:  # noqa: BLE001
            last_error = e

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Không xác thực được token: {last_error}" if last_error else "Chưa cấu hình xác thực Supabase Auth",
    )


def get_current_user_id(request: Request) -> uuid.UUID:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Thiếu Authorization: Bearer <token>")
    token = auth_header.split(" ", 1)[1]
    payload = _decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không có claim 'sub'")
    return uuid.UUID(sub)


def get_authed_db(
    user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)
) -> Generator[Session, None, None]:
    """Dependency cho các route cần đăng nhập: vừa xác thực JWT, vừa wiring
    session variable cho RLS. Trả về (qua contextvar-like pattern) session
    đã sẵn sàng; user_id lấy lại qua get_current_user_id nếu route cần."""
    # SET LOCAL không nhận bind parameter (chỉ nhận literal) — dùng
    # set_config(), tương đương SET LOCAL khi is_local=true, nhưng là một
    # lời gọi hàm bình thường nên bind parameter hoạt động đúng.
    db.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(user_id)})
    yield db
