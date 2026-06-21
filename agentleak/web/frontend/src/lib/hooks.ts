import { useEffect, useState } from "react"
import { api, type AgentType } from "./api"

// Agent frameworks come from the backend registry (/api/meta), so a newly
// registered framework shows up in the pickers automatically.
export function useAgentTypes(): AgentType[] {
  const [types, setTypes] = useState<AgentType[]>([])
  useEffect(() => {
    api.meta().then((m) => setTypes(m.agent_types)).catch(() => {})
  }, [])
  return types
}
