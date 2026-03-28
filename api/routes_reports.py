"""api/routes_reports.py — Report download and audit trail endpoints."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from database.db_manager import get_audit_trail, get_business, get_sessions

router = APIRouter()


@router.get("/{business_id}/audit")
async def get_audit(business_id: str, limit: int = 50):
    return get_audit_trail(business_id=business_id, limit=limit)


@router.get("/{business_id}/download/{session_id}")
async def download_report(business_id: str, session_id: str):
    sessions = get_sessions(business_id, limit=20)
    session = next((s for s in sessions if s["id"] == session_id), None)

    if not session or not session.get("report_path"):
        raise HTTPException(status_code=404, detail="Report not found. Run analysis first.")

    report_path = Path(session["report_path"])
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file missing on server.")

    return FileResponse(
        path=str(report_path),
        media_type="text/html",
        filename=f"ComplianceOS_Report_{business_id}.html",
    )


@router.get("/{business_id}/sessions")
async def list_sessions(business_id: str):
    return get_sessions(business_id, limit=10)