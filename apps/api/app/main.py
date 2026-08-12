"""
Stock Intelligence Platform — Backend API
Chạy: uvicorn app.main:app --reload --port 8000
Docs tự động: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    analysis,
    fundamentals,
    health,
    history,
    internal,
    portfolio,
    predictions,
    stocks,
    sync,
    watchlist,
)
from app.scheduler import shutdown_scheduler, start_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Chỉ bật scheduler ở đúng 1 instance (service `worker`) — xem README
    # phần Deploy. Service `api` (có thể scale nhiều instance) không bật
    # cờ này, chỉ phục vụ request.
    if settings.run_scheduler:
        start_scheduler()
    yield
    if settings.run_scheduler:
        shutdown_scheduler()


app = FastAPI(
    title="Stock Intelligence API",
    description="API phục vụ nền tảng phân tích & dự đoán chứng khoán HOSE",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_allow_origin_regex or None,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(stocks.router)
app.include_router(history.router)
app.include_router(sync.router)
app.include_router(analysis.router)
app.include_router(fundamentals.router)
app.include_router(predictions.router)
app.include_router(watchlist.router)
app.include_router(portfolio.router)
app.include_router(internal.router)
