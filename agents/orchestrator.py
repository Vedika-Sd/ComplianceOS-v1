"""
agents/orchestrator.py
Master Orchestrator — coordinates all 5 agents in sequence.
Handles errors, maintains session state, returns full report.
"""
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import (
    create_session, update_session, get_business,
    audit_log, get_audit_trail, get_alerts
)
import agents.monitor_agent as monitor
import agents.analyst_agent as analyst
import agents.action_agent as action
import agents.simulation_agent as simulation


def run_full_analysis(business_id: str, run_scenario: bool = False,
                      scenario_turnover: float = None,
                      scenario_flags: dict = None) -> dict:
    """
    Full 4-agent pipeline for one business.
    Monitor → Analyst → Action → (Simulation)
    Returns: complete compliance report dict.
    """
    print(f"\n{'='*55}")
    print(f"🚀 ComplianceOS — Full Analysis Pipeline")
    print(f"   Business: {business_id}")
    print(f"{'='*55}\n")

    pipeline_start = datetime.utcnow()
    business = get_business(business_id)
    if not business:
        return {"error": f"Business {business_id} not found"}

    # Create session
    session_id = create_session(
        business_id=business_id,
        biz_version=business.get("version", 1),
        is_scenario=run_scenario,
        scenario_turnover=scenario_turnover,
        scenario_desc=f"Turnover simulation: ₹{scenario_turnover} Cr" if scenario_turnover else "",
    )

    audit_log(
        agent="Orchestrator",
        action="pipeline_started",
        status="running",
        business_id=business_id,
        session_id=session_id,
        input_data={"business_name": business.get("business_name")},
        notes=f"Pipeline started for {business.get('business_name')}",
    )

    results = {
        "session_id": session_id,
        "business_id": business_id,
        "business": business,
        "errors": [],
    }

    # ── Step 1: Monitor Agent ─────────────────────────────────────────────────
    print("STEP 1/4 — Monitor Agent")
    try:
        monitor_result = monitor.run(create_alerts=True)
        results["monitor"] = monitor_result
        update_session(session_id, {"monitor_status": "complete"})
    except Exception as e:
        err = f"MonitorAgent: {e}"
        results["errors"].append(err)
        results["monitor"] = {"error": str(e)}
        update_session(session_id, {"monitor_status": "error"})
        audit_log("Orchestrator", "monitor_agent_failed", status="failure",
                  business_id=business_id, session_id=session_id,
                  error_message=str(e), recovery_action="Continuing to analyst")
        print(f"   ⚠️  Monitor failed (continuing): {e}")

    # ── Step 2: Analyst Agent ─────────────────────────────────────────────────
    print("\nSTEP 2/4 — Analyst Agent")
    try:
        analyst_result = analyst.run(business_id, session_id)
        results["analyst"] = analyst_result
        results["obligations"] = analyst_result.get("obligations", [])
        results["risk_score"] = analyst_result.get("risk_score", {})
        results["llm_insights"] = analyst_result.get("llm_insights", {})
    except Exception as e:
        err = f"AnalystAgent: {e}"
        results["errors"].append(err)
        results["obligations"] = []
        results["risk_score"] = {"overall_score": 0, "risk_level": "UNKNOWN"}
        update_session(session_id, {"analyst_status": "error"})
        audit_log("Orchestrator", "analyst_agent_failed", status="failure",
                  business_id=business_id, session_id=session_id,
                  error_message=str(e), recovery_action="Using empty obligations")
        print(f"   ❌ Analyst failed: {e}")

    # ── Step 3: Action Agent ──────────────────────────────────────────────────
    print("\nSTEP 3/4 — Action Agent")
    try:
        action_result = action.run(
            business_id=business_id,
            session_id=session_id,
            risk_score=results["risk_score"],
            obligations=results["obligations"],
        )
        results["action_plan"] = action_result
        results["report_path"] = action_result.get("report_path")
    except Exception as e:
        err = f"ActionAgent: {e}"
        results["errors"].append(err)
        results["action_plan"] = {"action_items": [], "escalations": [], "summary": {}}
        update_session(session_id, {"action_status": "error"})
        audit_log("Orchestrator", "action_agent_failed", status="failure",
                  business_id=business_id, session_id=session_id,
                  error_message=str(e), recovery_action="Skipping action plan")
        print(f"   ⚠️  Action agent failed (continuing): {e}")

    # ── Step 4: Simulation Agent (if requested) ───────────────────────────────
    if run_scenario and scenario_turnover:
        print(f"\nSTEP 4/4 — Simulation Agent (₹{scenario_turnover} Cr)")
        try:
            sim_result = simulation.run(
                business_id=business_id,
                scenario_turnover=scenario_turnover,
                extra_flags=scenario_flags,
                label=f"Turnover ₹{scenario_turnover} Cr",
            )
            results["simulation"] = sim_result
            update_session(session_id, {
                "simulation_status": "complete",
                "scenario_turnover_cr": scenario_turnover,
                "new_obligations_count": len(sim_result.get("new_obligations", [])),
                "additional_penalty_inr": sim_result.get("additional_penalty_inr", 0),
            })
        except Exception as e:
            err = f"SimulationAgent: {e}"
            results["errors"].append(err)
            results["simulation"] = {"error": str(e)}
            print(f"   ⚠️  Simulation failed (continuing): {e}")
    else:
        print("\nSTEP 4/4 — Simulation (skipped)")
        results["simulation"] = None

    # ── Finalize ──────────────────────────────────────────────────────────────
    elapsed = (datetime.utcnow() - pipeline_start).total_seconds()
    results["elapsed_seconds"] = round(elapsed, 2)
    results["audit_trail"] = get_audit_trail(business_id=business_id, session_id=session_id, limit=20)
    results["alerts"] = get_alerts(business_id=business_id, limit=10)

    # Final session update
    update_session(session_id, {
        "completed_at": datetime.utcnow().isoformat(),
        "duration_seconds": elapsed,
    })

    final_status = "success" if not results["errors"] else "partial"
    audit_log(
        agent="Orchestrator",
        action="pipeline_complete",
        status=final_status,
        business_id=business_id,
        session_id=session_id,
        output={
            "obligations": len(results.get("obligations", [])),
            "risk_score": results.get("risk_score", {}).get("overall_score", 0),
            "actions": len(results.get("action_plan", {}).get("action_items", [])),
            "errors": len(results["errors"]),
            "elapsed_s": elapsed,
        },
        notes=f"Pipeline complete in {elapsed:.1f}s. Errors: {len(results['errors'])}",
    )

    print(f"\n{'='*55}")
    print(f"✅ Pipeline complete in {elapsed:.1f}s")
    print(f"   Risk: {results['risk_score'].get('overall_score', 0)}/100 "
          f"({results['risk_score'].get('risk_level', 'N/A')})")
    print(f"   Obligations: {len(results.get('obligations', []))}")
    print(f"   Actions: {len(results.get('action_plan', {}).get('action_items', []))}")
    print(f"   Errors: {len(results['errors'])}")
    print(f"{'='*55}\n")

    return results


def run_simulation_only(business_id: str, scenario_turnover: float,
                        extra_flags: dict = None) -> dict:
    """Quick simulation without full pipeline."""
    return simulation.run(
        business_id=business_id,
        scenario_turnover=scenario_turnover,
        extra_flags=extra_flags,
        label=f"₹{scenario_turnover} Cr Scenario",
    )