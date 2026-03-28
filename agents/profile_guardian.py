"""
agents/profile_guardian.py
Agent 1 — Profile Guardian
Validates business profile inputs, detects inconsistencies,
enriches with derived fields, and stores to DB.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import create_business, audit_log, create_alert
from datetime import datetime


REQUIRED_FIELDS = ["business_name", "entity_type", "industry", "state", "annual_turnover_cr"]

INDUSTRY_OPTIONS = [
    "Digital Lending / NBFC", "Payments / FinTech", "E-Commerce",
    "Manufacturing", "IT / Software Services", "Healthcare",
    "Agriculture / AgriTech", "Retail / Trading", "Other",
]

ENTITY_OPTIONS = [
    "Sole Proprietorship", "Partnership", "LLP",
    "Private Limited", "Public Limited", "OPC", "Trust", "Society",
]


def run(profile: dict) -> dict:
    """
    Validate, enrich, and store a business profile.
    Returns: { success, business_id, warnings, errors }
    """
    start = datetime.utcnow()
    errors = []
    warnings = []

    # ── Step 1: Required field check ─────────────────────────────────────────
    for f in REQUIRED_FIELDS:
        if not profile.get(f) and profile.get(f) != 0:
            errors.append(f"Missing required field: {f}")

    if errors:
        audit_log("ProfileGuardian", "validation_failed",
                  status="failure", input_data=profile,
                  error_message="; ".join(errors),
                  notes="Required fields missing")
        return {"success": False, "errors": errors, "warnings": []}

    # ── Step 2: Value validation ──────────────────────────────────────────────
    turnover = float(profile.get("annual_turnover_cr", 0))
    if turnover < 0:
        errors.append("Annual turnover cannot be negative")

    if profile.get("entity_type") not in ENTITY_OPTIONS:
        warnings.append(f"Entity type '{profile.get('entity_type')}' not in standard list")

    # ── Step 3: Consistency checks ────────────────────────────────────────────
    # NBFC with no loan portfolio
    if profile.get("has_nbfc_license") and float(profile.get("loan_portfolio_cr", 0)) == 0:
        warnings.append("NBFC license flagged but loan portfolio is ₹0. Please verify.")

    # Digital lending app with no NBFC or PA license
    if profile.get("has_digital_lending_app") and \
       not profile.get("has_nbfc_license") and \
       not profile.get("has_pa_license"):
        warnings.append(
            "Digital lending app without NBFC/PA license — you must partner with a Regulated Entity (RE)."
        )

    # LSP without digital lending app
    if profile.get("uses_lsp") and not profile.get("has_digital_lending_app"):
        warnings.append("LSP marked but no digital lending app — confirm if this is intentional.")

    # E-invoicing flag vs turnover
    if turnover >= 5.0 and not profile.get("files_einvoice") and float(profile.get("b2b_sales_pct", 0)) > 0:
        warnings.append(
            "Turnover ≥ ₹5 Cr with B2B sales but e-invoicing not enabled. "
            "This is likely a compliance gap — our analysis will flag this."
        )

    # Employee thresholds
    emp = int(profile.get("employee_count", 0))
    if emp >= 20 and not profile.get("has_pf_registration", False):
        warnings.append("20+ employees — PF registration is mandatory.")
    if emp >= 10 and not profile.get("has_esi_registration", False):
        warnings.append("10+ employees — ESI registration is mandatory.")

    # ── Step 4: Derive MSME classification ───────────────────────────────────
    inv = float(profile.get("investment_plant_cr", 0))
    if turnover <= 5 and inv <= 1:
        profile["msme_classification"] = "Micro Enterprise"
    elif turnover <= 50 and inv <= 10:
        profile["msme_classification"] = "Small Enterprise"
    elif turnover <= 250 and inv <= 50:
        profile["msme_classification"] = "Medium Enterprise"
    else:
        profile["msme_classification"] = "Beyond MSME"

    # ── Step 5: Store to DB ───────────────────────────────────────────────────
    if errors:
        audit_log("ProfileGuardian", "validation_failed",
                  status="failure", input_data={"name": profile.get("business_name")},
                  error_message="; ".join(errors))
        return {"success": False, "errors": errors, "warnings": warnings}

    biz_id = create_business(profile)

    duration = int((datetime.utcnow() - start).total_seconds() * 1000)
    audit_log(
        agent="ProfileGuardian",
        action="profile_created",
        status="success",
        business_id=biz_id,
        input_data={"name": profile["business_name"], "turnover": turnover},
        output={"business_id": biz_id, "msme_class": profile.get("msme_classification")},
        confidence=1.0,
        duration_ms=duration,
        notes=f"Profile created. MSME class: {profile.get('msme_classification')}. "
              f"Warnings: {len(warnings)}",
    )

    # Create welcome alert
    create_alert(
        business_id=biz_id,
        alert_type="ANALYSIS_COMPLETE",
        title="Profile Created — Run Your First Analysis",
        message=f"Welcome, {profile['business_name']}! Your profile is ready. "
                f"Click 'Run Analysis' to get your compliance assessment.",
        severity="LOW",
        action_url=f"/analyze/{biz_id}",
        action_label="Run Analysis",
    )

    if warnings:
        create_alert(
            business_id=biz_id,
            alert_type="ANOMALY",
            title=f"{len(warnings)} Profile Warning(s) Detected",
            message="\n".join(f"• {w}" for w in warnings),
            severity="MEDIUM",
            action_url=f"/business/{biz_id}/edit",
            action_label="Review Profile",
        )

    return {
        "success": True,
        "business_id": biz_id,
        "msme_classification": profile.get("msme_classification"),
        "warnings": warnings,
        "errors": [],
    }