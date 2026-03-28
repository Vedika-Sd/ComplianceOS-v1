"""api/routes_alerts.py — Alert management endpoints."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, HTTPException
from database.db_manager import get_alerts, mark_alert_read, get_conn

router = APIRouter()


@router.get("/{business_id}")
async def get_business_alerts(business_id: str, unread_only: bool = False):
    return get_alerts(business_id, unread_only=unread_only, limit=30)


@router.patch("/{alert_id}/read")
async def mark_read(alert_id: str):
    mark_alert_read(alert_id)
    return {"message": "Alert marked as read"}


@router.patch("/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str):
    with get_conn() as conn:
        conn.execute("UPDATE alerts SET is_dismissed=1 WHERE id=?", (alert_id,))
    return {"message": "Alert dismissed"}


@router.get("/{business_id}/count")
async def unread_count(business_id: str):
    alerts = get_alerts(business_id, unread_only=True)
    return {"unread_count": len(alerts)}