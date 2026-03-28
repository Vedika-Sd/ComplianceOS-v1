"""
database/db_manager.py
Central database manager for ComplianceOS.
Handles: schema init, all CRUD operations, threshold engine, audit logging.
"""
import sqlite3
import json
import uuid
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DB_PATH  = BASE_DIR / "complianceos.db"
SCHEMA_PATH   = BASE_DIR / "database" / "schema.sql"
SEED_PATH     = BASE_DIR / "database" / "seed_thresholds.sql"


# ── Connection helper ─────────────────────────────────────────────────────────
@contextmanager
def get_conn():
    """Context manager for SQLite connections. Always closes cleanly."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row          # rows accessible as dicts
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema initialisation ─────────────────────────────────────────────────────
def init_db() -> bool:
    """
    Create all tables and seed threshold rules.
    Safe to call multiple times — uses CREATE IF NOT EXISTS.
    """
    print("🗄️  Initialising ComplianceOS database...")

    with get_conn() as conn:
        # Create tables
        with open(SCHEMA_PATH) as f:
            conn.executescript(f.read())
        print("   ✅ Schema created")

        # Seed threshold rules
        with open(SEED_PATH) as f:
            conn.executescript(f.read())

        count = conn.execute("SELECT COUNT(*) FROM thresholds WHERE is_active=1").fetchone()[0]
        print(f"   ✅ {count} threshold rules loaded")

        # Seed scheduled jobs
        jobs = [
            ("daily_monitor",   "Daily regulatory monitor",  "08:00"),
            ("weekly_report",   "Weekly compliance report",  "Monday 09:00"),
            ("monthly_summary", "Monthly risk summary",      "1st 10:00"),
        ]
        for job_id, name, schedule in jobs:
            conn.execute("""
                INSERT OR IGNORE INTO scheduled_jobs(id, job_name, is_enabled)
                VALUES (?, ?, 1)
            """, (job_id, name))
        print("   ✅ Scheduled jobs seeded")

    print("   🎉 Database ready!")
    return True


# ── Business Profile CRUD ────────────────────────────────────────────────────
def create_business(profile: dict) -> str:
    """
    Insert a new business profile. Returns the business_id.
    Generates a unique ID if not provided.
    """
    biz_id = profile.get("id") or f"biz_{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO businesses (
                id, version, is_current,
                business_name, entity_type, industry, state, year_of_incorporation,
                annual_turnover_cr, projected_turnover_cr, digital_revenue_pct,
                b2b_sales_pct, exports_revenue_cr, investment_plant_cr, loan_portfolio_cr,
                has_gstin, has_nbfc_license, has_pa_license, has_udyam_registration,
                is_listed, uses_lsp, has_digital_lending_app, has_export_activities,
                has_gst_notices, files_einvoice,
                employee_count, inter_state_sales_pct, states_operating,
                contact_email, contact_phone, alerts_enabled,
                created_at, updated_at
            ) VALUES (
                :id, 1, 1,
                :business_name, :entity_type, :industry, :state, :year_of_incorporation,
                :annual_turnover_cr, :projected_turnover_cr, :digital_revenue_pct,
                :b2b_sales_pct, :exports_revenue_cr, :investment_plant_cr, :loan_portfolio_cr,
                :has_gstin, :has_nbfc_license, :has_pa_license, :has_udyam_registration,
                :is_listed, :uses_lsp, :has_digital_lending_app, :has_export_activities,
                :has_gst_notices, :files_einvoice,
                :employee_count, :inter_state_sales_pct, :states_operating,
                :contact_email, :contact_phone, :alerts_enabled,
                :created_at, :updated_at
            )
        """, {
            "id": biz_id,
            "business_name": profile["business_name"],
            "entity_type": profile.get("entity_type", "Private Limited"),
            "industry": profile.get("industry", "IT / Software Services"),
            "state": profile.get("state", "Maharashtra"),
            "year_of_incorporation": profile.get("year_of_incorporation"),
            "annual_turnover_cr": float(profile.get("annual_turnover_cr", 0)),
            "projected_turnover_cr": profile.get("projected_turnover_cr"),
            "digital_revenue_pct": float(profile.get("digital_revenue_pct", 0)),
            "b2b_sales_pct": float(profile.get("b2b_sales_pct", 0)),
            "exports_revenue_cr": float(profile.get("exports_revenue_cr", 0)),
            "investment_plant_cr": float(profile.get("investment_plant_cr", 0)),
            "loan_portfolio_cr": float(profile.get("loan_portfolio_cr", 0)),
            "has_gstin": int(profile.get("has_gstin", 0)),
            "has_nbfc_license": int(profile.get("has_nbfc_license", 0)),
            "has_pa_license": int(profile.get("has_pa_license", 0)),
            "has_udyam_registration": int(profile.get("has_udyam_registration", 0)),
            "is_listed": int(profile.get("is_listed", 0)),
            "uses_lsp": int(profile.get("uses_lsp", 0)),
            "has_digital_lending_app": int(profile.get("has_digital_lending_app", 0)),
            "has_export_activities": int(profile.get("has_export_activities", 0)),
            "has_gst_notices": int(profile.get("has_gst_notices", 0)),
            "files_einvoice": int(profile.get("files_einvoice", 0)),
            "employee_count": int(profile.get("employee_count", 0)),
            "inter_state_sales_pct": float(profile.get("inter_state_sales_pct", 0)),
            "states_operating": json.dumps(profile.get("states_operating", [])),
            "contact_email": profile.get("contact_email"),
            "contact_phone": profile.get("contact_phone"),
            "alerts_enabled": int(profile.get("alerts_enabled", 1)),
            "created_at": now,
            "updated_at": now,
        })

    audit_log(
        agent="ProfileGuardian",
        action="business_created",
        business_id=biz_id,
        output={"business_name": profile["business_name"], "turnover": profile.get("annual_turnover_cr")},
        notes=f"New business profile created: {profile['business_name']}",
    )
    return biz_id


