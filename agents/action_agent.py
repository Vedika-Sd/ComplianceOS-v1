"""
agents/action_agent.py
Agent 4 — Action & Report Agent
Converts obligations → prioritised action items, creates alerts,
flags escalations, generates compliance report.
"""
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import (
    get_obligations, save_action_items, create_alert,
    update_session, audit_log, get_business, get_audit_trail
)
from core.report_generator import generate_report


URGENCY_MAP = {
    "One-time": "IMMEDIATE",
    "Continuous": "ONGOING",
    "Monthly": "THIS_MONTH",
    "Quarterly": "THIS_QUARTER",
    "Annual": "THIS_YEAR",
    "Optional": "THIS_QUARTER",
}

APPROVER_MAP = {
    "RBI": "Chief Compliance Officer / Company Secretary",
    "GST": "CFO / Chartered Accountant",
    "SEBI": "Company Secretary / Legal Counsel",
    "MSME": "MD / CEO",
    "MCA": "Company Secretary",
    "PF_ESI": "HR Head / CFO",
}


def run(business_id: str, session_id: str, risk_score: dict, obligations: list) -> dict:
    """
    Generate action plan, create alerts, produce report.
    Returns: { action_items, escalations, alerts_created, report_path, summary }
    """
    start = datetime.utcnow()
    print(f"✅ Action Agent: Building action plan for {business_id}...")

    business = get_business(business_id)
    if not business:
        return {"error": "Business not found"}

    audit_log(
        agent="ActionAgent",
        action="action_plan_started",
        status="running",
        business_id=business_id,
        session_id=session_id,
        input_data={"obligations": len(obligations), "risk_level": risk_score.get("risk_level")},
        notes="Generating action plan from obligations",
    )

    action_items = []
    escalations = []
    alerts_created = 0

    # ── Build action items per obligation ────────────────────────────────────
    applicable = [o for o in obligations if not o.get("is_benefit")]

    for obs in sorted(applicable, key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x.get("priority", "LOW"), 2)):
        steps_raw = obs.get("action_steps", [])
        if isinstance(steps_raw, str):
            try:
                steps_raw = json.loads(steps_raw)
            except Exception:
                steps_raw = [steps_raw]

        urgency = URGENCY_MAP.get(obs.get("deadline_type", ""), "THIS_MONTH")
        due_date = obs.get("due_date")
        penalty = obs.get("estimated_penalty_inr", 0)
        needs_human = obs.get("priority") == "HIGH" or penalty > 100000

        # Build structured action steps
        structured_steps = []
        for i, step_text in enumerate(steps_raw, 1):
            structured_steps.append({
                "title": f"Step {i}",
                "description": step_text,
                "priority": obs.get("priority", "MEDIUM"),
                "urgency": urgency,
                "due_date": due_date,
                "needs_human_approval": int(needs_human and i == 1),
                "recommended_approver": APPROVER_MAP.get(obs.get("regulator", ""), "Senior Management"),
                "external_link": obs.get("citation_url", ""),
            })

        # Save to DB — using obligation_id from session
        obl_id = f"obl_{uuid.uuid4().hex[:6]}"
        if structured_steps:
            save_action_items(obl_id, business_id, structured_steps)

        action_item = {
            "obligation_id": obl_id,
            "title": obs.get("title"),
            "regulator": obs.get("regulator"),
            "priority": obs.get("priority"),
            "urgency": urgency,
            "due_date": due_date,
            "steps": structured_steps,
            "penalty_inr": penalty,
            "needs_human_approval": needs_human,
            "recommended_approver": APPROVER_MAP.get(obs.get("regulator", ""), "Senior Management"),
            "citation": obs.get("citation", ""),
        }
        action_items.append(action_item)

        # Escalation if high-risk
        if needs_human:
            escalations.append({
                "title": obs.get("title"),
                "regulator": obs.get("regulator"),
                "reason": f"High-priority item — penalty exposure ₹{penalty:,.0f}",
                "recommended_approver": APPROVER_MAP.get(obs.get("regulator", ""), "Senior Management"),
            })

    # ── Create alerts ────────────────────────────────────────────────────────
    # Risk level alert
    risk_level = risk_score.get("risk_level", "MEDIUM")
    severity_map = {"HIGH": "CRITICAL", "MEDIUM": "HIGH", "LOW": "MEDIUM"}

    create_alert(
        business_id=business_id,
        session_id=session_id,
        alert_type="ANALYSIS_COMPLETE",
        title=f"Analysis Complete — Risk Level: {risk_level}",
        message=(
            f"Your compliance analysis is ready. Risk Score: {risk_score.get('overall_score')}/100. "
            f"{len(applicable)} obligations found with ₹{risk_score.get('total_penalty_inr',0)/100000:.1f}L "
            f"maximum penalty exposure."
        ),
        severity=severity_map.get(risk_level, "MEDIUM"),
        action_url=f"/dashboard/{business_id}",
        action_label="View Dashboard",
    )
    alerts_created += 1

    # Immediate action alerts
    immediate = [a for a in action_items if a["urgency"] == "IMMEDIATE"]
    if immediate:
        create_alert(
            business_id=business_id,
            session_id=session_id,
            alert_type="NEW_OBLIGATION",
            title=f"⚠️ {len(immediate)} Immediate Action(s) Required",
            message="\n".join(f"• {a['title']} [{a['regulator']}]" for a in immediate[:3]),
            severity="CRITICAL",
            action_url=f"/obligations/{business_id}",
            action_label="View Obligations",
        )
        alerts_created += 1

    # Deadline approaching alerts
    upcoming = _get_upcoming_deadlines(action_items)
    if upcoming:
        create_alert(
            business_id=business_id,
            session_id=session_id,
            alert_type="DEADLINE_APPROACHING",
            title=f"📅 {len(upcoming)} Deadline(s) in Next 30 Days",
            message="\n".join(
                f"• {a['title']} — due {a.get('due_date', 'N/A')}" for a in upcoming[:3]
            ),
            severity="HIGH",
            action_url=f"/obligations/{business_id}",
            action_label="View Deadlines",
        )
        alerts_created += 1

    # Escalation alert
    if escalations:
        create_alert(
            business_id=business_id,
            session_id=session_id,
            alert_type="ESCALATION_NEEDED",
            title=f"👤 {len(escalations)} Items Need Human Approval",
            message="\n".join(f"• {e['title']} → {e['recommended_approver']}" for e in escalations[:3]),
            severity="HIGH",
            action_url=f"/obligations/{business_id}",
            action_label="Review Escalations",
        )
        alerts_created += 1

    # ── Generate report ───────────────────────────────────────────────────────
    report_path = None
    print("   📄 Generating compliance report...")
    try:
        audit_trail = get_audit_trail(business_id=business_id, session_id=session_id, limit=20)
        report_path = generate_report(
            business=business,
            obligations=obligations,
            risk_score=risk_score,
            action_plan={"action_items": action_items, "escalations": escalations},
            audit_trail=audit_trail,
            session_id=session_id,
        )
        print(f"   ✅ Report saved: {report_path}")

        create_alert(
            business_id=business_id,
            session_id=session_id,
            alert_type="REPORT_READY",
            title="📄 Compliance Report Ready for Download",
            message="Your detailed compliance report has been generated and is ready to download.",
            severity="LOW",
            action_url=f"/reports/{business_id}",
            action_label="Download Report",
        )
        alerts_created += 1
    except Exception as e:
        print(f"   ⚠️  Report generation failed: {e}")
        audit_log(
            agent="ActionAgent",
            action="report_generation",
            status="failure",
            business_id=business_id,
            session_id=session_id,
            error_message=str(e),
            recovery_action="Action plan saved, report skipped",
        )

    # ── Update session ────────────────────────────────────────────────────────
    update_session(session_id, {
        "action_status": "complete",
        "total_actions": len(action_items),
        "report_path": report_path,
        "report_generated_at": datetime.utcnow().isoformat() if report_path else None,
    })

    summary = {
        "total_actions": len(action_items),
        "immediate": len(immediate),
        "escalations": len(escalations),
        "alerts_created": alerts_created,
        "report_generated": bool(report_path),
    }

    duration = int((datetime.utcnow() - start).total_seconds() * 1000)
    audit_log(
        agent="ActionAgent",
        action="action_plan_complete",
        status="success",
        business_id=business_id,
        session_id=session_id,
        output=summary,
        duration_ms=duration,
        notes=f"Action plan: {len(action_items)} actions, {len(escalations)} escalations",
    )

    print(f"   ✅ Action plan: {len(action_items)} items, {len(escalations)} escalations")
    return {
        "action_items": action_items,
        "escalations": escalations,
        "alerts_created": alerts_created,
        "report_path": report_path,
        "summary": summary,
    }


def _get_upcoming_deadlines(action_items: list, days: int = 30) -> list:
    """Return actions with deadlines within next N days."""
    today = datetime.utcnow()
    upcoming = []
    for item in action_items:
        due = item.get("due_date")
        if not due or due == "Ongoing":
            continue
        try:
            due_dt = datetime.strptime(due, "%Y-%m-%d")
            if 0 <= (due_dt - today).days <= days:
                upcoming.append(item)
        except Exception:
            continue
    return upcoming