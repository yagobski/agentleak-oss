import { useEffect, useState } from "react"
import { Loader2, Play, Plus, Trash2, Wand2 } from "lucide-react"
import { toast } from "sonner"
import { api, type AnalyzePayload, type CustomRule, type Scenario } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"

const DETECTORS = ["pii", "secrets", "healthcare", "finance", "hr"] as const
const DETECTOR_LABEL: Record<string, string> = {
  pii: "PII",
  secrets: "Secrets",
  healthcare: "Healthcare",
  finance: "Finance",
  hr: "HR",
}
const LEVEL_TO_SEVERITY: Record<string, string> = { "4": "critical", "3": "high", "2": "medium", "1": "low" }

interface Props {
  scenarios: Scenario[]
  loading: boolean
  onAnalyze: (payload: AnalyzePayload, traceText: string) => void
  initialScenarioId?: string
}

export function ConfigPanel({ scenarios, loading, onAnalyze, initialScenarioId }: Props) {
  const [scenarioId, setScenarioId] = useState("")
  const [traceText, setTraceText] = useState("")
  const [detectors, setDetectors] = useState<Record<string, boolean>>(
    Object.fromEntries(DETECTORS.map((d) => [d, true]))
  )
  const [rules, setRules] = useState<CustomRule[]>([])
  const [vaultMode, setVaultMode] = useState<"observed" | "explicit">("observed")
  const [vault, setVault] = useState({ 1: 0, 2: 0, 3: 0, 4: 0 })
  const [redact, setRedact] = useState(true)

  useEffect(() => {
    if (!scenarios.length) return
    if (initialScenarioId && scenarios.some((s) => s.id === initialScenarioId)) {
      loadScenario(initialScenarioId)
    } else if (!scenarioId) {
      loadScenario(scenarios[0].id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarios, initialScenarioId])

  async function loadScenario(id: string) {
    setScenarioId(id)
    try {
      const trace = await api.example(id)
      setTraceText(JSON.stringify(trace, null, 2))
    } catch (e) {
      toast.error(`Could not load scenario: ${(e as Error).message}`)
    }
  }

  function formatJson() {
    try {
      setTraceText(JSON.stringify(JSON.parse(traceText), null, 2))
      toast.success("Trace formatted")
    } catch {
      toast.error("Invalid JSON — cannot format")
    }
  }

  function run() {
    let trace: unknown
    try {
      trace = JSON.parse(traceText)
    } catch {
      toast.error("Trace is not valid JSON")
      return
    }
    const payload: AnalyzePayload = { trace, detectors, redact }
    const validRules = rules
      .filter((r) => r.name && r.pattern)
      .map((r) => ({ ...r, data_type: r.name }))
    if (validRules.length) payload.custom_detectors = validRules
    if (vaultMode === "explicit") {
      payload.vault = { mode: "explicit", levels: vault as unknown as Record<string, number> }
    }
    onAnalyze(payload, traceText)
  }

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1">
        <div className="space-y-5 p-5">
          {/* scenario */}
          <div className="space-y-2">
            <Label className="eyebrow">Scenario</Label>
            <Select value={scenarioId} onValueChange={loadScenario}>
              <SelectTrigger>
                <SelectValue placeholder="Pick a scenario" />
              </SelectTrigger>
              <SelectContent>
                {scenarios.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.name ?? s.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* trace */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="eyebrow">Trace (JSON)</Label>
              <button
                onClick={formatJson}
                className="flex items-center gap-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
              >
                <Wand2 className="size-3" /> Format
              </button>
            </div>
            <Textarea
              value={traceText}
              onChange={(e) => setTraceText(e.target.value)}
              spellCheck={false}
              className="h-52 resize-y font-mono text-[12px] leading-relaxed"
              placeholder="Paste an agent trace…"
            />
          </div>

          <Separator />

          {/* detectors */}
          <div className="space-y-3">
            <Label className="eyebrow">Detectors</Label>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
              {DETECTORS.map((d) => (
                <div key={d} className="flex items-center justify-between">
                  <span className="text-sm">{DETECTOR_LABEL[d]}</span>
                  <Switch
                    checked={detectors[d]}
                    onCheckedChange={(v) => setDetectors((s) => ({ ...s, [d]: v }))}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* custom rules */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <Label className="eyebrow">Custom rules</Label>
              <button
                onClick={() => setRules((r) => [...r, { name: "", pattern: "", severity: "high", data_type: "" }])}
                className="flex items-center gap-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
              >
                <Plus className="size-3" /> Add
              </button>
            </div>
            {rules.map((r, i) => (
              <div key={i} className="space-y-1.5 rounded-md border border-border p-2.5">
                <div className="flex gap-1.5">
                  <Input
                    value={r.name}
                    placeholder="name"
                    className="h-7 text-xs"
                    onChange={(e) => setRules((s) => s.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))}
                  />
                  <Select
                    value={String({ critical: 4, high: 3, medium: 2, low: 1 }[r.severity] ?? 3)}
                    onValueChange={(v) =>
                      setRules((s) => s.map((x, j) => (j === i ? { ...x, severity: LEVEL_TO_SEVERITY[v] } : x)))
                    }
                  >
                    <SelectTrigger className="h-7 w-16 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {["4", "3", "2", "1"].map((l) => (
                        <SelectItem key={l} value={l}>
                          L{l}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 shrink-0 text-muted-foreground"
                    onClick={() => setRules((s) => s.filter((_, j) => j !== i))}
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
                <Input
                  value={r.pattern}
                  placeholder="regex pattern, e.g. PROJECT-[A-Z]{3}-\d{4}"
                  className="h-7 font-mono text-xs"
                  onChange={(e) => setRules((s) => s.map((x, j) => (j === i ? { ...x, pattern: e.target.value } : x)))}
                />
              </div>
            ))}
          </div>

          <Separator />

          {/* vault */}
          <div className="space-y-2.5">
            <Label className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Vault scope <span className="lowercase">(ρ_S)</span>
            </Label>
            <div className="grid grid-cols-2 gap-1.5 rounded-md bg-muted p-1">
              {(["observed", "explicit"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setVaultMode(m)}
                  className={`rounded px-2 py-1 text-xs font-medium capitalize transition-colors ${
                    vaultMode === m ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"
                  }`}
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

          {/* redact */}
          <div className="flex items-center justify-between">
            <span className="text-sm">Redact sensitive values</span>
            <Switch checked={redact} onCheckedChange={setRedact} />
          </div>
        </div>
      </ScrollArea>

      <div className="border-t border-border p-4">
        <Button className="w-full" size="lg" onClick={run} disabled={loading}>
          {loading ? <Loader2 className="animate-spin" /> : <Play />}
          {loading ? "Analyzing…" : "Analyze"}
        </Button>
      </div>
    </div>
  )
}
