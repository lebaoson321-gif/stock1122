from datetime import date as date_type

from pydantic import BaseModel


class IndexBarOut(BaseModel):
    date: date_type
    open: float
    high: float
    low: float
    close: float
    volume: int


class IndexQuote(BaseModel):
    code: str
    name: str
    date: date_type
    close: float
    change_point: float
    change_pct: float


class IndexSyncItem(BaseModel):
    code: str
    rows_synced: int
    message: str


class IndexSyncResult(BaseModel):
    results: list[IndexSyncItem]
