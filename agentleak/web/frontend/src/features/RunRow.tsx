import type { ReactNode } from "react"
import type { RunSummary } from "@/lib/api"
import { verdictColor } from "@/lib/format"

export function timeAgo(epochSeconds: number): string {
  const s = Math.max(1, Math.floor(Date.now() / 1000 - epochSeconds))
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

export function VerdictChip({ verdict, ri }: { verdict: RunSummary["verdict"]; ri?: number }) {
  const c = verdictColor(verdict)
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={{ color: c, backgroundColor: `${c}1f` }}
    >
      {verdict}
      {ri != null && <span className="font-mono tnum opacity-80">{ri.toFixed(3)}</span>}
    </span>
  )
}

export function RunRow({ run, onClick, right }: { run: RunSummary; onClick?: () => void; right?: ReactNode }) {
  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-3 px-5 py-3 ${onClick ? "cursor-pointer transition-colors hover:bg-accent/50" : ""}`}
    >
      <VerdictChip verdict={run.verdict} ri={run.risk_index} />
      <div className="min-w-0 flex-1">
        <div className="truncate font-mono text-[13px]">{run.agent_name || "agent"}</div>
        <div className="text-[11px] text-muted-foreground">
          {run.leaked_secrets} leaked · {run.source} · {timeAgo(run.created_at)}
        </div>
      </div>
      {run.blocked && (
        <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-sev-l4 ring-1 ring-inset ring-sev-l4/25">
          blocked
        </span>
      )}
      {right}
    </div>
  )
}
