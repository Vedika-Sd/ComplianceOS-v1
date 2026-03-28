"""
agents/monitor_agent.py
Agent 2 — Regulatory Monitor
Runs daily: checks RBI/GST/SEBI for new circulars,
loads them into ChromaDB, creates alerts for affected businesses.
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import (
    audit_log, create_alert, get_all_businesses,
    get_conn
)

# ── Simulated recent regulatory alerts (production: scrape actual portals) ────
REGULATORY_ALERTS = [
    {
        "alert_id": "RBI-2024-DL-001",
        "regulator": "RBI",
        "title": "RBI clarifies FLDG reporting format — quarterly submission mandatory",
        "date": "2024-03-15",
        "summary": "All Regulated Entities with FLDG arrangements must submit quarterly FLDG exposure reports in prescribed format. Format issued in Annex to the circular.",
        "impact_level": "HIGH",
        "affects": ["has_nbfc_license", "uses_lsp"],
        "threshold_change": False,
    },
    {
        "alert_id": "GST-2024-EI-001",
        "regulator": "GST",
        "title": "CBIC clarifies e-invoicing for SEZ and export supplies",
        "date": "2024-02-20",
        "summary": "E-invoicing is not mandatory for supplies to SEZ units and SEZ developers. Export supplies are also exempt. However, the exemption must be correctly marked in GSTR-1.",
        "impact_level": "MEDIUM",
        "affects": ["has_export_activities"],
        "threshold_change": False,
    },
    {
        "alert_id": "GST-2024-ITC-001",
        "regulator": "GST",
        "title": "CBIC issues guidelines on ITC reversal for vendor non-compliance",
        "date": "2024-01-10",
        "summary": "Businesses must reverse ITC within 60 days if supplier's GSTR-2B does not reflect the supply. Failure attracts 18% interest from original avail date.",
        "impact_level": "HIGH",
        "affects": ["has_gstin"],
        "threshold_change": False,
    },
    {
        "alert_id": "MSME-2024-UD-001",
        "regulator": "MSME",
        "title": "Annual Udyam self-declaration deadline — March 31st",
        "date": "2024-02-01",
        "summary": "All Udyam-registered businesses must file annual self-declaration on udyamregistration.gov.in before March 31st each year. Non-filing suspends MSME classification benefits.",
        "impact_level": "HIGH",
        "affects": ["has_udyam_registration"],
        "threshold_change": False,
    },
    {
        "alert_id": "RBI-2023-PA-001",
        "regulator": "RBI",
        "title": "RBI enhances PA net worth requirements",
        "date": "2023-11-30",
        "summary": "Payment Aggregators must achieve minimum net worth of ₹25 Crore by end of third year of license. Existing PAs must comply by March 2026.",
        "impact_level": "HIGH",
        "affects": ["has_pa_license"],
        "threshold_change": True,
    },
]


def run(create_alerts: bool = True) -> dict:
    """
    Main monitor run. Checks for new regulations,
    matches them to affected businesses, creates alerts.
    """
    start = datetime.utcnow()
    print("📡 Monitor Agent: Starting regulatory scan...")

    session_id = f"mon_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    audit_log(
        agent="MonitorAgent",
        action="scan_started",
        session_id=session_id,
        status="running",
        notes="Daily regulatory monitoring scan started",
    )

    # Get all businesses
    businesses = get_all_businesses()
    print(f"   📊 Monitoring {len(businesses)} business profiles")

    alerts_created = 0
    matched_alerts = []

    for alert in REGULATORY_ALERTS:
        # Check if alert is recent (within last 90 days for demo)
        try:
            alert_date = datetime.strptime(alert["date"], "%Y-%m-%d")
            if (datetime.utcnow() - alert_date).days > 90:
                continue
        except Exception:
            continue

        matched_businesses = []

        for biz in businesses:
            # Check if this alert affects this business
            affected = False
            for flag in alert.get("affects", []):
                if biz.get(flag):
                    affected = True
                    break

            # Turnover-based matching
            if "has_gstin" in alert.get("affects", []) and biz.get("has_gstin"):
                affected = True

            if not affected:
                continue

            matched_businesses.append(biz["id"])

            if create_alerts:
                create_alert(
                    business_id=biz["id"],
                    alert_type="NEW_REGULATION",
                    title=f"[{alert['regulator']}] {alert['title']}",
                    message=alert["summary"],
                    severity=alert["impact_level"],
                    regulator=alert["regulator"],
                    action_label="View Details",
                )
                alerts_created += 1

        if matched_businesses:
            matched_alerts.append({
                "alert_id": alert["alert_id"],
                "matched_businesses": len(matched_businesses),
            })

    # Try to load/update ChromaDB corpus
    chroma_status = "skipped"
    try:
        from core.rag_pipeline import get_chroma_stats, load_corpus
        stats = get_chroma_stats()
        if stats["chunks"] == 0:
            count = load_corpus()
            chroma_status = f"loaded_{count}_chunks"
            print(f"   📚 ChromaDB: loaded {count} regulatory chunks")
        else:
            chroma_status = f"ready_{stats['chunks']}_chunks"
            print(f"   📚 ChromaDB: {stats['chunks']} chunks already indexed")
    except Exception as e:
        chroma_status = f"error: {e}"
        print(f"   ⚠️  ChromaDB: {e}")

    duration = int((datetime.utcnow() - start).total_seconds() * 1000)

    audit_log(
        agent="MonitorAgent",
        action="scan_complete",
        session_id=session_id,
        status="success",
        output={
            "businesses_monitored": len(businesses),
            "alerts_created": alerts_created,
            "matched_alerts": len(matched_alerts),
            "chroma_status": chroma_status,
        },
        duration_ms=duration,
        notes=f"Scan complete. {alerts_created} alerts created for {len(businesses)} businesses.",
    )

    print(f"   ✅ Monitor complete: {alerts_created} alerts created")
    return {
        "businesses_monitored": len(businesses),
        "alerts_created": alerts_created,
        "matched_alerts": matched_alerts,
        "chroma_status": chroma_status,
        "session_id": session_id,
    }


def get_recent_alerts_for_business(business: dict) -> list:
    """Return relevant recent alerts for a specific business profile."""
    relevant = []
    for alert in REGULATORY_ALERTS:
        for flag in alert.get("affects", []):
            if business.get(flag):
                relevant.append(alert)
                break
    return relevant