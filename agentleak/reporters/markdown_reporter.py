"""Markdown report — readable in any editor, PR, or terminal."""

from __future__ import annotations

from typing import Any

_BADGE_ORDER = ["critical", "high", "medium", "low"]
_LEVEL_LABEL = {
    "critical": "L4 critical",
    "high": "L3 high",
    "medium": "L2 medium",
    "low": "L1 low",
    "none": "none",
}


def render(data: dict[str, Any]) -> str:
    lines: list[str] = []
    a = lines.append

    a("# AgentLeak Privacy Report")
    a("")
    a(f"- **Project:** {data.get('project', 'n/a')}")
    a(f"- **Agent:** {data.get('agent_name', 'n/a')}")
    if data.get("scenario_id"):
        a(f"- **Scenario:** {data['scenario_id']}")
    a(f"- **Run:** {data.get('run_id', 'n/a')}")
    a(f"- **Generated:** {data.get('generated_at', 'n/a')}")
    a("- **Scoring:** AgentRisk (severity-weighted Risk Index)")
    a("")

    ri = data.get("risk_index", 0.0)
    a(f"## Risk Index: {ri:.3f}  ·  Privacy score {data['privacy_score']}/100 — {data['verdict']}")
    a("")
    summary = data.get("summary", {})
    lp = summary.get("level_profile", {})
    a(f"- WSL (weighted severity leakage): **{data.get('wsl', 0)}**  /  ρ_S (vault density): **{data.get('rho_s', 0)}**")
    a(f"- Total findings: **{summary.get('total_findings', 0)}**")
    a(
        f"- Leaked by level — L4: {lp.get('L4', 0)} · L3: {lp.get('L3', 0)} · "
        f"L2: {lp.get('L2', 0)} · L1: {lp.get('L1', 0)}"
    )
    if data.get("scope_def"):
        a(f"- Scope (ρ_S denominator): {data['scope_def']}")
    if data.get("blocked"):
        a("- ⛔ **Blocked:** this run would fail a CI gate.")
    a("")

    a("## Risk by channel")
    a("")
    channel_risks = data.get("channel_risks", [])
    if channel_risks:
        a("| Channel | Level | Findings | Channel RI |")
        a("| --- | --- | ---: | ---: |")
        for cr in channel_risks:
            level = cr.get("level_label", _LEVEL_LABEL.get(cr.get("level", "none"), cr.get("level")))
            a(f"| {cr['channel']} | {level} | {cr['finding_count']} | {cr.get('ri', 0):.3f} |")
    else:
        a("_No leaks detected in any channel._")
    a("")

    a("## Findings")
    a("")
    findings = data.get("findings", [])
    if not findings:
        a("_No findings._")
    else:
        ordered = sorted(
            findings,
            key=lambda f: (_BADGE_ORDER.index(f["badge"]) if f.get("badge") in _BADGE_ORDER else 99),
        )
        for i, f in enumerate(ordered, start=1):
            value = f.get("redacted_value", f.get("matched_value", ""))
            a(f"### Finding {i} — {f.get('level_label', '')} ({f.get('data_type')})")
            a("")
            a(f"- **Channel:** {f['channel']}")
            a(f"- **Severity level:** {f.get('level_label', '')} (detector severity: {f['severity']})")
            a(f"- **Detector:** {f['detector']}")
            a(f"- **Value:** `{value}`")
            if f.get("recommendation"):
                a(f"- **Recommendation:** {f['recommendation']}")
            a("")

    leak_paths = data.get("leak_paths", [])
    if leak_paths:
        a("## Leak paths")
        a("")
        a("_Where each disclosed secret entered the system and how it propagated across agents._")
        a("")
        for p in leak_paths:
            chain = " → ".join(f"{s['source'] or '?'}:{s['channel']}" for s in p["steps"])
            agents = f" · agents: {', '.join(p['agents'])}" if p.get("agents") else ""
            a(
                f"- **{p['level_label']} {p['data_type']}** (`{p['value']}`) — entered via "
                f"`{p.get('entered_via') or 'unknown'}`, {p['leak_count']} disclosure(s){agents}\n"
                f"  - path: {chain}"
            )
        a("")

    recs = data.get("recommendations", [])
    if recs:
        a("## Recommendations")
        a("")
        for r in recs:
            a(f"- {r}")
        a("")

    compliance = data.get("compliance", {})
    frameworks = compliance.get("frameworks", [])
    if frameworks:
        cs = compliance.get("summary", {})
        a("## Compliance")
        a("")
        a(f"_{cs.get('compliant', 0)}/{cs.get('total', 0)} frameworks clear · "
          f"{cs.get('controls_at_risk', 0)} control(s) at risk_")
        a("")
        for fw in frameworks:
            status = "✅ clear" if fw["status"] == "compliant" else f"⚠️ {fw['at_risk']} at risk"
            a(f"### {fw['name']} — {status}")
            a("")
            for ctrl in fw["controls"]:
                mark = {"at_risk": "✗", "ok": "✓", "info": "ℹ"}.get(ctrl["status"], "·")
                ev = f" ({', '.join(ctrl['evidence'])})" if ctrl["evidence"] else ""
                a(f"- {mark} **{ctrl['name']}**{ev}")
            a("")

    a("---")
    a("_Scored with AgentRisk: RI = WSL / ρ_S, a density-normalized, "
      "severity-weighted Risk Index grounded in GDPR Article 9 and Québec Law 25._")

    return "\n".join(lines)
