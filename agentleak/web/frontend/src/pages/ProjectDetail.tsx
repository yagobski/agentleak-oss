import { useCallback, useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { Check, Copy, GitCompare, Loader2, Play, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"
import {
  api,
  type CustomRule,
  type Project,
  type RunSummary,
  type Scenario,
} from "@/lib/api"
import { agentLabel } from "@/lib/agents"
import { useAgentTypes } from "@/lib/hooks"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { RunRow } from "@/features/RunRow"

const DETECTORS = ["pii", "secrets", "healthcare", "finance", "hr"] as const
const DETECTOR_LABEL: Record<string, string> = { pii: "PII", secrets: "Secrets", healthcare: "Healthcare", finance: "Finance", hr: "HR" }

export function ProjectDetail() {
  const { id = "" } = useParams()
  const nav = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [notFound, setNotFound] = useState(false)

  const reload = useCallback(() => {
    api.project(id).then(setProject).catch(() => setNotFound(true))
    api.projectRuns(id).then(setRuns).catch(() => {})
  }, [id])
  useEffect(reload, [reload])

  if (notFound) return <div className="animate-fade-up text-sm text-sev-l4">Project not found.</div>
  if (!project) return <div className="animate-fade-up text-sm text-muted-foreground">Loading…</div>

  return (
    <div className="animate-fade-up">
      <div className="mb-5">
        <Link to="/projects" className="text-xs text-muted-foreground hover:text-foreground">
          ← Projects
        </Link>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold tracking-tight">{project.name}</h1>
          <span className="rounded bg-muted px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted-foreground">
            {agentLabel(project.agent_type)}
          </span>
          <span className="text-sm text-muted-foreground">
            {project.run_count ?? 0} runs
            {project.avg_risk_index != null ? ` · avg RI ${project.avg_risk_index.toFixed(3)}` : ""}
          </span>
        </div>
        {project.description && <p className="mt-1 text-sm text-muted-foreground">{project.description}</p>}
      </div>

      <Tabs defaultValue="audit">
        <TabsList>
          <TabsTrigger value="audit">Audit</TabsTrigger>
          <TabsTrigger value="runs">Runs ({runs.length})</TabsTrigger>
          <TabsTrigger value="connect">Connect</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="audit">
          <AuditTab project={project} onRan={reload} />
        </TabsContent>
        <TabsContent value="runs">
          <RunsTab runs={runs} onChange={reload} />
        </TabsContent>
        <TabsContent value="connect">
          <ConnectTab project={project} />
        </TabsContent>
        <TabsContent value="settings">
          <SettingsTab project={project} onSaved={reload} onDeleted={() => nav("/projects")} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

// ---------------------------------------------------------------- Audit
function AuditTab({ project, onRan }: { project: Project; onRan: () => void }) {
  const nav = useNavigate()
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [scenarioId, setScenarioId] = useState("")
  const [trace, setTrace] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.scenarios().then((s) => {
      setScenarios(s)
      if (s.length) loadScenario(s[0].id)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function loadScenario(sid: string) {
    setScenarioId(sid)
    try {
      setTrace(JSON.stringify(await api.example(sid), null, 2))
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  async function run() {
    let parsed: unknown
    try {
      parsed = JSON.parse(trace)
    } catch {
      return toast.error("Trace is not valid JSON")
    }
    setBusy(true)
    try {
      const r = await api.createRun(project.id, { trace: parsed, source: "manual" })
      toast.success(`Run ${r.verdict} · RI ${r.report.risk_index.toFixed(3)}`)
      onRan()
      nav(`/runs/${r.id}`)
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className="p-5">
      <p className="mb-4 text-sm text-muted-foreground">
        Runs use this project's detectors and vault scope (edit them in Settings). Pick a scenario or paste
        a trace from your agent.
      </p>
      <div className="grid gap-4 md:grid-cols-[240px_1fr]">
        <div className="space-y-1.5">
          <Label className="text-xs">Scenario</Label>
          <Select value={scenarioId} onValueChange={loadScenario}>
            <SelectTrigger>
              <SelectValue placeholder="Pick a scenario" />
            </SelectTrigger>
            <SelectContent>
              {scenarios.map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button className="mt-2 w-full" onClick={run} disabled={busy}>
            {busy ? <Loader2 className="animate-spin" /> : <Play />} Run analysis
          </Button>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Trace (JSON)</Label>
          <Textarea
            value={trace}
            onChange={(e) => setTrace(e.target.value)}
            spellCheck={false}
            className="h-72 font-mono text-[12px] leading-relaxed"
          />
        </div>
      </div>
    </Card>
  )
}

// ---------------------------------------------------------------- Runs
function RunsTab({ runs, onChange }: { runs: RunSummary[]; onChange: () => void }) {
  const nav = useNavigate()
  const [a, setA] = useState("")
  const [b, setB] = useState("")
  const [result, setResult] = useState<{ dominance: string; aRi: number; bRi: number } | null>(null)

  async function compare() {
    if (!a || !b || a === b) return toast.error("Pick two different runs")
    try {
      const res = await api.compare(a, b)
      setResult({ dominance: res.dominance, aRi: res.a.risk_index, bRi: res.b.risk_index })
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  if (!runs.length) {
    return (
      <Card className="p-10 text-center text-sm text-muted-foreground">
        No runs yet. Use the Audit tab or connect your agent via the SDK.
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-end gap-2 border-b border-border px-4 py-3">
          <div className="flex items-center gap-2 text-sm">
            <GitCompare className="size-4 text-muted-foreground" />
            <span className="text-muted-foreground">Compare</span>
          </div>
          <RunSelect runs={runs} value={a} onChange={setA} placeholder="Run A" />
          <RunSelect runs={runs} value={b} onChange={setB} placeholder="Run B" />
          <Button size="sm" variant="outline" onClick={compare}>
            Compare
          </Button>
          {result && (
            <span className="text-sm">
              {result.dominance === "neither" ? (
                <span className="text-muted-foreground">
                  Neither dominates — ordering is weight-dependent (RI {result.aRi.toFixed(3)} vs {result.bRi.toFixed(3)}).
                </span>
              ) : (
                <span>
                  <b>Run {result.dominance.toUpperCase()}</b> is weight-robustly riskier (dominates at every level).
                </span>
              )}
            </span>
          )}
        </div>
        <div className="divide-y divide-border">
          {runs.map((r) => (
            <RunRow
              key={r.id}
              run={r}
              onClick={() => nav(`/runs/${r.id}`)}
              right={
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-7 text-muted-foreground"
                  onClick={(e) => {
                    e.stopPropagation()
                    api.deleteRun(r.id).then(() => {
                      toast.success("Run deleted")
                      onChange()
                    })
                  }}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              }
            />
          ))}
        </div>
      </Card>
    </div>
  )
}

function RunSelect({ runs, value, onChange, placeholder }: { runs: RunSummary[]; value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="h-8 w-48 text-xs">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {runs.map((r) => (
          <SelectItem key={r.id} value={r.id}>
            {r.verdict} · RI {r.risk_index.toFixed(2)} · {r.agent_name || "agent"}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

// ------------------------------------------------------------- Connect
function ConnectTab({ project }: { project: Project }) {
  const [copied, setCopied] = useState(false)
  const [snippet, setSnippet] = useState("# loading…")

  useEffect(() => {
    api.connect(project.id).then((r) => setSnippet(r.snippet)).catch((e) => setSnippet(`# ${(e as Error).message}`))
  }, [project.id, project.agent_type, project.name])

  function copy() {
    navigator.clipboard.writeText(snippet).then(() => {
      setCopied(true)
      toast.success("Snippet copied")
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <Card>
      <div className="flex items-center justify-between border-b border-border px-5 py-3">
        <div className="text-sm">
          Connect your <b>{agentLabel(project.agent_type)}</b> agent via the SDK
        </div>
        <Button variant="outline" size="sm" onClick={copy}>
          {copied ? <Check /> : <Copy />} Copy
        </Button>
      </div>
      <pre className="overflow-x-auto p-5 font-mono text-[12px] leading-relaxed text-foreground/90">{snippet}</pre>
      <div className="border-t border-border px-5 py-3 text-xs text-muted-foreground">
        Make sure the platform is running (<code className="rounded bg-muted px-1.5 py-0.5">agentleak serve</code>).
        Submitted runs appear under this project.
      </div>
    </Card>
  )
}

// ------------------------------------------------------------ Settings
function SettingsTab({ project, onSaved, onDeleted }: { project: Project; onSaved: () => void; onDeleted: () => void }) {
  const agentTypes = useAgentTypes()
  const [name, setName] = useState(project.name)
  const [agentType, setAgentType] = useState(project.agent_type)
  const [detectors, setDetectors] = useState<Record<string, boolean>>({
    pii: true, secrets: true, healthcare: true, finance: false, hr: false,
    ...(project.config.detectors ?? {}),
  })
  const [redact, setRedact] = useState(project.config.redact ?? true)
  const [vaultMode, setVaultMode] = useState<"observed" | "explicit">(project.config.vault?.mode ?? "observed")
  const [vault, setVault] = useState<Record<string, number>>({
    1: 0, 2: 0, 3: 0, 4: 0, ...(project.config.vault?.levels ?? {}),
  })
  const [rules, setRules] = useState<CustomRule[]>(project.config.custom_detectors ?? [])
  const [busy, setBusy] = useState(false)

  async function save() {
    setBusy(true)
    try {
      const config = {
        detectors,
        redact,
        vault: vaultMode === "explicit" ? { mode: "explicit", levels: vault } : { mode: "observed" },
        custom_detectors: rules.filter((r) => r.name && r.pattern).map((r) => ({ ...r, data_type: r.name })),
      }
      await api.updateProject(project.id, { name, agent_type: agentType, config })
      toast.success("Project saved")
      onSaved()
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    if (!confirm(`Delete project “${project.name}” and all its runs?`)) return
    try {
      await api.deleteProject(project.id)
      toast.success("Project deleted")
      onDeleted()
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="space-y-4 p-5">
        <div className="space-y-1.5">
          <Label className="text-xs">Name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Agent framework</Label>
          <Select value={agentType} onValueChange={setAgentType}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {agentTypes.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Separator />
        <div className="flex items-center justify-between">
          <span className="text-sm">Redact sensitive values</span>
          <Switch checked={redact} onCheckedChange={setRedact} />
        </div>
        <div className="space-y-2">
          <Label className="text-xs">Vault scope (ρ_S)</Label>
          <div className="grid grid-cols-2 gap-1.5 rounded-md bg-muted p-1">
            {(["observed", "explicit"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setVaultMode(m)}
                className={`rounded px-2 py-1 text-xs font-medium capitalize transition-colors ${vaultMode === m ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"}`}
              >
                {m === "observed" ? "Observed (auto)" : "Explicit"}
              </button>
            ))}
          </div>
          {vaultMode === "explicit" && (
            <div className="grid grid-cols-4 gap-1.5">
              {([4, 3, 2, 1] as const).map((l) => (
                <div key={l}>
                  <Label className="mb-1 block text-center text-[11px] text-muted-foreground">L{l}</Label>
                  <Input
                    type="number"
                    min={0}
                    value={vault[l]}
                    className="h-8 text-center text-xs"
                    onChange={(e) => setVault((v) => ({ ...v, [l]: Math.max(0, +e.target.value) }))}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <Card className="space-y-4 p-5">
        <div className="space-y-3">
          <Label className="text-xs">Detectors</Label>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
            {DETECTORS.map((d) => (
              <div key={d} className="flex items-center justify-between">
                <span className="text-sm">{DETECTOR_LABEL[d]}</span>
                <Switch checked={detectors[d]} onCheckedChange={(v) => setDetectors((s) => ({ ...s, [d]: v }))} />
              </div>
            ))}
          </div>
        </div>
        <Separator />
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <Label className="text-xs">Custom rules</Label>
            <button
              onClick={() => setRules((r) => [...r, { name: "", pattern: "", severity: "high", data_type: "" }])}
              className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
            >
              <Plus className="size-3" /> Add
            </button>
          </div>
          {rules.map((r, i) => (
            <div key={i} className="flex gap-1.5">
              <Input
                value={r.name}
                placeholder="name"
                className="h-7 text-xs"
                onChange={(e) => setRules((s) => s.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))}
              />
              <Input
                value={r.pattern}
                placeholder="regex"
                className="h-7 flex-[2] font-mono text-xs"
                onChange={(e) => setRules((s) => s.map((x, j) => (j === i ? { ...x, pattern: e.target.value } : x)))}
              />
              <Button variant="ghost" size="icon" className="size-7 shrink-0" onClick={() => setRules((s) => s.filter((_, j) => j !== i))}>
                <Trash2 className="size-3.5" />
              </Button>
            </div>
          ))}
        </div>
      </Card>

      <div className="lg:col-span-2 flex items-center justify-between">
        <Button variant="ghost" className="text-sev-l4" onClick={remove}>
          <Trash2 /> Delete project
        </Button>
        <Button onClick={save} disabled={busy}>
          {busy && <Loader2 className="animate-spin" />} Save changes
        </Button>
      </div>
    </div>
  )
}
