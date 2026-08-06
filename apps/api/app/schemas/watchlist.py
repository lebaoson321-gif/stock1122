from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WatchlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stock_id: int
    symbol: str
    company_name: str
    added_at: datetime


class WatchlistOut(BaseModel):
    id: int
    name: str
    items: list[WatchlistItemOut] = []


class WatchlistItemCreate(BaseModel):
    symbol: str
