"""Minimal SDK example.

Run it:

    python examples/simple_agent.py

It builds a trace where the final answer is clean but a tool call and shared
memory leak sensitive data, then prints the privacy report.
"""

from __future__ import annotations

from agentleak import AgentLeakRunner, Trace


def main() -> None:
    trace = Trace(run_id="simple_demo", agent_name="support_bot")

    # The user's request.
    trace.add_event(
        channel="user_input", source="user", target="agent",
        content="What's the status of my refund?",
    )

    # The agent calls a CRM tool with WAY too much data.
    trace.add_event(
        channel="tool_call", source="agent", target="crm",
        content={
            "customer_email": "alex.martin@example.com",
            "account_id": "CUST-558812",
            "ssn": "412-55-9087",
        },
        metadata={"tool_name": "lookup_customer"},
    )

    # It caches the raw record in shared memory.
    trace.add_event(
        channel="shared_memory", source="agent", target="memory",
        content="cached: alex.martin@example.com / CUST-558812 / ssn 412-55-9087",
    )

    # ...but the final answer looks perfectly clean.
    trace.add_event(
        channel="final_output", source="agent", target="user",
        content="Your refund has been processed and should arrive within 5 business days.",
    )

    result = AgentLeakRunner().analyze(trace)

    print(f"\nPrivacy score: {result.privacy_score}/100  ({result.verdict})")
    print(f"Findings: {len(result.findings)}\n")
    for cr in result.score.channel_risks:
        print(f"  {cr.channel:<20} {cr.level:<9} {cr.finding_count} finding(s)")
    print("\nTop findings:")
    for f in result.findings[:5]:
        print(f"  [{f.severity.value:<8}] {f.channel:<16} {f.data_type:<18} {f.redacted_value}")


if __name__ == "__main__":
    main()
