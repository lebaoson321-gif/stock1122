-- CHỈ dùng cho Postgres local chạy qua Docker Compose (dev không cần
-- Supabase). Trên Supabase thật, schema `auth` + bảng `auth.users` đã
-- có sẵn do GoTrue (Supabase Auth) quản lý — KHÔNG chạy file này ở đó.
--
-- Alembic migration 0001 tạo FK watchlists.user_id -> auth.users.id,
-- nên Postgres local cần bảng này tồn tại trước khi `alembic upgrade
-- head` chạy. Đây là "shim" tối thiểu, không phải bản sao schema thật
-- của Supabase Auth.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid()
);
