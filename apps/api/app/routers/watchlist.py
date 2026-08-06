import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_authed_db, get_current_user_id
from app.models.stock import Stock
from app.models.watchlist import Watchlist, WatchlistItem
from app.schemas.watchlist import WatchlistItemCreate, WatchlistItemOut, WatchlistOut

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def _get_or_create_default_watchlist(db: Session, user_id: uuid.UUID) -> Watchlist:
    watchlist = db.execute(
        select(Watchlist).where(Watchlist.user_id == user_id, Watchlist.name == "default")
    ).scalar_one_or_none()
    if watchlist is None:
        watchlist = Watchlist(user_id=user_id, name="default")
        db.add(watchlist)
        db.commit()
        db.refresh(watchlist)
    return watchlist


def _serialize(db: Session, watchlist: Watchlist) -> WatchlistOut:
    rows = db.execute(
        select(WatchlistItem, Stock)
        .join(Stock, Stock.id == WatchlistItem.stock_id)
        .where(WatchlistItem.watchlist_id == watchlist.id)
        .order_by(Stock.symbol)
    ).all()
    items = [
        WatchlistItemOut(
            stock_id=stock.id, symbol=stock.symbol, company_name=stock.company_name, added_at=item.added_at
        )
        for item, stock in rows
    ]
    return WatchlistOut(id=watchlist.id, name=watchlist.name, items=items)


@router.get("", response_model=WatchlistOut)
def get_watchlist(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_authed_db),
):
    watchlist = _get_or_create_default_watchlist(db, user_id)
    return _serialize(db, watchlist)


@router.post("/items", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED)
def add_item(
    body: WatchlistItemCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_authed_db),
):
    symbol = body.symbol.upper()
    stock = db.execute(select(Stock).where(Stock.symbol == symbol)).scalar_one_or_none()
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chưa có dữ liệu cho mã {symbol}. Gọi POST /api/stocks/{symbol}/sync trước.",
        )

    watchlist = _get_or_create_default_watchlist(db, user_id)

    existing = db.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist.id, WatchlistItem.stock_id == stock.id
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(WatchlistItem(watchlist_id=watchlist.id, stock_id=stock.id))
        db.commit()

    return _serialize(db, watchlist)


@router.delete("/items/{stock_id}", response_model=WatchlistOut)
def remove_item(
    stock_id: int,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_authed_db),
):
    watchlist = _get_or_create_default_watchlist(db, user_id)
    item = db.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist.id, WatchlistItem.stock_id == stock_id
        )
    ).scalar_one_or_none()
    if item is not None:
        db.delete(item)
        db.commit()
    return _serialize(db, watchlist)