def get_business(business_id: str) -> Optional[dict]:
    """Fetch the current version of a business profile."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM businesses WHERE id=? AND is_current=1",
            (business_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_businesses() -> List[dict]:
    """Return all current business profiles."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM businesses WHERE is_current=1 ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_business(business_id: str, updates: dict) -> bool:
    """
    Update a business profile by creating a new version.
    Old version is preserved (is_current=0).
    """
    old = get_business(business_id)
    if not old:
        return False

    # Mark old version as historical
    with get_conn() as conn:
        conn.execute(
            "UPDATE businesses SET is_current=0 WHERE id=? AND is_current=1",
            (business_id,)
        )
        # Merge old data with updates
        new_profile = {**old, **updates, "version": old["version"] + 1, "is_current": 1}
        new_profile["updated_at"] = datetime.utcnow().isoformat()
        create_business(new_profile)

    audit_log(
        agent="ProfileGuardian",
        action="business_updated",
        business_id=business_id,
        input_data=updates,
        notes=f"Profile updated to version {old['version'] + 1}",
    )
    return True


# ── Threshold Engine ──────────────────────────────────────────────────────────
def run_threshold_engine(business: dict) -> List[dict]:
    """
    THE DETERMINISTIC COMPLIANCE ENGINE.
    Evaluates every active threshold rule against the business profile.
    Returns list of triggered obligations.
    Zero LLM involvement — pure Python logic.
    """
    with get_conn() as conn:
        rules = conn.execute(
            "SELECT * FROM thresholds WHERE is_active=1 ORDER BY regulator, priority"
        ).fetchall()

    triggered = []

    for rule in rules:
        rule = dict(rule)
        # Evaluate primary condition
        if not _evaluate_condition(
            business,
            rule["condition_field"],
            rule["operator"],
            rule["condition_value"],
            rule["condition_type"]
        ):
            continue

        # Evaluate secondary condition if present
        if rule.get("condition_field_2"):
            if not _evaluate_condition(
                business,
                rule["condition_field_2"],
                rule["operator_2"],
                rule["condition_value_2"],
                rule["condition_type_2"]
            ):
                continue

        # Rule triggered!
        due_date = _compute_due_date(rule["deadline_type"], rule.get("deadline_days"))
        action_steps = json.loads(rule.get("action_steps", "[]"))

        triggered.append({
            "threshold_id": rule["id"],
            "rule_id": rule["rule_id"],
            "regulator": rule["regulator"],
            "category": rule["category"],
            "title": rule["obligation_title"],
            "description": rule["obligation_desc"],
            "priority": rule["priority"],
            "deadline_type": rule["deadline_type"],
            "due_date": due_date,
            "estimated_penalty_inr": rule["estimated_penalty_inr"],
            "penalty_description": rule.get("penalty_description", ""),
            "action_steps": action_steps,
            "citation": rule["citation"],
            "citation_url": rule.get("citation_url", ""),
            "is_benefit": bool(rule.get("is_benefit", 0)),
            "confidence": 1.0,  # Deterministic = 100% confidence
            "analysis_method": "rule_based",
        })

    return triggered


