from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import Watchlist, User, get_db
from app.services.auth_service import get_current_user
from app.services.smart_alerts import get_smart_alerts_system

router = APIRouter(prefix="/api/watchlist")


class WatchlistItemRequest(BaseModel):
    ticker: str = Field(min_length=1)
    type: str = Field(default="stock")
    notes: Optional[str] = None


def _serialize_items(items: List[Watchlist]) -> List[dict]:
    return [
        {
            "ticker": item.ticker,
            "type": item.asset_type,
            "notes": item.notes,
            "added_at": item.added_at.isoformat() if item.added_at else None,
        }
        for item in items
    ]


@router.get("")
def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == current_user.id)
        .order_by(Watchlist.added_at.desc())
        .all()
    )
    return {"success": True, "data": {"items": _serialize_items(items)}}


@router.post("")
def add_watchlist_item(
    request: WatchlistItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticker = request.ticker.upper().strip()
    asset_type = request.type.lower().strip() or "stock"

    existing = (
        db.query(Watchlist)
        .filter(
            Watchlist.user_id == current_user.id,
            Watchlist.ticker == ticker,
            Watchlist.asset_type == asset_type,
        )
        .first()
    )
    if existing:
        return {"success": True, "data": _serialize_items([existing])[0]}

    item = Watchlist(
        user_id=current_user.id,
        ticker=ticker,
        asset_type=asset_type,
        notes=request.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {"success": True, "data": _serialize_items([item])[0]}


@router.delete("/{ticker}")
def remove_watchlist_item(
    ticker: str,
    type_: str = Query("stock", alias="type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticker = ticker.upper().strip()
    asset_type = type_.lower().strip() or "stock"

    item = (
        db.query(Watchlist)
        .filter(
            Watchlist.user_id == current_user.id,
            Watchlist.ticker == ticker,
            Watchlist.asset_type == asset_type,
        )
        .first()
    )
    if item:
        db.delete(item)
        db.commit()

    return {"success": True, "data": {"removed": bool(item), "ticker": ticker, "type": asset_type}}


@router.get("/alerts")
def get_watchlist_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    tickers = [item.ticker for item in items]
    alerts_system = get_smart_alerts_system()
    alerts = alerts_system.check_alerts(tickers) if tickers else []
    return {
        "success": True,
        "data": {
            "total": len(alerts),
            "alerts": alerts,
        },
    }


@router.get("/summary")
def get_watchlist_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    tickers = [item.ticker for item in items]
    alerts_system = get_smart_alerts_system()
    summary = alerts_system.get_watchlist_alerts(tickers) if tickers else {
        "total_alerts": 0,
        "by_type": {},
        "by_severity": {},
        "recent_alerts": [],
    }
    return {"success": True, "data": summary}
