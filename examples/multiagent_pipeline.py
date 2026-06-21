"""Multi-agent pipeline example using the generic recorder.

Simulates an orchestrator + summary agent flow (the shape of a LangGraph /
CrewAI pipeline) without requiring any framework installed. Run it:

    python examples/multiagent_pipeline.py
"""

from __future__ import annotations

from agentleak import AgentLeakRunner
from agentleak.integrations.generic import TraceRecorder


def main() -> None:
    rec = TraceRecorder(run_id="pipeline_demo", agent_name="healthcare_pipeline")

    rec.user_input("Summarize the record for patient Jean Tremblay.", source="user")

    # Orchestrator pulls the full record from an EHR tool.
    rec.tool_call(
        {"patient_name": "Jean Tremblay", "nam": "TREM12345678", "diagnosis": "Type 2 diabetes"},
        source="orchestrator", target="ehr_db", metadata={"tool_name": "get_record"},
    )

    # It writes the raw record into shared memory for the summary agent.
    rec.shared_memory(
        "Patient Jean Tremblay, NAM TREM12345678, has Type 2 diabetes.",
        source="orchestrator", target="memory",
    )

    # Inter-agent handoff carries the diagnosis.
    rec.inter_agent_message(
        "Please summarize: patient with Type 2 diabetes needs follow-up.",
        source="orchestrator", target="summary_agent",
    )

    # The summary agent produces a clean, minimal answer.
    rec.final_output(
        "The patient requires a routine follow-up appointment.",
        source="summary_agent", target="user",
    )

    result = AgentLeakRunner().analyze(rec.trace)

    print(f"\nPrivacy score: {result.privacy_score}/100  ({result.verdict})")
    for cr in result.score.channel_risks:
        print(f"  {cr.channel:<20} {cr.level:<9} {cr.finding_count} finding(s)")

    levels = {cr.channel: cr.level for cr in result.score.channel_risks}
    if levels.get("final_output", "none") == "none":
        print("\nThe final answer is clean — but the internal channels leaked.")


if __name__ == "__main__":
    main()
