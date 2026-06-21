"""HTML report — a single self-contained file (inline CSS, no external assets,
no network calls), consistent with the local-only privacy guarantee.
"""

from __future__ import annotations

from importlib import resources
from typing import Any

from jinja2 import Template

# Internal (non-user-facing) disclosure channels — leaks here are the headline.
_INTERNAL_CHANNELS = {
    "tool_call", "shared_memory", "log", "inter_agent_message", "generated_file",
}

_VERDICT_COLORS = {
    "Pass": ("#6ad1a0", "rgba(106,209,160,0.14)"),
    "Conditional pass": ("#ffce56", "rgba(255,206,86,0.14)"),
    "High risk": ("#ff8c42", "rgba(255,140,66,0.14)"),
    "Fail": ("#ff4d4f", "rgba(255,77,79,0.14)"),
}


def _load_template() -> Template:
    text = resources.files("agentleak.reporters.templates").joinpath(
        "report.html.j2"
    ).read_text(encoding="utf-8")
    return Template(text)


def _build_insight(data: dict[str, Any]) -> str | None:
    """The headline takeaway: clean output, leaky internals."""
    channel_levels = {cr["channel"]: cr["level"] for cr in data.get("channel_risks", [])}
    output_level = channel_levels.get("final_output", "none")
    internal_hits = [
        cr for cr in data.get("channel_risks", [])
        if cr["channel"] in _INTERNAL_CHANNELS and cr["level"] != "none"
    ]
    if output_level in {"none", "low"} and internal_hits:
        worst = max(internal_hits, key=lambda c: c.get("ri", 0))
        chans = ", ".join(f"<code>{c['channel']}</code>" for c in internal_hits)
        return (
            "<b>Key insight:</b> the final answer looks safe, but sensitive data "
            f"leaked through internal channels ({chans}). The highest-risk channel is "
            f"<b>{worst['channel']}</b> ({worst.get('level_label', worst['level'])}, "
            f"RI {worst.get('ri', 0):.3f}). Output-only audits would have missed this."
        )
    return None


def render(data: dict[str, Any]) -> str:
    color, bg = _VERDICT_COLORS.get(data.get("verdict", ""), ("#9aa3b2", "rgba(154,163,178,0.14)"))
    max_contrib = max(
        (cr.get("ri", 0) for cr in data.get("channel_risks", [])),
        default=0,
    )
    template = _load_template()
    return template.render(
        d=data,
        verdict_color=color,
        verdict_bg=bg,
        insight=_build_insight(data),
        max_contrib=max_contrib,
    )
