import { ArrowRight, Bot, Database, FileText, HardDrive, Radio, ScrollText, User } from "lucide-react"
import type { Badge as Sev } from "@/lib/api"
import { type Flow, type FlowNode, type LeakPath, type Report } from "@/lib/api"
import { badgeChipClass, badgeColor } from "@/lib/format"
import { Card } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

const LEVEL_BADGE: Record<number, Sev> = { 4: "critical", 3: "high", 2: "medium", 1: "low" }

function levelColor(level: number): string {
  return level > 0 ? badgeColor(LEVEL_BADGE[level] ?? "low") : "hsl(var(--muted-foreground) / 0.45)"
}

const KIND_META: Record<string, { label: string; icon: typeof Bot }> = {
  user: { label: "User", icon: User },
  tool: { label: "Tool / data", icon: Database },
  agent: { label: "Agent", icon: Bot },
  memory: { label: "Memory", icon: HardDrive },
  log: { label: "Log", icon: ScrollText },
  file: { label: "File", icon: FileText },
  external: { label: "External", icon: Radio },
  output: { label: "Output", icon: ArrowRight },
}

// ---- agent topology diagram (hand-rolled SVG, deterministic 3-lane layout) ----
const W = 760
const NODE_W = 150
const NODE_H = 38
const VGAP = 18

function AgentDiagram({ flow }: { flow: Flow }) {
  const lanes = [0, 1, 2].map((l) => flow.nodes.filter((n) => n.lane === l))
  const laneX = [16, (W - NODE_W) / 2, W - NODE_W - 16]
  const rows = Math.max(1, ...lanes.map((l) => l.length))
  const H = rows * (NODE_H + VGAP) + 24

  const pos: Record<string, { x: number; y: number }> = {}
  lanes.forEach((ns, li) => {
    const laneH = ns.length * (NODE_H + VGAP) - VGAP
    const startY = (H - laneH) / 2
    ns.forEach((n, i) => {
      pos[n.id] = { x: laneX[li], y: startY + i * (NODE_H + VGAP) }
    })
  })

  function path(s: { x: number; y: number }, t: { x: number; y: number }) {
    const forward = t.x > s.x + 4
    const sx = forward ? s.x + NODE_W : s.x
    const tx = forward ? t.x : t.x + NODE_W
    const sy = s.y + NODE_H / 2
    const ty = t.y + NODE_H / 2
    if (Math.abs(t.x - s.x) < 4) {
      // same lane: bow out to the left so the arc clears the column
      const bow = s.x - 46
      return `M${s.x},${sy} C${bow},${sy} ${bow},${ty} ${t.x},${ty}`
    }
    const mx = (sx + tx) / 2
    return `M${sx},${sy} C${mx},${sy} ${mx},${ty} ${tx},${ty}`
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 420 }} role="img" aria-label="Agent topology">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="context-stroke" />
        </marker>
      </defs>
      {flow.edges.map((e, i) => {
        const s = pos[e.source]
        const t = pos[e.target]
        if (!s || !t) return null
        const color = levelColor(e.level)
        return (
          <path
            key={i}
            d={path(s, t)}
            fill="none"
            stroke={color}
            strokeWidth={e.leaked ? 2 : 1.25}
            strokeOpacity={e.leaked ? 0.95 : 0.5}
            markerEnd="url(#arrow)"
          >
            <title>{`${e.source} → ${e.target} · ${e.channel}${e.leaked ? ` · LEAK (${e.level_label})` : ""}`}</title>
          </path>
        )
      })}
      {flow.nodes.map((n) => {
        const p = pos[n.id]
        const leakInto = flow.edges.some((e) => e.target === n.id && e.leaked)
        return (
          <g key={n.id} transform={`translate(${p.x},${p.y})`}>
            <rect
              width={NODE_W}
              height={NODE_H}
              rx={8}
              className="fill-card"
              stroke={leakInto ? badgeColor("high") : "hsl(var(--border))"}
              strokeWidth={leakInto ? 1.5 : 1}
            />
            <text x={12} y={NODE_H / 2 + 1} dominantBaseline="middle" className="fill-muted-foreground" fontSize={9}>
              {(KIND_META[n.kind]?.label ?? n.kind).toUpperCase()}
            </text>
            <text x={12} y={NODE_H / 2 + 12} dominantBaseline="middle" className="fill-foreground" fontSize={12} fontWeight={500}>
              {n.id.length > 18 ? n.id.slice(0, 17) + "…" : n.id}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

// ---- per-secret propagation chain ----
function LeakPathCard({ path }: { path: LeakPath }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${badgeChipClass(LEVEL_BADGE[path.level] ?? "low")}`}>
          {path.level_label}
        </span>
        <span className="text-sm font-medium">{path.data_type}</span>
        <code className="font-mono text-xs text-muted-foreground">{path.value}</code>
        <span className="text-[11px] text-muted-foreground">
          · entered via <code className="font-mono">{path.entered_via ?? "unknown"}</code> · {path.leak_count} disclosure
          {path.leak_count === 1 ? "" : "s"}
          {path.agents.length > 0 && <> · agents {path.agents.join(", ")}</>}
        </span>
      </div>
      <div className="mt-2.5 flex flex-wrap items-center gap-x-1 gap-y-2">
        {path.steps.map((s, i) => (
          <div key={s.event_id + i} className="flex items-center gap-1">
            {i > 0 && <ArrowRight className="size-3 shrink-0 text-muted-foreground" />}
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] ${
                    s.kind === "leak" ? "border-transparent" : "border-border bg-muted/40"
                  }`}
                  style={
                    s.kind === "leak"
                      ? { background: `${levelColor(s.level)}1f`, color: levelColor(s.level) }
                      : undefined
                  }
                >
                  <span className="font-medium">{s.source || "?"}</span>
                  <span className="opacity-60">→</span>
                  <code className="font-mono">{s.channel}</code>
                </span>
              </TooltipTrigger>
              <TooltipContent>
                {s.kind === "source" ? "Entered here (source)" : `Disclosed (${s.level_label})`}: {s.source} → {s.target} on {s.channel}
              </TooltipContent>
            </Tooltip>
          </div>
        ))}
      </div>
    </div>
  )
}

