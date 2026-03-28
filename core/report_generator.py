"""
core/report_generator.py
Generates professional HTML compliance reports downloadable from the UI.
"""
import json
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def generate_report(business: dict, obligations: list, risk_score: dict,
                    action_plan: dict, audit_trail: list, session_id: str) -> str:
    """
    Generate a full HTML compliance report.
    Returns the file path of the saved report.
    """
    now = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")
    biz_name = business.get("business_name", "Business")
    risk_level = risk_score.get("risk_level", "MEDIUM")
    risk_color = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#22c55e"}.get(risk_level, "#6b7280")
    score = risk_score.get("overall_score", 0)
    penalty = risk_score.get("total_penalty_inr", 0)

    # Build obligations HTML
    obs_html = ""
    for o in obligations:
        if o.get("is_benefit"):
            continue
        p = o.get("priority", "MEDIUM")
        p_color = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#22c55e"}.get(p, "#6b7280")
        steps_html = "".join(
            f"<li>{s}</li>" for s in (o.get("action_steps") or [])
        )
        obs_html += f"""
        <div class="obligation-card" style="border-left:4px solid {p_color}">
          <div class="obs-header">
            <span class="badge" style="background:{p_color}22;color:{p_color};border:1px solid {p_color}44">{p}</span>
            <span class="obs-reg">[{o.get('regulator')}] {o.get('category')}</span>
          </div>
          <h3 class="obs-title">{o.get('title')}</h3>
          <p class="obs-desc">{o.get('description')}</p>
          <div class="obs-meta">
            <span>📅 {o.get('deadline_type')}</span>
            <span>⚠️ Penalty: ₹{o.get('estimated_penalty_inr', 0):,.0f}</span>
            <span>📌 {o.get('citation')}</span>
          </div>
          {'<ul class="steps-list">' + steps_html + '</ul>' if steps_html else ''}
        </div>"""

    # Build audit trail HTML
    audit_html = ""
    for evt in (audit_trail or [])[:15]:
        status_color = {"success": "#22c55e", "failure": "#ef4444", "running": "#f59e0b"}.get(
            evt.get("status", ""), "#6b7280")
        audit_html += f"""
        <tr>
          <td>{evt.get('timestamp','')[:19].replace('T',' ')}</td>
          <td><code>{evt.get('agent_name','')}</code></td>
          <td>{evt.get('action','')}</td>
          <td style="color:{status_color};font-weight:600">{evt.get('status','').upper()}</td>
          <td>{evt.get('notes','')[:80]}</td>
        </tr>"""

    # Breakdown chart bars
    breakdown = risk_score.get("breakdown", {})
    breakdown_html = ""
    for reg, data in breakdown.items():
        pct = min(data.get("count", 0) * 20, 100)
        breakdown_html += f"""
        <div class="breakdown-row">
          <span class="reg-name">{reg}</span>
          <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
          <span class="reg-count">{data.get('count',0)} obligations</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ComplianceOS Report — {biz_name}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI',Arial,sans-serif; background:#f8fafc; color:#1e293b; }}
  .header {{ background:linear-gradient(135deg,#1e3a5f,#2e6db4); color:#fff; padding:40px 48px; }}
  .header h1 {{ font-size:2rem; font-weight:700; }}
  .header p {{ opacity:.8; margin-top:6px; }}
  .header-meta {{ display:flex; gap:32px; margin-top:20px; }}
  .meta-item {{ font-size:.85rem; opacity:.85; }}
  .meta-item strong {{ display:block; font-size:1rem; opacity:1; }}
  .body {{ max-width:1000px; margin:0 auto; padding:40px 24px; }}
  .section {{ margin-bottom:40px; }}
  .section-title {{ font-size:1.25rem; font-weight:700; color:#1e3a5f; border-bottom:2px solid #e2e8f0;
                    padding-bottom:8px; margin-bottom:20px; }}
  .metrics {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:32px; }}
  .metric-box {{ background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:20px; text-align:center;
                 box-shadow:0 1px 3px rgba(0,0,0,.06); }}
  .metric-value {{ font-size:2rem; font-weight:700; }}
  .metric-label {{ font-size:.8rem; color:#64748b; margin-top:4px; }}
  .risk-badge {{ display:inline-block; padding:6px 18px; border-radius:20px; font-size:.9rem; font-weight:700;
                 background:{risk_color}22; color:{risk_color}; border:1px solid {risk_color}44; }}
  .obligation-card {{ background:#fff; border-radius:10px; padding:20px; margin-bottom:16px;
                      box-shadow:0 1px 3px rgba(0,0,0,.06); }}
  .obs-header {{ display:flex; align-items:center; gap:10px; margin-bottom:10px; }}
  .badge {{ padding:3px 10px; border-radius:12px; font-size:.75rem; font-weight:700; }}
  .obs-reg {{ font-size:.8rem; color:#64748b; }}
  .obs-title {{ font-size:1rem; font-weight:700; color:#1e293b; margin-bottom:6px; }}
  .obs-desc {{ font-size:.875rem; color:#475569; line-height:1.6; margin-bottom:10px; }}
  .obs-meta {{ display:flex; gap:16px; font-size:.78rem; color:#64748b; flex-wrap:wrap; }}
  .steps-list {{ margin-top:12px; padding-left:20px; font-size:.83rem; color:#374151; line-height:2; }}
  .breakdown-row {{ display:flex; align-items:center; gap:12px; margin-bottom:10px; }}
  .reg-name {{ width:60px; font-size:.85rem; font-weight:700; color:#1e3a5f; }}
  .bar-track {{ flex:1; height:10px; background:#e2e8f0; border-radius:5px; }}
  .bar-fill {{ height:100%; background:linear-gradient(90deg,#2e6db4,#4f8ef7); border-radius:5px; }}
  .reg-count {{ font-size:.8rem; color:#64748b; width:100px; }}
  table {{ width:100%; border-collapse:collapse; font-size:.82rem; }}
  th {{ background:#1e3a5f; color:#fff; padding:10px 14px; text-align:left; }}
  td {{ padding:9px 14px; border-bottom:1px solid #f1f5f9; }}
  tr:hover td {{ background:#f8fafc; }}
  code {{ background:#f1f5f9; padding:2px 6px; border-radius:4px; font-size:.8rem; }}
  .footer {{ text-align:center; padding:32px; color:#94a3b8; font-size:.8rem; }}
  .callout {{ background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:14px 18px;
              color:#1e40af; font-size:.875rem; margin-bottom:20px; }}
  @media print {{ .header {{ -webkit-print-color-adjust:exact; }} }}
</style>
</head>
<body>

<div class="header">
  <div>⚖️ ComplianceOS — Compliance Intelligence Report</div>
  <h1>{biz_name}</h1>
  <p>{business.get('industry','')} · {business.get('entity_type','')} · {business.get('state','')}</p>
  <div class="header-meta">
    <div class="meta-item"><strong>₹{business.get('annual_turnover_cr',0)} Cr</strong>Annual Turnover</div>
    <div class="meta-item"><strong>{len([o for o in obligations if not o.get('is_benefit')])}</strong>Obligations</div>
    <div class="meta-item"><strong>₹{penalty/100000:.1f}L</strong>Penalty Exposure</div>
    <div class="meta-item"><strong>{now}</strong>Generated At</div>
  </div>
</div>

<div class="body">

  <div class="callout">
    ⚖️ This report is generated by ComplianceOS AI agents. All obligations are based on publicly available
    Indian regulatory frameworks. Consult a Chartered Accountant or legal counsel before taking action.
    Session ID: <code>{session_id}</code>
  </div>

  <div class="section">
    <div class="section-title">📊 Risk Summary</div>
    <div class="metrics">
      <div class="metric-box">
        <div class="metric-value" style="color:{risk_color}">{score}</div>
        <div class="metric-label">Risk Score (0–100)</div>
        <div style="margin-top:8px"><span class="risk-badge">{risk_level}</span></div>
      </div>
      <div class="metric-box">
        <div class="metric-value" style="color:#ef4444">{risk_score.get('high_count',0)}</div>
        <div class="metric-label">High Priority Obligations</div>
      </div>
      <div class="metric-box">
        <div class="metric-value" style="color:#f59e0b">{risk_score.get('medium_count',0)}</div>
        <div class="metric-label">Medium Priority Obligations</div>
      </div>
      <div class="metric-box">
        <div class="metric-value" style="color:#1e3a5f">₹{penalty/100000:.1f}L</div>
        <div class="metric-label">Max Penalty Exposure</div>
      </div>
    </div>
    <div class="section-title" style="font-size:1rem">Obligations by Regulator</div>
    {breakdown_html or '<p style="color:#94a3b8">No obligations found.</p>'}
  </div>

  <div class="section">
    <div class="section-title">📋 Compliance Obligations</div>
    {obs_html or '<p style="color:#22c55e">✅ No compliance obligations triggered for this profile.</p>'}
  </div>

  <div class="section">
    <div class="section-title">🔍 Agent Audit Trail</div>
    <table>
      <thead><tr><th>Timestamp</th><th>Agent</th><th>Action</th><th>Status</th><th>Notes</th></tr></thead>
      <tbody>{audit_html}</tbody>
    </table>
  </div>

</div>

<div class="footer">
  ComplianceOS — ET AI Hackathon 2026 | Report ID: {session_id} | Generated {now}<br>
  Regulatory sources: RBI (rbi.org.in) · GST Council (gst.gov.in) · SEBI (sebi.gov.in) · MSME (msme.gov.in)
</div>

</body>
</html>"""

    report_path = REPORTS_DIR / f"report_{business.get('id','biz')}_{session_id}.html"
    report_path.write_text(html, encoding="utf-8")
    return str(report_path)