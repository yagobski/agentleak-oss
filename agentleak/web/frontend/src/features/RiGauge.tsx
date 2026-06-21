import type { Report } from "@/lib/api"
import { verdictColor } from "@/lib/format"

// 270° gauge, opening at the bottom. Center (110,110), radius 90.
const CX = 110
const CY = 110
const R = 90
const START = 135 // degrees
const SWEEP = 270
const ARC_LEN = (2 * Math.PI * R * SWEEP) / 360

function polar(angleDeg: number) {
  const a = (angleDeg * Math.PI) / 180
  return { x: CX + R * Math.cos(a), y: CY + R * Math.sin(a) }
}

const start = polar(START)
const end = polar(START + SWEEP)
const ARC = `M ${start.x} ${start.y} A ${R} ${R} 0 1 1 ${end.x} ${end.y}`

export function RiGauge({ report }: { report: Report }) {
  const color = verdictColor(report.verdict)
  // Rendered offset is always the FINAL value; the .arc-draw keyframe animates
  // in from the full (hidden) length. The keyed element replays on each run.
  const offset = ARC_LEN * (1 - report.risk_index)

  return (
    <div className="relative flex flex-col items-center">
      <svg viewBox="0 0 220 200" className="w-[230px]" role="img" aria-label={`Risk Index ${report.risk_index}`}>
        <path d={ARC} fill="none" stroke="hsl(var(--muted))" strokeWidth={13} strokeLinecap="round" />
        <path
          key={`${report.run_id}-${report.risk_index}`}
          className="arc-draw"
          d={ARC}
          fill="none"
          stroke={color}
          strokeWidth={13}
          strokeLinecap="round"
          strokeDasharray={ARC_LEN}
          strokeDashoffset={offset}
          style={{ ["--arc-len" as string]: `${ARC_LEN}`, filter: `drop-shadow(0 0 9px ${color}55)` }}
        />
        {[0, 0.25, 0.5, 0.75, 1].map((q) => {
          const ang = ((START + SWEEP * q) * Math.PI) / 180
          const p = polar(START + SWEEP * q)
          return (
            <line
              key={q}
              x1={p.x}
              y1={p.y}
              x2={CX + (R - 16) * Math.cos(ang)}
              y2={CY + (R - 16) * Math.sin(ang)}
              stroke="hsl(var(--border))"
              strokeWidth={1.5}
            />
          )
        })}
        <text x={CX} y={96} textAnchor="middle" className="fill-muted-foreground" style={{ fontSize: 10, letterSpacing: "0.16em" }}>
          RISK INDEX
        </text>
        <text x={CX} y={138} textAnchor="middle" className="font-mono tnum" style={{ fontSize: 46, fontWeight: 600, fill: color }}>
          {report.risk_index.toFixed(3)}
        </text>
      </svg>
      <div className="-mt-3 flex flex-col items-center gap-1.5">
        <span className="rounded-full px-3 py-1 text-sm font-semibold" style={{ color, backgroundColor: `${color}1f` }}>
          {report.verdict}
        </span>
        <span className="text-xs text-muted-foreground">
          privacy score <span className="tnum text-foreground">{report.privacy_score}</span>/100
        </span>
      </div>
    </div>
  )
}
