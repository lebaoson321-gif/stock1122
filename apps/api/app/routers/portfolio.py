"""
Danh mục đầu tư ảo. Mọi endpoint đều cần đăng nhập (Supabase Auth) —
danh mục gắn với user_id, và RLS trên 3 bảng portfolio* là lớp phòng hờ
(xem migration 03288f241f54).
"""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_authed_db, get_current_user_id
from app.models.portfolio import Portfolio, PortfolioPosition, PortfolioTransaction
from app.models.stock import Stock
from app.schemas.portfolio import (
    OrderCreate,
    OrderResult,
    PortfolioCreate,
    PortfolioMissing,
    PortfolioOut,
    PositionOut,
    TransactionOut,
)
from app.services.pricing import get_current_price
from app.services.trading import PRICE_UNIT_VND, TradeError, execute_order, reset_portfolio

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _load_portfolio(db: Session, user_id: uuid.UUID) -> Portfolio | None:
    return db.execute(select(Portfolio).where(Portfolio.user_id == user_id)).scalar_one_or_none()


def _require_portfolio(db: Session, user_id: uuid.UUID) -> Portfolio:
    portfolio = _load_portfolio(db, user_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chưa có danh mục. Gọi POST /api/portfolio để tạo trước.",
        )
    return portfolio


def _serialize(db: Session, portfolio: Portfolio) -> PortfolioOut:
    rows = db.execute(
        select(PortfolioPosition, Stock)
        .join(Stock, Stock.id == PortfolioPosition.stock_id)
        .where(PortfolioPosition.portfolio_id == portfolio.id)
        .order_by(Stock.symbol)
    ).all()

    positions: list[PositionOut] = []
    holdings_value = Decimal(0)
    for position, stock in rows:
        current = get_current_price(db, stock.id)
        cost_value = Decimal(position.quantity) * position.avg_cost * PRICE_UNIT_VND

        market_value = pnl = None
        pnl_pct = None
        if current is not None:
            market_value = Decimal(position.quantity) * current.price * PRICE_UNIT_VND
            pnl = market_value - cost_value
            pnl_pct = float(pnl / cost_value * 100) if cost_value else None
            holdings_value += market_value
        else:
            # Không có giá thì tính theo giá vốn — tổng tài sản không bị
            # tụt giả tạo chỉ vì 1 mã thiếu dữ liệu.
            holdings_value += cost_value

        positions.append(
            PositionOut(
                stock_id=stock.id,
                symbol=stock.symbol,
                company_name=stock.company_name,
                quantity=position.quantity,
                avg_cost=position.avg_cost,
                current_price=current.price if current else None,
                price_source=current.source if current else None,
                market_value=market_value,
                cost_value=cost_value,
                pnl=pnl,
                pnl_pct=pnl_pct,
            )
        )

    total_value = portfolio.cash_balance + holdings_value
    total_pnl = total_value - portfolio.initial_capital
    return PortfolioOut(
        id=portfolio.id,
        initial_capital=portfolio.initial_capital,
        cash_balance=portfolio.cash_balance,
        positions=positions,
        holdings_value=holdings_value,
        total_value=total_value,
        total_pnl=total_pnl,
        total_pnl_pct=float(total_pnl / portfolio.initial_capital * 100)
        if portfolio.initial_capital
        else 0.0,
    )


def _get_stock_or_404(db: Session, symbol: str) -> Stock:
    stock = db.execute(select(Stock).where(Stock.symbol == symbol.upper())).scalar_one_or_none()
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chưa có dữ liệu cho mã {symbol.upper()}. Đồng bộ mã này trước.",
        )
    return stock


@router.get("", response_model=PortfolioOut | PortfolioMissing)
def get_portfolio(
    user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_authed_db)
):
    portfolio = _load_portfolio(db, user_id)
    if portfolio is None:
        return PortfolioMissing()
    return _serialize(db, portfolio)


@router.post("", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    body: PortfolioCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_authed_db),
):
    if _load_portfolio(db, user_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Đã có danh mục. Dùng POST /api/portfolio/reset để làm lại từ đầu.",
        )
    portfolio = Portfolio(
        user_id=user_id, initial_capital=body.initial_capital, cash_balance=body.initial_capital
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return _serialize(db, portfolio)


@router.post("/reset", response_model=PortfolioOut)
def reset(
    body: PortfolioCreate | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_authed_db),
):
    """Xoá sạch vị thế + lịch sử, đưa tiền về vốn ban đầu. Truyền
    `initial_capital` nếu muốn đổi luôn mức vốn."""
    portfolio = _require_portfolio(db, user_id)
    reset_portfolio(db, portfolio, body.initial_capital if body else None)
    return _serialize(db, portfolio)


@router.post("/orders", response_model=OrderResult, status_code=status.HTTP_201_CREATED)
def place_order(
    body: OrderCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_authed_db),
):
    portfolio = _require_portfolio(db, user_id)
    stock = _get_stock_or_404(db, body.symbol)
    try:
        transaction = execute_order(db, portfolio, stock, body.side, body.quantity)
    except TradeError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    return OrderResult(
        transaction=TransactionOut(
            id=transaction.id,
            symbol=stock.symbol,
            side=transaction.side,
            quantity=transaction.quantity,
            price=transaction.price,
            amount=transaction.amount,
            price_source=transaction.price_source,
            executed_at=transaction.executed_at,
        ),
        portfolio=_serialize(db, portfolio),
    )


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    limit: int = Query(50, ge=1, le=500),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_authed_db),
):
    portfolio = _require_portfolio(db, user_id)
    rows = db.execute(
        select(PortfolioTransaction, Stock)
        .join(Stock, Stock.id == PortfolioTransaction.stock_id)
        .where(PortfolioTransaction.portfolio_id == portfolio.id)
        .order_by(PortfolioTransaction.executed_at.desc(), PortfolioTransaction.id.desc())
        .limit(limit)
    ).all()
    return [
        TransactionOut(
            id=t.id,
            symbol=s.symbol,
            side=t.side,
            quantity=t.quantity,
            price=t.price,
            amount=t.amount,
            price_source=t.price_source,
            executed_at=t.executed_at,
        )
        for t, s in rows
    ]
