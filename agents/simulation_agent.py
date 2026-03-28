"""
agents/simulation_agent.py
Agent 5 — Simulation Agent
Runs threshold engine on a hypothetical profile,
returns delta vs current state with LLM narrative.
"""
import sys
import copy
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import (
    run_simulation, compute_risk_score, audit_log, get_business,
    run_threshold_engine, create_alert
)


def run(business_id: str, scenario_turnover: float,
        extra_flags: dict = None, label: str = "") -> dict:
    """
    Simulate compliance obligations under a different turnover.
    extra_flags: additional profile changes (e.g. uses_lsp=1, has_nbfc_license=1)
    Returns full simulation delta.
    """
    start = datetime.utcnow()
    print(f"🔮 Simulation Agent: {business_id} → ₹{scenario_turnover} Cr...")

    business = get_business(business_id)
    if not business:
        return {"error": "Business not found"}

    base_turnover = float(business.get("annual_turnover_cr", 0))

    audit_log(
        agent="SimulationAgent",
        action="simulation_started",
        status="running",
        business_id=business_id,
        input_data={
            "base_turnover": base_turnover,
            "scenario_turnover": scenario_turnover,
            "extra_flags": extra_flags or {},
        },
        notes=f"Scenario: ₹{base_turnover} Cr → ₹{scenario_turnover} Cr"
              + (f" + {extra_flags}" if extra_flags else ""),
    )

    # Run simulation via DB manager
    result = run_simulation(business_id, scenario_turnover, extra_flags)

    if not result:
        return {"error": "Simulation failed"}

    # Enrich with LLM narrative
    narrative = _generate_narrative(business, result, scenario_turnover, label)

    # Build structured output
    new_obs = result.get("new_obligations", [])
    removed_obs = result.get("removed_obligations", [])
    risk_delta = result.get("risk_delta", 0)
    add_penalty = result.get("additional_penalty_inr", 0)

    # Create alert if significant impact
    if new_obs or risk_delta > 10:
        create_alert(
            business_id=business_id,
            alert_type="THRESHOLD_CROSSED",
            title=f"Scenario Analysis: {len(new_obs)} New Obligations at ₹{scenario_turnover} Cr",
            message=(
                f"If your turnover reaches ₹{scenario_turnover} Cr, "
                f"{len(new_obs)} new compliance obligations are triggered with "
                f"₹{add_penalty/100000:.1f}L additional penalty exposure. "
                f"Risk score changes from {result.get('base_risk_score')} to {result.get('scenario_risk_score')}."
            ),
            severity="HIGH" if new_obs else "MEDIUM",
            action_url=f"/simulator/{business_id}",
            action_label="View Simulation",
        )

    duration = int((datetime.utcnow() - start).total_seconds() * 1000)
    audit_log(
        agent="SimulationAgent",
        action="simulation_complete",
        status="success",
        business_id=business_id,
        output={
            "new_obligations": len(new_obs),
            "removed_obligations": len(removed_obs),
            "risk_delta": risk_delta,
            "additional_penalty_inr": add_penalty,
        },
        confidence=0.98,
        duration_ms=duration,
        notes=(
            f"Simulation complete. {len(new_obs)} new obligations triggered. "
            f"Risk: {result.get('base_risk_score')} → {result.get('scenario_risk_score')}. "
            f"Additional penalty: ₹{add_penalty:,.0f}"
        ),
    )

    print(f"   ✅ Simulation: {len(new_obs)} new obligations, risk delta {risk_delta:+d}")
    return {
        **result,
        "narrative": narrative,
        "scenario_label": label or f"Turnover at ₹{scenario_turnover} Cr",
    }


def _generate_narrative(business: dict, result: dict, scenario_turnover: float, label: str) -> str:
    """LLM-generated or fallback narrative for the simulation."""
    new_obs = result.get("new_obligations", [])
    base_score = result.get("base_risk_score", 0)
    scenario_score = result.get("scenario_risk_score", 0)
    add_penalty = result.get("additional_penalty_inr", 0)

    if not new_obs:
        return (
            f"If {business.get('business_name')} grows to ₹{scenario_turnover} Cr turnover, "
            f"no new compliance obligations are triggered beyond the current {result.get('base_obligation_count', 0)}. "
            f"This is a compliance-neutral growth scenario."
        )

    # Try LLM
    try:
        from core.llm_provider import call_llm_simple
        obs_list = "\n".join(f"- [{o['regulator']}] {o['title']}" for o in new_obs[:4])
        prompt = f"""A business named {business.get('business_name')} ({business.get('industry')}) 
currently at ₹{business.get('annual_turnover_cr')} Cr turnover is simulating growth to ₹{scenario_turnover} Cr.

New compliance obligations that would be triggered:
{obs_list}

Additional penalty exposure: ₹{add_penalty/100000:.1f} Lakh
Risk score change: {base_score} → {scenario_score}

Write 2 sentences explaining what this means for the business and what they should plan for.
Be specific and practical. No generic advice."""

        response = call_llm_simple(prompt, temperature=0.2)
        if response and "[LLM unavailable" not in response:
            return response.strip()
    except Exception:
        pass

    # Fallback
    top = new_obs[0] if new_obs else {}
    return (
        f"Growing to ₹{scenario_turnover} Cr triggers {len(new_obs)} new compliance obligation(s) "
        f"for {business.get('business_name')}, most critically: {top.get('title', 'N/A')} "
        f"({top.get('citation', '')}). "
        f"Plan for ₹{add_penalty/100000:.1f}L additional compliance cost and start preparation "
        f"at least 90 days before crossing the threshold."
    )


def run_multi_scenario(business_id: str, scenarios: list) -> list:
    """
    Run multiple scenarios at once. Useful for the simulator slider.
    scenarios: [{"turnover": 6.0, "label": "Moderate Growth"}, ...]
    """
    results = []
    for s in scenarios:
        r = run(
            business_id=business_id,
            scenario_turnover=s["turnover"],
            extra_flags=s.get("flags"),
            label=s.get("label", ""),
        )
        results.append(r)
    return results