"""
agents/analyst_agent.py
Agent 3 — Compliance Analyst
Runs threshold engine (deterministic) + RAG retrieval + LLM explanation.
Produces structured obligations with plain-English descriptions.
"""
import sys
import json
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import (
    run_threshold_engine, compute_risk_score, save_obligations,
    save_risk_score, update_session, audit_log, get_business
)


def run(business_id: str, session_id: str) -> dict:
    """
    Full analysis pipeline for a business.
    Returns: { obligations, risk_score, rag_clauses, llm_insights }
    """
    start = datetime.utcnow()
    print(f"🔍 Analyst Agent: Analysing {business_id}...")

    business = get_business(business_id)
    if not business:
        return {"error": "Business not found"}

    audit_log(
        agent="AnalystAgent",
        action="analysis_started",
        status="running",
        business_id=business_id,
        session_id=session_id,
        input_data={
            "turnover": business["annual_turnover_cr"],
            "industry": business["industry"],
        },
        notes="Threshold engine + RAG analysis starting",
    )

    # ── Step 1: Deterministic threshold engine ────────────────────────────────
    print("   ⚙️  Running threshold engine (deterministic)...")
    obligations = run_threshold_engine(business)
    print(f"   ✅ {len(obligations)} obligations triggered")

    audit_log(
        agent="AnalystAgent",
        action="threshold_engine_complete",
        status="success",
        business_id=business_id,
        session_id=session_id,
        output={"obligations_count": len(obligations)},
        confidence=1.0,
        notes=f"Deterministic engine triggered {len(obligations)} obligations",
    )

    # ── Step 2: RAG retrieval ─────────────────────────────────────────────────
    rag_clauses = []
    print("   🔍 Running RAG retrieval...")
    try:
        from core.rag_pipeline import retrieve, get_chroma_stats
        stats = get_chroma_stats()

        if stats["chunks"] > 0:
            queries = [_build_profile_query(business)]
            if business.get("has_digital_lending_app"):
                queries.append("RBI digital lending KFS LSP fund flow")
            if float(business.get("annual_turnover_cr", 0)) >= 4.5:
                queries.append("GST e-invoicing threshold 5 crore mandatory")
            if business.get("has_nbfc_license"):
                queries.append("NBFC compliance reporting NOF requirements")

            seen = set()
            for q in queries:
                for clause in retrieve(q, k=3):
                    key = clause["content"][:60]
                    if key not in seen:
                        seen.add(key)
                        rag_clauses.append(clause)

            print(f"   ✅ {len(rag_clauses)} relevant clauses retrieved")
        else:
            print("   ℹ️  ChromaDB empty — using rule engine only")

        audit_log(
            agent="AnalystAgent",
            action="rag_retrieval_complete",
            status="success",
            business_id=business_id,
            session_id=session_id,
            output={"clauses": len(rag_clauses)},
            notes=f"RAG retrieved {len(rag_clauses)} clauses",
        )
    except Exception as e:
        print(f"   ⚠️  RAG skipped: {e}")
        audit_log(
            agent="AnalystAgent",
            action="rag_retrieval",
            status="failure",
            business_id=business_id,
            session_id=session_id,
            error_message=str(e),
            recovery_action="Continuing with deterministic rules only",
        )

    # ── Step 3: LLM enrichment ────────────────────────────────────────────────
    llm_insights = {}
    print("   🤖 Generating LLM insights...")
    try:
        llm_insights = _generate_llm_insights(business, obligations, rag_clauses)
        audit_log(
            agent="AnalystAgent",
            action="llm_enrichment_complete",
            status="success",
            business_id=business_id,
            session_id=session_id,
            output={"insights_generated": bool(llm_insights)},
            confidence=0.85,
            notes="LLM insights generated for executive summary",
        )
    except Exception as e:
        print(f"   ⚠️  LLM enrichment skipped: {e}")
        llm_insights = {
            "executive_summary": _fallback_summary(business, obligations),
            "top_risk": _fallback_top_risk(obligations),
        }
        audit_log(
            agent="AnalystAgent",
            action="llm_enrichment",
            status="failure",
            business_id=business_id,
            session_id=session_id,
            error_message=str(e),
            recovery_action="Using rule-based fallback summary",
        )

    # ── Step 4: Risk scoring ──────────────────────────────────────────────────
    risk_score = compute_risk_score(obligations)
    save_risk_score(business_id, session_id, risk_score)

    # ── Step 5: Save obligations ──────────────────────────────────────────────
    saved = save_obligations(
        business_id=business_id,
        session_id=session_id,
        obligations=obligations,
        biz_version=business.get("version", 1),
    )

    # ── Step 6: Update session ────────────────────────────────────────────────
    high_count = sum(1 for o in obligations if o.get("priority") == "HIGH")
    update_session(session_id, {
        "analyst_status": "complete",
        "total_obligations": len(obligations),
        "high_priority_count": high_count,
        "total_penalty_inr": risk_score["total_penalty_inr"],
        "risk_score": risk_score["overall_score"],
        "risk_level": risk_score["risk_level"],
    })

    duration = int((datetime.utcnow() - start).total_seconds() * 1000)
    audit_log(
        agent="AnalystAgent",
        action="analysis_complete",
        status="success",
        business_id=business_id,
        session_id=session_id,
        output={
            "obligations": len(obligations),
            "risk_score": risk_score["overall_score"],
            "risk_level": risk_score["risk_level"],
            "penalty_inr": risk_score["total_penalty_inr"],
        },
        confidence=0.95,
        duration_ms=duration,
        notes=f"Analysis complete. Risk: {risk_score['overall_score']}/100 ({risk_score['risk_level']})",
    )

    print(f"   🎯 Risk Score: {risk_score['overall_score']}/100 ({risk_score['risk_level']})")
    return {
        "obligations": obligations,
        "risk_score": risk_score,
        "rag_clauses": rag_clauses,
        "llm_insights": llm_insights,
        "saved_count": saved,
    }