def _evaluate_condition(business: dict, field: str, operator: str, value: str, ctype: str) -> bool:
    """Evaluate a single condition against the business profile."""
    biz_val = business.get(field)
    if biz_val is None:
        return False

    try:
        if ctype == "numeric":
            biz_val = float(biz_val)
            threshold = float(value)
            ops = {">=": biz_val >= threshold, "<=": biz_val <= threshold,
                   ">": biz_val > threshold, "<": biz_val < threshold,
                   "==": biz_val == threshold, "!=": biz_val != threshold}
            return ops.get(operator, False)

        elif ctype == "boolean":
            biz_val = int(biz_val)
            threshold = int(value)
            return (biz_val == threshold) if operator == "==" else (biz_val != threshold)

        elif ctype == "string":
            return (str(biz_val) == value) if operator == "==" else (str(biz_val) != value)

    except (ValueError, TypeError):
        return False

    return False


def _compute_due_date(deadline_type: str, deadline_days: Optional[int]) -> Optional[str]:
    """Compute a human-readable due date from deadline type."""
    today = datetime.utcnow()

    if "one-time" in deadline_type.lower() and deadline_days:
        return (today + timedelta(days=deadline_days)).strftime("%Y-%m-%d")
    elif "monthly" in deadline_type.lower():
        # Next month's 15th (mid-month approximation)
        next_month = today.replace(day=1) + timedelta(days=32)
        return next_month.replace(day=15).strftime("%Y-%m-%d")
    elif "quarterly" in deadline_type.lower():
        # Next quarter end
        quarter_ends = [
            datetime(today.year, 6, 30), datetime(today.year, 9, 30),
            datetime(today.year, 12, 31), datetime(today.year + 1, 3, 31),
        ]
        for qe in quarter_ends:
            if qe > today:
                return qe.strftime("%Y-%m-%d")
    elif "annual" in deadline_type.lower():
        return datetime(today.year, 12, 31).strftime("%Y-%m-%d")
    elif "continuous" in deadline_type.lower():
        return "Ongoing"

    return None


# ── Risk Scoring ─────────────────────────────────────────────────────────────
def compute_risk_score(obligations: List[dict]) -> dict:
    """
    Compute overall and per-regulator risk scores.
    Deterministic scoring — no LLM.
    """
    if not obligations:
        return {"overall_score": 0, "risk_level": "LOW", "breakdown": {}}

    applicable = [o for o in obligations if not o.get("is_benefit")]
    high = [o for o in applicable if o["priority"] == "HIGH"]
    medium = [o for o in applicable if o["priority"] == "MEDIUM"]

    raw = (len(high) * 20) + (len(medium) * 8)
    score = min(raw, 100)

    level = "LOW" if score < 30 else ("MEDIUM" if score < 60 else "HIGH")

    breakdown = {}
    for o in applicable:
        reg = o["regulator"]
        if reg not in breakdown:
            breakdown[reg] = {"count": 0, "high": 0, "penalty_inr": 0}
        breakdown[reg]["count"] += 1
        breakdown[reg]["penalty_inr"] += o.get("estimated_penalty_inr", 0)
        if o["priority"] == "HIGH":
            breakdown[reg]["high"] += 1

    return {
        "overall_score": score,
        "risk_level": level,
        "high_count": len(high),
        "medium_count": len(medium),
        "total_penalty_inr": sum(o.get("estimated_penalty_inr", 0) for o in applicable),
        "breakdown": breakdown,
    }


