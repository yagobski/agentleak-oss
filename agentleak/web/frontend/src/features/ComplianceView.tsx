import { AlertTriangle, CheckCircle2, ExternalLink, Info, ShieldCheck } from "lucide-react"
import type { Compliance, ControlResult } from "@/lib/api"
import { Card } from "@/components/ui/card"

function StatusIcon({ status }: { status: ControlResult["status"] }) {
  if (status === "at_risk") return <AlertTriangle className="size-4 shrink-0 text-sev-l4" />
  if (status === "info") return <Info className="size-4 shrink-0 text-primary" />
  return <CheckCircle2 className="size-4 shrink-0 text-sev-ok" />
}

export function ComplianceView({ compliance }: { compliance: Compliance }) {
  if (!compliance?.frameworks?.length) return null
  const s = compliance.summary
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Compliance
        </span>
        <span className="text-xs text-muted-foreground">
          {s.compliant}/{s.total} frameworks clear · {s.controls_at_risk} control(s) at risk
        </span>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {compliance.frameworks.map((fw) => {
          const ok = fw.status === "compliant"
          return (
            <Card key={fw.id} className="overflow-hidden">
              <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-2.5">
                <a
                  href={fw.url}
                  target="_blank"
                  rel="noreferrer"
                  className="group flex items-center gap-1.5 text-sm font-medium hover:text-primary"
                >
                  {fw.name}
                  <ExternalLink className="size-3 opacity-0 transition-opacity group-hover:opacity-60" />
                </a>
                <span
                  className="flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium"
                  style={
                    ok
                      ? { color: "hsl(var(--sev-ok))", backgroundColor: "hsl(var(--sev-ok) / 0.14)" }
                      : { color: "hsl(var(--sev-l4))", backgroundColor: "hsl(var(--sev-l4) / 0.14)" }
                  }
                >
                  {ok ? <ShieldCheck className="size-3" /> : <AlertTriangle className="size-3" />}
                  {ok ? "Clear" : `${fw.at_risk} at risk`}
                </span>
              </div>
              <ul className="divide-y divide-border">
                {fw.controls.map((ctrl) => (
                  <li key={ctrl.id} className="flex gap-2.5 px-4 py-2.5">
                    <StatusIcon status={ctrl.status} />
                    <div className="min-w-0">
                      <div className="text-[13px] font-medium leading-tight">{ctrl.name}</div>
                      <div className="mt-0.5 text-[11px] text-muted-foreground">{ctrl.rationale}</div>
                      {ctrl.evidence.length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {ctrl.evidence.slice(0, 6).map((e, i) => (
                            <code
                              key={i}
                              className="rounded bg-sev-l4/10 px-1.5 py-0.5 text-[10px] text-sev-l4"
                            >
                              {e}
                            </code>
                          ))}
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
