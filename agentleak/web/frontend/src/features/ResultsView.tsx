import { type ReactNode } from "react"
import { Download, FileJson, FileText, Lightbulb, ListChecks, ScrollText, ShieldAlert, ShieldCheck, Workflow } from "lucide-react"
import { toast } from "sonner"
import { api, type Report } from "@/lib/api"
import { badgeChipClass, badgeColor, download, keyInsight, LEVEL_META } from "@/lib/format"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { ComplianceView } from "./ComplianceView"
import { FlowView } from "./FlowView"
import { RiGauge } from "./RiGauge"

function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-md bg-muted/50 px-3.5 py-2.5">
      <div className="text-[11px] font-medium tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-lg tnum leading-none">{value}</div>
      {hint && <div className="mt-1 text-[11px] text-muted-foreground">{hint}</div>}
    </div>
  )
}

function TabCount({ n, tone }: { n: number; tone?: "danger" | "muted" }) {
  const cls =
    tone === "danger" && n > 0
      ? "bg-sev-l4/15 text-sev-l4"
      : "bg-muted text-muted-foreground"
  return <span className={`ml-1 rounded px-1.5 py-0.5 text-[10px] tnum ${cls}`}>{n}</span>
}

export function ResultsView({ report }: { report: Report }) {
  const insight = keyInsight(report)
  const maxRi = Math.max(...report.channel_risks.map((c) => c.ri), 0.0001)
  const atRisk = report.compliance?.summary.controls_at_risk ?? 0
  const leakPaths = report.leak_paths?.length ?? 0
  const hasFlow = (report.flow?.nodes.length ?? 0) > 0

  async function onExport(fmt: "json" | "html" | "markdown") {
    try {
      if (fmt === "json") {
        download(`${report.run_id}.json`, JSON.stringify(report, null, 2), "application/json")
      } else {
        const text = await api.render(fmt, report)
        const ext = fmt === "markdown" ? "md" : "html"
        download(`${report.run_id}.${ext}`, text, fmt === "html" ? "text/html" : "text/markdown")
      }
      toast.success(`Exported ${report.run_id}.${fmt === "markdown" ? "md" : fmt}`)
    } catch (e) {
      toast.error(`Export failed: ${(e as Error).message}`)
    }
  }

  return (
    <div className="animate-fade-up space-y-5">
      {/* header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-mono text-sm">{report.agent_name}</div>
          <div className="text-xs text-muted-foreground">
            run <span className="text-foreground">{report.run_id}</span> · {report.event_count} events
            {report.scenario_id ? <> · {report.scenario_id}</> : null}
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <Button variant="outline" size="sm" onClick={() => onExport("json")}>
            <FileJson /> JSON
          </Button>
          <Button variant="outline" size="sm" onClick={() => onExport("markdown")}>
            <FileText /> MD
          </Button>
          <Button variant="outline" size="sm" onClick={() => onExport("html")}>
            <Download /> HTML
          </Button>
        </div>
      </div>

      {/* hero: gauge + headline stats (always visible) */}
      <Card className="overflow-hidden">
        <div className="grid gap-6 p-5 md:grid-cols-[260px_1fr]">
          <div className="flex items-center justify-center border-b border-border pb-4 md:border-b-0 md:border-r md:pb-0 md:pr-6">
            <RiGauge report={report} />
          </div>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              <Stat label="WSL" value={report.wsl} hint="weighted leakage" />
              <Stat label="ρ_S" value={report.rho_s} hint="vault density" />
              <Stat
                label="Leaked"
                value={`${report.summary.leaked_secrets}/${report.summary.vault_secrets}`}
                hint="secrets in scope"
              />
              <Stat label="Findings" value={report.summary.total_findings} hint="disclosures" />
            </div>
            <div>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-x-3">
                <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                  Leaked by severity level
                </span>
                <span className="text-[11px] text-muted-foreground">{report.scope_def}</span>
              </div>
              <div className="grid grid-cols-4 gap-2">
                {LEVEL_META.map((l) => {
                  const n = report.summary.level_profile[l.label as "L4"] ?? 0
                  const vault = report.summary.vault_level_profile[l.label as "L4"] ?? 0
                  return (
                    <Tooltip key={l.label}>
                      <TooltipTrigger asChild>
                        <div className="rounded-md border border-border bg-card px-3 py-2">
                          <div className="font-mono text-xl tnum leading-none" style={{ color: badgeColor(l.badge) }}>
                            {n}
                          </div>
                          <div className="mt-1 flex items-center justify-between text-[11px] text-muted-foreground">
                            <span>{l.label}</span>
                            <span className="tnum">/{vault}</span>
                          </div>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        {l.name} — {n} leaked of {vault} in scope
                      </TooltipContent>
                    </Tooltip>
                  )
                })}
              </div>
            </div>
            {report.blocked && (
              <div className="flex items-center gap-2 rounded-md border border-sev-l4/30 bg-sev-l4/10 px-3 py-2 text-sm text-sev-l4">
                <ShieldAlert className="size-4 shrink-0" />
                Blocked — this run would fail a CI privacy gate.
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* detail tabs */}
      <Tabs defaultValue="overview">
        <TabsList className="flex h-auto w-full flex-wrap justify-start">
          <TabsTrigger value="overview">
            <ScrollText className="size-3.5" /> Overview
          </TabsTrigger>
          {hasFlow && (
            <TabsTrigger value="flow">
              <Workflow className="size-3.5" /> Leak flow
              <TabCount n={leakPaths} tone="danger" />
            </TabsTrigger>
          )}
          <TabsTrigger value="findings">
            <ListChecks className="size-3.5" /> Findings
            <TabCount n={report.findings.length} tone="danger" />
          </TabsTrigger>
          <TabsTrigger value="recommendations">
            <Lightbulb className="size-3.5" /> Recommendations
            <TabCount n={report.recommendations.length} tone="muted" />
          </TabsTrigger>
          {report.compliance && (
            <TabsTrigger value="compliance">
              {atRisk > 0 ? <ShieldAlert className="size-3.5" /> : <ShieldCheck className="size-3.5" />} Compliance
              <TabCount n={atRisk} tone="danger" />
            </TabsTrigger>
          )}
        </TabsList>

        {/* Overview: key insight + risk by channel */}
        <TabsContent value="overview" className="space-y-5">
          {insight && (
            <Card className="border-primary/30 bg-primary/[0.06]">
              <div className="flex gap-3 p-4">
                <Lightbulb className="mt-0.5 size-4 shrink-0 text-primary" />
                <p className="text-sm leading-relaxed">
                  <span className="font-semibold text-primary">Key insight. </span>
                  {insight}
                </p>
              </div>
            </Card>
          )}
          <Card>
            <div className="border-b border-border px-5 py-3">
              <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Risk by channel
              </span>
            </div>
            <div className="divide-y divide-border">
              {report.channel_risks.length === 0 && (
                <div className="px-5 py-6 text-sm text-muted-foreground">No leaks detected in any channel.</div>
              )}
              {report.channel_risks.map((c) => (
                <div key={c.channel} className="grid grid-cols-[1fr_auto] items-center gap-4 px-5 py-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2.5">
                      <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${badgeChipClass(c.level)}`}>
                        {c.level_label}
                      </span>
                      <code className="truncate font-mono text-[13px]">{c.channel}</code>
                      <span className="text-[11px] text-muted-foreground">{c.finding_count} finding(s)</span>
                    </div>
                    <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        key={`${report.run_id}-${c.channel}`}
                        className="bar-grow h-full rounded-full"
                        style={{ width: `${(c.ri / maxRi) * 100}%`, backgroundColor: badgeColor(c.level) }}
                      />
                    </div>
                  </div>
                  <div className="font-mono text-sm tnum text-muted-foreground">{c.ri.toFixed(3)}</div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        {/* Leak flow — topology + propagation paths */}
        {hasFlow && (
          <TabsContent value="flow">
            <FlowView report={report} />
          </TabsContent>
        )}

        {/* Findings */}
        <TabsContent value="findings">
          <Card>
            <div className="flex items-center justify-between border-b border-border px-5 py-3">
              <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Findings — leaked secrets by channel
              </span>
              <Badge variant="muted">{report.findings.length}</Badge>
            </div>
            <ScrollArea className="max-h-[520px]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-card">
                  <tr className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-2 font-medium">Level</th>
                    <th className="px-3 py-2 font-medium">Channel</th>
                    <th className="px-3 py-2 font-medium">Type</th>
                    <th className="px-3 py-2 font-medium">Value</th>
                    <th className="px-5 py-2 font-medium">Detector</th>
                  </tr>
                </thead>
                <tbody>
                  {report.findings.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-5 py-10 text-center text-muted-foreground">
                        No leaks detected. 🎉
                      </td>
                    </tr>
                  )}
                  {report.findings.map((f) => (
                    <Tooltip key={f.finding_id}>
                      <TooltipTrigger asChild>
                        <tr className="border-t border-border transition-colors hover:bg-muted/40">
                          <td className="px-5 py-2.5">
                            <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${badgeChipClass(f.badge)}`}>
                              {f.level_label}
                            </span>
                          </td>
                          <td className="px-3 py-2.5">
                            <code className="font-mono text-[12px] text-muted-foreground">{f.channel}</code>
                          </td>
                          <td className="px-3 py-2.5">{f.data_type}</td>
                          <td className="px-3 py-2.5">
                            <code className="font-mono text-[12px]">{f.redacted_value || f.matched_value}</code>
                          </td>
                          <td className="px-5 py-2.5 text-[12px] text-muted-foreground">{f.detector}</td>
                        </tr>
                      </TooltipTrigger>
                      <TooltipContent side="left">{f.recommendation}</TooltipContent>
                    </Tooltip>
                  ))}
                </tbody>
              </table>
            </ScrollArea>
          </Card>
        </TabsContent>

        {/* Recommendations */}
        <TabsContent value="recommendations">
          <Card>
            <div className="border-b border-border px-5 py-3">
              <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Recommendations
              </span>
            </div>
            {report.recommendations.length === 0 ? (
              <div className="px-5 py-10 text-center text-sm text-muted-foreground">
                No recommendations — nothing leaked.
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {report.recommendations.map((r, i) => (
                  <li key={i} className="flex gap-2.5 px-5 py-3 text-sm">
                    <span className="select-none font-mono text-primary">→</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </TabsContent>

        {/* Compliance */}
        {report.compliance && (
          <TabsContent value="compliance">
            <ComplianceView compliance={report.compliance} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}
