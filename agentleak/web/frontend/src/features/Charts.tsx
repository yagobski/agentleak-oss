import type { RunSummary } from "@/lib/api"
import { verdictColor } from "@/lib/format"
import { Card } from "@/components/ui/card"

const VERDICTS: RunSummary["verdict"][] = ["Pass", "Conditional pass", "High risk", "Fail"]

function RiTrend({ runs }: { runs: RunSummary[] }) {
  const series = [...runs].reverse() // chronological
  const W = 460
  const H = 120
  const pad = { l: 28, r: 8, t: 10, b: 18 }
  const iw = W - pad.l - pad.r
  const ih = H - pad.t - pad.b
  const n = series.length
  const x = (i: number) => pad.l + (n <= 1 ? iw / 2 : (i / (n - 1)) * iw)
  const y = (ri: number) => pad.t + (1 - Math.min(1, Math.max(0, ri))) * ih
  const line = series.map((r, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(r.risk_index).toFixed(1)}`).join(" ")

  return (
    <Card className="p-4">
      <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Risk Index — recent runs
      </div>
      {n === 0 ? (
        <div className="flex h-[120px] items-center justify-center text-xs text-muted-foreground">No runs yet</div>
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Risk Index over recent runs">
          {[0, 0.5, 1].map((g) => (
            <g key={g}>
              <line x1={pad.l} x2={W - pad.r} y1={y(g)} y2={y(g)} stroke="hsl(var(--border))" strokeWidth={1} />
              <text x={pad.l - 6} y={y(g) + 3} textAnchor="end" className="fill-muted-foreground" style={{ fontSize: 9 }}>
                {g}
              </text>
            </g>
          ))}
          <path d={line} fill="none" stroke="hsl(var(--primary))" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          {series.map((r, i) => (
            <circle key={r.id} cx={x(i)} cy={y(r.risk_index)} r={3} fill={verdictColor(r.verdict)} />
          ))}
        </svg>
      )}
    </Card>
  )
}

function VerdictBars({ runs }: { runs: RunSummary[] }) {
  const counts = VERDICTS.map((v) => ({ v, n: runs.filter((r) => r.verdict === v).length }))
  const max = Math.max(1, ...counts.map((c) => c.n))
  return (
    <Card className="p-4">
      <div className="mb-3 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Verdict distribution
      </div>
      <div className="space-y-2">
        {counts.map(({ v, n }) => (
          <div key={v} className="flex items-center gap-2.5 text-xs">
            <span className="w-28 shrink-0 text-muted-foreground">{v}</span>
            <div className="h-3 flex-1 overflow-hidden rounded-sm bg-muted">
              <div
                className="bar-grow h-full rounded-sm"
                style={{ width: `${(n / max) * 100}%`, backgroundColor: verdictColor(v) }}
              />
            </div>
            <span className="w-5 text-right font-mono tnum">{n}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}

export function DashboardCharts({ runs }: { runs: RunSummary[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <RiTrend runs={runs} />
      <VerdictBars runs={runs} />
    </div>
  )
}