def _build_profile_query(business: dict) -> str:
    """Build a natural language query from business profile for RAG."""
    parts = [
        f"{business.get('industry', '')} company",
        f"turnover Rs. {business.get('annual_turnover_cr', 0)} crore",
        f"state {business.get('state', '')}",
    ]
    if business.get("has_nbfc_license"):
        parts.append("NBFC license")
    if business.get("has_digital_lending_app"):
        parts.append("digital lending app")
    if business.get("uses_lsp"):
        parts.append("LSP arrangement")
    return " ".join(parts)


def _generate_llm_insights(business: dict, obligations: list, rag_clauses: list) -> dict:
    """Use LLM to generate executive summary and top risk narrative."""
    from core.llm_provider import call_llm_simple

    high_obs = [o for o in obligations if o.get("priority") == "HIGH" and not o.get("is_benefit")]
    top_3 = high_obs[:3]

    obs_text = "\n".join([
        f"- [{o['regulator']}] {o['title']}: {o['description'][:150]}"
        for o in top_3
    ])

    prompt = f"""You are a senior compliance analyst for Indian MSMEs and FinTechs.

Business: {business.get('business_name')}
Industry: {business.get('industry')}
Turnover: ₹{business.get('annual_turnover_cr')} Crore
State: {business.get('state')}

Top compliance obligations triggered:
{obs_text if obs_text else "No high-priority obligations found."}

Write a 2-3 sentence executive summary of this business's compliance status.
Then write one sentence identifying the single most urgent action they must take.

Format:
SUMMARY: [your summary]
TOP_ACTION: [single most urgent action]"""

    response = call_llm_simple(prompt, temperature=0.1)

    summary = ""
    top_action = ""

    for line in response.split("\n"):
        if line.startswith("SUMMARY:"):
            summary = line.replace("SUMMARY:", "").strip()
        elif line.startswith("TOP_ACTION:"):
            top_action = line.replace("TOP_ACTION:", "").strip()

    return {
        "executive_summary": summary or _fallback_summary(business, obligations),
        "top_risk": top_action or _fallback_top_risk(obligations),
        "llm_powered": bool(summary),
    }


def _fallback_summary(business: dict, obligations: list) -> str:
    high = sum(1 for o in obligations if o.get("priority") == "HIGH")
    penalty = sum(o.get("estimated_penalty_inr", 0) for o in obligations)
    return (
        f"{business.get('business_name')} has {len(obligations)} compliance obligations "
        f"across Indian regulatory frameworks, of which {high} are high priority. "
        f"Maximum penalty exposure is ₹{penalty/100000:.1f} Lakh if all obligations are unaddressed."
    )


def _fallback_top_risk(obligations: list) -> str:
    high = [o for o in obligations if o.get("priority") == "HIGH" and not o.get("is_benefit")]
    if high:
        return f"Immediate action required: {high[0]['title']} — {high[0].get('citation', '')}"
    return "Review all flagged obligations and prioritise those with earliest deadlines."