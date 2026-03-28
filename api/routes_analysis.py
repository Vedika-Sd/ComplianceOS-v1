"""
api/routes_analysis.py
Analysis, dashboard, and simulation endpoints.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from database.db_manager import (
    get_business, get_obligations, get_action_items,
    get_sessions, get_risk_history, get_db_stats,
    run_threshold_engine, compute_risk_score
)
from agents.orchestrator import run_full_analysis, run_simulation_only

router = APIRouter()


class AnalysisRequest(BaseModel):
    run_scenario: bool = False
    scenario_turnover: Optional[float] = None
    scenario_flags: Optional[dict] = None


class SimulationRequest(BaseModel):
    scenario_turnover: float
    extra_flags: Optional[dict] = None
    label: Optional[str] = ""


@router.post("/{business_id}")
async def run_analysis(business_id: str, req: AnalysisRequest):
    """
    Run full 4-agent compliance analysis pipeline.
    Returns complete compliance report.
    """
    biz = get_business(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")

    try:
        result = run_full_analysis(
            business_id=business_id,
            run_scenario=req.run_scenario,
            scenario_turnover=req.scenario_turnover,
            scenario_flags=req.scenario_flags,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/dashboard/{business_id}")
async def get_dashboard(business_id: str):
    """
    Return all data needed for the dashboard UI.
    Does NOT re-run analysis — reads from DB.
    """
    biz = get_business(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")

    obligations = get_obligations(business_id)
    action_items = get_action_items(business_id)
    sessions = get_sessions(business_id, limit=5)
    risk_history = get_risk_history(business_id, limit=10)

    # Quick risk score from current obligations
    risk = compute_risk_score(obligations)

    # Split obligations
    applicable = [o for o in obligations if not o.get("is_benefit")]
    high = [o for o in applicable if o.get("priority") == "HIGH"]
    upcoming = [a for a in action_items if a.get("urgency") in ("IMMEDIATE", "THIS_WEEK", "THIS_MONTH")]

    return {
        "business": biz,
        "risk_score": risk,
        "obligations": {
            "total": len(applicable),
            "high": len(high),
            "medium": len([o for o in applicable if o.get("priority") == "MEDIUM"]),
            "low": len([o for o in applicable if o.get("priority") == "LOW"]),
            "items": applicable[:20],
        },
        "action_items": {
            "total": len(action_items),
            "upcoming": upcoming[:5],
            "pending": len([a for a in action_items if a.get("status") == "PENDING"]),
        },
        "sessions": sessions,
        "risk_history": risk_history,
    }


@router.post("/simulate/{business_id}")
async def simulate(business_id: str, req: SimulationRequest):
    """Run scenario simulation without full pipeline."""
    biz = get_business(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")

    try:
        result = run_simulation_only(
            business_id=business_id,
            scenario_turnover=req.scenario_turnover,
            extra_flags=req.extra_flags,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.get("/quick/{business_id}")
async def quick_analysis(business_id: str):
    """
    Fast deterministic-only analysis (no LLM, no RAG).
    Returns obligations and risk score instantly.
    """
    biz = get_business(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")

    obligations = run_threshold_engine(biz)
    risk = compute_risk_score(obligations)

    return {
        "business_id": business_id,
        "business_name": biz["business_name"],
        "obligations": obligations,
        "risk_score": risk,
        "analysis_type": "quick_deterministic",
    }


@router.get("/obligations/{business_id}")
async def get_business_obligations(business_id: str, status: str = None):
    """Get all obligations for a business."""
    biz = get_business(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    return get_obligations(business_id, status)


@router.get("/actions/{business_id}")
async def get_business_actions(business_id: str):
    """Get all action items for a business."""
    return get_action_items(business_id)


@router.get("/history/{business_id}")
async def get_analysis_history(business_id: str):
    """Get past analysis sessions."""
    return get_sessions(business_id, limit=10)