function nodeKinds(nodes: FlowNode[]): string[] {
  return Array.from(new Set(nodes.map((n) => n.kind)))
}

export function FlowView({ report }: { report: Report }) {
  const flow = report.flow
  const paths = report.leak_paths ?? []

  if (!flow || flow.nodes.length === 0) {
    return (
      <Card className="p-10 text-center text-sm text-muted-foreground">
        No flow data for this run. Re-run it to capture the agent topology and leak paths.
      </Card>
    )
  }

  return (
    <div className="space-y-5">
      <Card>
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Agent topology — data flow
          </span>
          <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4" style={{ background: levelColor(4) }} /> leak
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4" style={{ background: levelColor(0) }} /> clean
            </span>
          </div>
        </div>
        <div className="p-4">
          <AgentDiagram flow={flow} />
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 px-1 text-[11px] text-muted-foreground">
            {nodeKinds(flow.nodes).map((k) => {
              const M = KIND_META[k]
              const Icon = M?.icon ?? Bot
              return (
                <span key={k} className="flex items-center gap-1">
                  <Icon className="size-3" /> {M?.label ?? k}
                </span>
              )
            })}
          </div>
        </div>
      </Card>

      <Card>
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Leak paths — where each secret came from
          </span>
          <span className="text-[11px] text-muted-foreground">{paths.length} traced</span>
        </div>
        <div className="space-y-3 p-4">
          {paths.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No secret was disclosed — nothing leaked across channels.
            </p>
          ) : (
            paths.map((p, i) => <LeakPathCard key={p.data_type + i} path={p} />)
          )}
        </div>
      </Card>
    </div>
  )
}
