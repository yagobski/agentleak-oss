import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowRight, FlaskConical, FolderKanban, ShieldAlert } from "lucide-react"
import { api, type Project, type Stats } from "@/lib/api"
import { riVerdict, verdictColor } from "@/lib/format"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { PageHeader } from "@/layout/AppShell"
import { DashboardCharts } from "@/features/Charts"
import { RunRow } from "@/features/RunRow"

function Metric({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <Card className="p-4">
      <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1.5 font-mono text-2xl tnum leading-none">{value}</div>
      {sub && <div className="mt-1 text-[11px] text-muted-foreground">{sub}</div>}
    </Card>
  )
}

export function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const nav = useNavigate()

  useEffect(() => {
    api.stats().then(setStats).catch(() => {})
    api.projects().then(setProjects).catch(() => {})
  }, [])

  const avg = stats?.avg_risk_index
  return (
    <div className="animate-fade-up">
      <PageHeader
        title="Dashboard"
        description="Privacy posture across your agents, scored with AgentRisk."
        actions={
          <Button asChild>
            <Link to="/projects">
              <FolderKanban /> Projects
            </Link>
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric label="Projects" value={stats?.projects ?? "—"} />
        <Metric label="Runs" value={stats?.runs ?? "—"} />
        <Metric
          label="Avg Risk Index"
          value={avg != null ? avg.toFixed(3) : "—"}
          sub={avg != null ? "across all runs" : undefined}
        />
        <Metric label="Blocked runs" value={stats?.blocked_runs ?? "—"} sub="would fail CI" />
      </div>

      {stats && stats.recent_runs.length > 0 && (
        <div className="mt-5">
          <DashboardCharts runs={stats.recent_runs} />
        </div>
      )}

      <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_320px]">
        <Card>
          <div className="flex items-center justify-between border-b border-border px-5 py-3">
            <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Recent runs
            </span>
          </div>
          <div className="divide-y divide-border">
            {!stats?.recent_runs.length && (
              <div className="px-5 py-10 text-center text-sm text-muted-foreground">
                No runs yet. Create a project and connect an agent, or try the{" "}
                <Link to="/playground" className="text-primary underline-offset-2 hover:underline">
                  playground
                </Link>
                .
              </div>
            )}
            {stats?.recent_runs.map((r) => (
              <RunRow key={r.id} run={r} onClick={() => nav(`/runs/${r.id}`)} />
            ))}
          </div>
        </Card>

        <div className="space-y-5">
          <Card className="p-5">
            <div className="flex items-center gap-2 text-sm font-medium">
              <FlaskConical className="size-4 text-primary" /> Quick audit
            </div>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Score a trace instantly without creating a project.
            </p>
            <Button variant="outline" size="sm" className="mt-3 w-full" asChild>
              <Link to="/playground">
                Open playground <ArrowRight />
              </Link>
            </Button>
          </Card>

          <Card className="p-5">
            <div className="flex items-center gap-2 text-sm font-medium">
              <ShieldAlert className="size-4 text-sev-l3" /> Projects
            </div>
            <div className="mt-3 space-y-1.5">
              {projects.slice(0, 4).map((p) => (
                <Link
                  key={p.id}
                  to={`/projects/${p.id}`}
                  className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent"
                >
                  <span className="truncate">{p.name}</span>
                  {p.avg_risk_index != null && (
                    <span className="font-mono text-xs tnum" style={{ color: verdictColor(riVerdict(p.avg_risk_index)) }}>
                      {p.avg_risk_index.toFixed(2)}
                    </span>
                  )}
                </Link>
              ))}
              {!projects.length && <p className="text-sm text-muted-foreground">No projects yet.</p>}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
