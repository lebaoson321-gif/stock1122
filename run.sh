#!/usr/bin/env bash
# Chạy đồng thời Backend (FastAPI/uvicorn) và Frontend (React/Vite).
# Dùng: ./run.sh   (Ctrl+C để dừng cả hai)
set -e
cd "$(dirname "$0")"

if [ ! -d backend/venv ]; then
  echo "==> Tạo virtualenv cho backend..."
  python3 -m venv backend/venv
fi
echo "==> Cài (hoặc kiểm tra) dependency backend..."
backend/venv/bin/pip install -q -r backend/requirements.txt

if [ ! -d frontend/node_modules ]; then
  echo "==> Cài dependency frontend (npm install)..."
  (cd frontend && npm install)
fi

cleanup() {
  echo
  echo "==> Đang dừng backend..."
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Khởi động backend tại http://localhost:8000 (docs: /docs)"
(cd backend && ../backend/venv/bin/uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

sleep 1
echo "==> Khởi động frontend tại http://localhost:5173"
(cd frontend && npm run dev)