# ── Obligation CRUD ──────────────────────────────────────────────────────────
def save_obligations(business_id: str, session_id: str, obligations: List[dict], biz_version: int = 1) -> int:
    """Save triggered obligations to DB. Returns count saved."""
    now = datetime.utcnow().isoformat()
    saved = 0

    with get_conn() as conn:
        for o in obligations:
            obl_id = f"obl_{uuid.uuid4().hex[:8]}"
            conn.execute("""
                INSERT INTO obligations (
                    id, business_id, business_version, threshold_id, analysis_session_id,
                    status, applicability, confidence,
                    regulator, category, title, description, priority,
                    deadline_type, due_date, estimated_penalty_inr, citation, action_steps,
                    triggered_by_agent, analysis_method, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    'OPEN', 'APPLICABLE', ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    'AnalystAgent', ?, ?, ?
                )
            """, (
                obl_id, business_id, biz_version, o["threshold_id"], session_id,
                o.get("confidence", 1.0),
                o["regulator"], o["category"], o["title"], o["description"], o["priority"],
                o["deadline_type"], o.get("due_date"), o.get("estimated_penalty_inr", 0),
                o["citation"], json.dumps(o.get("action_steps", [])),
                o.get("analysis_method", "rule_based"), now, now
            ))
            saved += 1

    return saved


def get_obligations(business_id: str, status: str = None) -> List[dict]:
    """Fetch obligations for a business, optionally filtered by status."""
    with get_conn() as conn:
        query = "SELECT * FROM obligations WHERE business_id=?"
        params = [business_id]
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY CASE priority WHEN 'HIGH' THEN 0 WHEN 'MEDIUM' THEN 1 ELSE 2 END"
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def update_obligation_status(obligation_id: str, status: str, notes: str = "") -> bool:
    """Update an obligation's status — called when user marks something done."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE obligations SET status=?, updated_at=? WHERE id=?
        """, (status, datetime.utcnow().isoformat(), obligation_id))
    return True


# ── Analysis Sessions ────────────────────────────────────────────────────────
def create_session(business_id: str, biz_version: int, is_scenario: bool = False,
                   scenario_turnover: float = None, scenario_desc: str = "") -> str:
    """Create a new analysis session record."""
    session_id = f"ses_{uuid.uuid4().hex[:8]}"
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO analysis_sessions (
                id, business_id, business_version,
                is_scenario, scenario_turnover_cr, scenario_description,
                monitor_status, analyst_status, action_status,
                started_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'running', 'pending', 'pending', ?)
        """, (session_id, business_id, biz_version,
              int(is_scenario), scenario_turnover, scenario_desc,
              datetime.utcnow().isoformat()))
    return session_id


def update_session(session_id: str, updates: dict):
    """Update session with results."""
    updates["completed_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [session_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE analysis_sessions SET {set_clause} WHERE id=?", values)


def get_sessions(business_id: str, limit: int = 10) -> List[dict]:
    """Get recent analysis sessions for a business."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM analysis_sessions
            WHERE business_id=? ORDER BY started_at DESC LIMIT ?
        """, (business_id, limit)).fetchall()
        return [dict(r) for r in rows]


# ── Action Items ─────────────────────────────────────────────────────────────
def save_action_items(obligation_id: str, business_id: str, steps: List[dict]) -> int:
    """Save action items for an obligation."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        for i, step in enumerate(steps, 1):
            conn.execute("""
                INSERT OR IGNORE INTO action_items (
                    id, obligation_id, business_id, step_number,
                    title, description, status, priority, urgency,
                    due_date, needs_human_approval, recommended_approver,
                    external_link, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"act_{uuid.uuid4().hex[:8]}",
                obligation_id, business_id, i,
                step.get("title", f"Step {i}"),
                step.get("description", ""),
                step.get("priority", "MEDIUM"),
                step.get("urgency", "THIS_MONTH"),
                step.get("due_date"),
                int(step.get("needs_human_approval", 0)),
                step.get("recommended_approver"),
                step.get("external_link"),
                now, now
            ))
    return len(steps)


def get_action_items(business_id: str, status: str = None) -> List[dict]:
    """Get action items for a business."""
    with get_conn() as conn:
        q = "SELECT * FROM action_items WHERE business_id=?"
        p = [business_id]
        if status:
            q += " AND status=?"
            p.append(status)
        q += " ORDER BY CASE urgency WHEN 'IMMEDIATE' THEN 0 WHEN 'THIS_WEEK' THEN 1 WHEN 'THIS_MONTH' THEN 2 ELSE 3 END"
        return [dict(r) for r in conn.execute(q, p).fetchall()]


# ── Alerts ───────────────────────────────────────────────────────────────────
def create_alert(business_id: str, alert_type: str, title: str, message: str,
                 severity: str = "MEDIUM", regulator: str = None,
                 obligation_id: str = None, session_id: str = None,
                 action_url: str = None, action_label: str = None) -> str:
    """Create an in-app alert."""
    alert_id = f"alt_{uuid.uuid4().hex[:8]}"
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO alerts (
                id, business_id, obligation_id, session_id,
                alert_type, title, message, severity, regulator,
                channel, is_read, is_dismissed, action_url, action_label,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'in_app', 0, 0, ?, ?, ?)
        """, (
            alert_id, business_id, obligation_id, session_id,
            alert_type, title, message, severity, regulator,
            action_url, action_label, datetime.utcnow().isoformat()
        ))
    return alert_id


