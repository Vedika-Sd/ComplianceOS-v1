"""
api/routes_business.py
Business profile CRUD endpoints.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from database.db_manager import get_business, get_all_businesses, update_business
import agents.profile_guardian as guardian

router = APIRouter()


class BusinessProfileIn(BaseModel):
    business_name: str
    entity_type: str = "Private Limited"
    industry: str = "IT / Software Services"
    state: str = "Maharashtra"
    year_of_incorporation: Optional[int] = None

    annual_turnover_cr: float = Field(..., ge=0)
    projected_turnover_cr: Optional[float] = None
    digital_revenue_pct: float = Field(0, ge=0, le=100)
    b2b_sales_pct: float = Field(0, ge=0, le=100)
    exports_revenue_cr: float = 0
    investment_plant_cr: float = 0
    loan_portfolio_cr: float = 0
    inter_state_sales_pct: float = 0

    has_gstin: bool = False
    has_nbfc_license: bool = False
    has_pa_license: bool = False
    has_udyam_registration: bool = False
    is_listed: bool = False
    uses_lsp: bool = False
    has_digital_lending_app: bool = False
    has_export_activities: bool = False
    has_gst_notices: bool = False
    files_einvoice: bool = False

    employee_count: int = 0
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    alerts_enabled: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "QuickLend FinTech Pvt Ltd",
                "entity_type": "Private Limited",
                "industry": "Digital Lending / NBFC",
                "state": "Karnataka",
                "annual_turnover_cr": 12.5,
                "b2b_sales_pct": 30,
                "has_gstin": True,
                "has_nbfc_license": True,
                "uses_lsp": True,
                "has_digital_lending_app": True,
                "loan_portfolio_cr": 45.0,
                "employee_count": 120,
            }
        }


@router.post("/", status_code=201)
async def create_business(profile: BusinessProfileIn):
    """Create a new business profile. Triggers Profile Guardian agent."""
    data = profile.model_dump()
    # Convert booleans to integers for SQLite
    bool_fields = [
        "has_gstin", "has_nbfc_license", "has_pa_license", "has_udyam_registration",
        "is_listed", "uses_lsp", "has_digital_lending_app", "has_export_activities",
        "has_gst_notices", "files_einvoice", "alerts_enabled",
    ]
    for f in bool_fields:
        data[f] = int(data.get(f, False))

    result = guardian.run(data)

    if not result["success"]:
        raise HTTPException(status_code=422, detail={
            "errors": result["errors"],
            "warnings": result.get("warnings", []),
        })

    return {
        "business_id": result["business_id"],
        "msme_classification": result.get("msme_classification"),
        "warnings": result.get("warnings", []),
        "message": "Business profile created successfully",
    }


@router.get("/{business_id}")
async def get_business_profile(business_id: str):
    biz = get_business(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    return biz


@router.get("/")
async def list_businesses():
    return get_all_businesses()


@router.put("/{business_id}")
async def update_business_profile(business_id: str, profile: BusinessProfileIn):
    biz = get_business(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")

    data = profile.model_dump()
    bool_fields = [
        "has_gstin", "has_nbfc_license", "has_pa_license", "has_udyam_registration",
        "is_listed", "uses_lsp", "has_digital_lending_app", "has_export_activities",
        "has_gst_notices", "files_einvoice", "alerts_enabled",
    ]
    for f in bool_fields:
        data[f] = int(data.get(f, False))

    success = update_business(business_id, data)
    if not success:
        raise HTTPException(status_code=500, detail="Update failed")

    return {"message": "Profile updated", "business_id": business_id}