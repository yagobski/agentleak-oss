// Display labels for agent frameworks. The authoritative list (and the SDK
// connection snippets) come from the backend registry via /api/meta and
// /api/projects/{id}/connect — this is only a fallback for rendering labels.
export const AGENT_LABELS: Record<string, string> = {
  generic: "Generic / SDK",
  langchain: "LangChain",
  langgraph: "LangGraph",
  crewai: "CrewAI",
  autogen: "AutoGen",
  openai_agents: "OpenAI Agents SDK",
}

export function agentLabel(t: string): string {
  return AGENT_LABELS[t] ?? t
}