def get_alerts(business_id: str, unread_only: bool = False, limit: int = 20) -> List[dict]:
    """Get alerts for a business."""
    with get_conn() as conn:
        q = "SELECT * FROM alerts WHERE business_id=? AND is_dismissed=0"
        p = [business_id]
        if unread_only:
            q += " AND is_read=0"
        q += f" ORDER BY created_at DESC LIMIT {limit}"
        return [dict(r) for r in conn.execute(q, p).fetchall()]


def mark_alert_read(alert_id: str):
    """Mark an alert as read."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE alerts SET is_read=1, read_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), alert_id)
        )


# ── Audit Log ─────────────────────────────────────────────────────────────────
def audit_log(
    agent: str,
    action: str,
    status: str = "success",
    business_id: str = None,
    session_id: str = None,
    obligation_id: str = None,
    threshold_id: str = None,
    input_data: Any = None,
    output: Any = None,
    confidence: float = None,
    citations: list = None,
    error_message: str = None,
    recovery_action: str = None,
    duration_ms: int = None,
    notes: str = "",
) -> str:
    """
    Append an immutable event to the audit log.
    NEVER call UPDATE or DELETE on audit_log.
    """
    event_id = f"evt_{uuid.uuid4().hex[:8]}"

    def safe_json(val):
        if val is None:
            return None
        try:
            return json.dumps(val)[:500]
        except Exception:
            return str(val)[:500]

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO audit_log (
                event_id, timestamp, agent_name, action, status,
                business_id, session_id, obligation_id, threshold_id,
                input_summary, output_summary, confidence, citations,
                error_message, recovery_action, duration_ms, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id, datetime.utcnow().isoformat(), agent, action, status,
            business_id, session_id, obligation_id, threshold_id,
            safe_json(input_data), safe_json(output), confidence,
            json.dumps(citations or []),
            error_message, recovery_action, duration_ms, notes
        ))
    return event_id


def get_audit_trail(business_id: str = None, session_id: str = None,
                    limit: int = 50) -> List[dict]:
    """Fetch recent audit events."""
    with get_conn() as conn:
        q = "SELECT * FROM audit_log WHERE 1=1"
        p = []
        if business_id:
            q += " AND business_id=?"
            p.append(business_id)
        if session_id:
            q += " AND session_id=?"
            p.append(session_id)
        q += f" ORDER BY timestamp DESC LIMIT {limit}"
        rows = conn.execute(q, p).fetchall()
        return [dict(r) for r in rows]


# ── Risk Score History ────────────────────────────────────────────────────────
def save_risk_score(business_id: str, session_id: str, score_data: dict):
    """Save a risk score to time-series table."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO risk_scores (
                business_id, session_id, overall_score, risk_level,
                gst_score, rbi_score, sebi_score, msme_score,
                penalty_exposure_inr, obligation_count, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            business_id, session_id,
            score_data["overall_score"], score_data["risk_level"],
            score_data.get("breakdown", {}).get("GST", {}).get("count", 0) * 10,
            score_data.get("breakdown", {}).get("RBI", {}).get("count", 0) * 10,
            score_data.get("breakdown", {}).get("SEBI", {}).get("count", 0) * 10,
            score_data.get("breakdown", {}).get("MSME", {}).get("count", 0) * 5,
            score_data["total_penalty_inr"],
            score_data["high_count"] + score_data["medium_count"],
            datetime.utcnow().isoformat()
        ))


def get_risk_history(business_id: str, limit: int = 10) -> List[dict]:
    """Get risk score time-series for a business."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM risk_scores WHERE business_id=?
            ORDER BY recorded_at DESC LIMIT ?
        """, (business_id, limit)).fetchall()
        return [dict(r) for r in rows]


