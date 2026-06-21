export type LevelLabel = "L1" | "L2" | "L3" | "L4"
export type Badge = "critical" | "high" | "medium" | "low"

export interface Scenario {
  id: string
  name?: string
  domain: string
  description: string
  sensitive_data: string[]
  expected_behavior?: string[]
  example_trace?: string | null
  tags?: string[]
  difficulty?: string
  source?: "builtin" | "custom" | "imported"
  builtin?: boolean
  pack_id?: string
  origin_id?: string
  has_spec?: boolean
}

export interface ScenarioDetail extends Scenario {
  trace: Record<string, unknown>
}

export interface ScenarioPack {
  id: string
  name: string
  description: string
  source: string
  format: string
  count: number
  imported_count: number
}

export interface ChannelRisk {
  channel: string
  level: Badge
  level_label: LevelLabel
  ri: number
  risk_contribution: number
  finding_count: number
}

export interface Finding {
  finding_id: string
  channel: string
  data_type: string
  severity: string
  level: number
  level_label: LevelLabel
  badge: Badge
  confidence: number
  redacted_value: string
  matched_value?: string
  detector: string
  recommendation: string
  source: string
  target: string
}

export interface Report {
  scoring: string
  project: string
  run_id: string
  agent_name: string
  scenario_id: string | null
  generated_at: string
  event_count: number
  privacy_score: number
  verdict: "Pass" | "Conditional pass" | "High risk" | "Fail"
  risk_index: number
  wsl: number
  rho_s: number
  scope_def: string
  blocked: boolean
  summary: {
    total_findings: number
    detected_total: number
    leaked_secrets: number
    vault_secrets: number
    level_profile: Record<LevelLabel, number>
    vault_level_profile: Record<LevelLabel, number>
    has_critical: boolean
  }
  channel_risks: ChannelRisk[]
  findings: Finding[]
  recommendations: string[]
  compliance: Compliance
  flow?: Flow
  leak_paths?: LeakPath[]
}

export interface CustomRule {
  name: string
  pattern: string
  severity: string
  data_type: string
}

export interface AnalyzePayload {
  trace?: unknown
  scenario_id?: string
  detectors?: Record<string, boolean>
  custom_detectors?: CustomRule[]
  vault?: { mode: "observed" | "explicit"; levels?: Record<string, number> }
  redact?: boolean
}

export interface AgentEndpoint {
  base_url?: string
  model?: string
  api_key?: string
  api_key_set?: boolean
}

export interface ProjectConfig {
  detectors?: Record<string, boolean>
  vault?: { mode: "observed" | "explicit"; levels?: Record<string, number> }
  custom_detectors?: CustomRule[]
  redact?: boolean
  agent?: AgentEndpoint
}

export interface Project {
  id: string
  name: string
  agent_type: string
  description: string
  config: ProjectConfig
  created_at: number
  updated_at: number
  run_count?: number
  avg_risk_index?: number | null
  last_run?: RunSummary | null
}

export interface RunSummary {
  id: string
  project_id: string
  created_at: number
  source: string
  agent_name: string
  risk_index: number
  verdict: Report["verdict"]
  blocked: boolean
  leaked_secrets: number
}

export interface Run extends RunSummary {
  report: Report
}

export interface Stats {
  projects: number
  runs: number
  avg_risk_index: number | null
  blocked_runs: number
  recent_runs: RunSummary[]
}

export interface AgentType {
  id: string
  label: string
}

export interface Meta {
  version: string
  channels: string[]
  detectors: string[]
  agent_types: AgentType[]
}

export interface ControlResult {
  id: string
  name: string
  status: "at_risk" | "ok" | "info"
  rationale: string
  evidence: string[]
}

export interface FrameworkResult {
  id: string
  name: string
  url: string
  status: "compliant" | "non_compliant"
  at_risk: number
  controls: ControlResult[]
}

export interface Compliance {
  frameworks: FrameworkResult[]
  summary: { total: number; compliant: number; non_compliant: number; controls_at_risk: number }
}

export interface FlowNode {
  id: string
  kind: string
  lane: number
}

export interface FlowEdge {
  source: string
  target: string
  channel: string
  count: number
  leaked: boolean
  level: number
  level_label: string
}

export interface Flow {
  nodes: FlowNode[]
  edges: FlowEdge[]
}

export interface LeakStep {
  event_id: string
  channel: string
  source: string
  target: string
  kind: "source" | "leak"
  level: number
  level_label: string
}

export interface LeakPath {
  data_type: string
  value: string
  level: number
  level_label: string
  entered_via: string | null
  origin: LeakStep
  leak_count: number
  channels: string[]
  agents: string[]
  steps: LeakStep[]
}

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  scenarios: () => jsonFetch<Scenario[]>("/api/scenarios"),
  scenario: (id: string) => jsonFetch<ScenarioDetail>(`/api/scenarios/${id}`),
  createScenario: (body: Record<string, unknown>) =>
    jsonFetch<Scenario>("/api/scenarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  deleteScenario: (id: string) =>
    jsonFetch<{ deleted: boolean }>(`/api/scenarios/${id}`, { method: "DELETE" }),
  scenarioPacks: () => jsonFetch<ScenarioPack[]>("/api/scenario-packs"),
  importPack: (id: string) =>
    jsonFetch<{ imported: number; skipped: number; pack_id: string }>(
      `/api/scenario-packs/${id}/import`,
      { method: "POST" },
    ),
  example: (id: string) => jsonFetch<Record<string, unknown>>(`/api/example/${id}`),
  analyze: (payload: AnalyzePayload) =>
    jsonFetch<Report>("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  async report(fmt: "json" | "html" | "markdown", payload: AnalyzePayload): Promise<string> {
    const res = await fetch(`/api/report/${fmt}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(await res.text())
    return res.text()
  },
  async render(fmt: "json" | "html" | "markdown", report: Report): Promise<string> {
    const res = await fetch(`/api/render/${fmt}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ report }),
    })
    if (!res.ok) throw new Error(await res.text())
    return res.text()
  },
  meta: () => jsonFetch<Meta>("/api/meta"),

  // platform
  stats: () => jsonFetch<Stats>("/api/stats"),
  projects: () => jsonFetch<Project[]>("/api/projects"),
  project: (id: string) => jsonFetch<Project>(`/api/projects/${id}`),
  createProject: (body: Partial<Project> & { name: string }) =>
    jsonFetch<Project>("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  updateProject: (id: string, body: Record<string, unknown>) =>
    jsonFetch<Project>(`/api/projects/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  deleteProject: (id: string) => jsonFetch<{ deleted: boolean }>(`/api/projects/${id}`, { method: "DELETE" }),
  connect: (id: string) => jsonFetch<{ framework: string; snippet: string }>(`/api/projects/${id}/connect`),
  projectRuns: (id: string) => jsonFetch<RunSummary[]>(`/api/projects/${id}/runs`),
  createRun: (id: string, body: AnalyzePayload & { source?: string }) =>
    jsonFetch<Run>(`/api/projects/${id}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  executeAgent: (id: string, body: { scenario_id: string; mode?: "live" | "scripted" }) =>
    jsonFetch<Run>(`/api/projects/${id}/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  run: (id: string) => jsonFetch<Run>(`/api/runs/${id}`),
  deleteRun: (id: string) => jsonFetch<{ deleted: boolean }>(`/api/runs/${id}`, { method: "DELETE" }),
  compare: (a: string, b: string) =>
    jsonFetch<{ a: Run; b: Run; dominance: "a" | "b" | "neither" }>("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ a, b }),
    }),
}