# ── DB Stats ─────────────────────────────────────────────────────────────────
def get_db_stats() -> dict:
    """Return database statistics for the dashboard."""
    with get_conn() as conn:
        stats = {}
        for table in ["businesses", "thresholds", "obligations", "action_items",
                       "audit_log", "alerts", "analysis_sessions"]:
            try:
                stats[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception:
                stats[table] = 0
        stats["active_thresholds"] = conn.execute(
            "SELECT COUNT(*) FROM thresholds WHERE is_active=1"
        ).fetchone()[0]
        stats["open_obligations"] = conn.execute(
            "SELECT COUNT(*) FROM obligations WHERE status='OPEN'"
        ).fetchone()[0]
        stats["unread_alerts"] = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE is_read=0 AND is_dismissed=0"
        ).fetchone()[0]
    return stats


# ── Simulation helper ─────────────────────────────────────────────────────────
def run_simulation(business_id: str, scenario_turnover: float,
                   extra_flags: dict = None) -> dict:
    """
    Run threshold engine on a hypothetical profile.
    Returns delta vs current state.
    """
    import copy
    business = get_business(business_id)
    if not business:
        return {}

    # Build scenario profile
    scenario = copy.deepcopy(business)
    scenario["annual_turnover_cr"] = scenario_turnover
    if extra_flags:
        scenario.update(extra_flags)

    base_obligations = run_threshold_engine(business)
    scenario_obligations = run_threshold_engine(scenario)

    base_ids = {o["threshold_id"] for o in base_obligations}
    scenario_ids = {o["threshold_id"] for o in scenario_obligations}

    new_obs = [o for o in scenario_obligations if o["threshold_id"] not in base_ids]
    removed_obs = [o for o in base_obligations if o["threshold_id"] not in scenario_ids]

    base_risk = compute_risk_score(base_obligations)
    scenario_risk = compute_risk_score(scenario_obligations)

    return {
        "base_turnover_cr": business["annual_turnover_cr"],
        "scenario_turnover_cr": scenario_turnover,
        "base_obligations": base_obligations,
        "scenario_obligations": scenario_obligations,
        "new_obligations": new_obs,
        "removed_obligations": removed_obs,
        "base_risk_score": base_risk["overall_score"],
        "scenario_risk_score": scenario_risk["overall_score"],
        "base_penalty_inr": base_risk["total_penalty_inr"],
        "scenario_penalty_inr": scenario_risk["total_penalty_inr"],
        "additional_penalty_inr": scenario_risk["total_penalty_inr"] - base_risk["total_penalty_inr"],
        "risk_delta": scenario_risk["overall_score"] - base_risk["overall_score"],
    }


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()

    # Quick self-test
    print("\n🧪 Running self-test...")

    # Create a test business
    test_id = create_business({
        "business_name": "TestCo Digital Lending Pvt Ltd",
        "entity_type": "Private Limited",
        "industry": "Digital Lending / NBFC",
        "state": "Karnataka",
        "annual_turnover_cr": 12.5,
        "b2b_sales_pct": 30,
        "has_gstin": 1,
        "has_nbfc_license": 1,
        "uses_lsp": 1,
        "has_digital_lending_app": 1,
        "loan_portfolio_cr": 45.0,
        "employee_count": 120,
        "contact_email": "compliance@testco.in",
    })
    print(f"   ✅ Business created: {test_id}")

    # Run threshold engine
    business = get_business(test_id)
    obligations = run_threshold_engine(business)
    print(f"   ✅ Obligations triggered: {len(obligations)}")
    for o in obligations:
        print(f"      [{o['priority']}] {o['rule_id']} — {o['title']}")

    # Risk score
    risk = compute_risk_score(obligations)
    print(f"   ✅ Risk Score: {risk['overall_score']}/100 ({risk['risk_level']})")
    print(f"   ✅ Penalty Exposure: ₹{risk['total_penalty_inr']:,.0f}")

    # Simulation
    sim = run_simulation(test_id, scenario_turnover=6.5)
    print(f"   ✅ Simulation (₹12.5→₹6.5 Cr): {len(sim.get('removed_obligations',[]))} obligations removed")

    # Stats
    stats = get_db_stats()
    print(f"\n📊 DB Stats: {stats}")
    print("\n🎉 All systems operational!")