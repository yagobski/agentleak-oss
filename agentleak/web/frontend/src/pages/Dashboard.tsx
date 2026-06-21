import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Activity, ArrowRight, FlaskConical, FolderKanban, Gauge, ShieldAlert, ShieldCheck } from "lucide-react"
import { api, type Project, type Stats } from "@/lib/api"
import { riVerdict, verdictColor } from "@/lib/format"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { PageHeader } from "@/layout/AppShell"
import { DashboardCharts } from "@/features/Charts"
import { RunRow } from "@/features/RunRow"

function SectionCard({
  label,
  value,
  icon,
  footer,
  sub,
}: {
  label: string
  value: React.ReactNode
  icon: React.ReactNode
  footer: React.ReactNode
  sub?: string
}) {
  return (
    <Card>
      <CardHeader className="relative space-y-0 p-4 pb-2">
        <CardDescription className="text-[11px] font-medium uppercase tracking-wide">{label}</CardDescription>
        <CardTitle className="font-mono text-3xl tabular-nums tnum">{value}</CardTitle>
        <div className="absolute right-4 top-4 text-muted-foreground/70">{icon}</div>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        <div className="text-sm font-medium">{footer}</div>
        {sub && <div className="mt-0.5 text-xs text-muted-foreground">{sub}</div>}
      </CardContent>
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
  const avgVerdict = avg != null ? riVerdict(avg) : null

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

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SectionCard
          label="Projects"
          value={stats?.projects ?? "—"}
          icon={<FolderKanban className="size-4" />}
          footer="Agents under test"
          sub="each scored independently"
        />
        <SectionCard
          label="Runs"
          value={stats?.runs ?? "—"}
          icon={<Activity className="size-4" />}
          footer="Analyses stored"
          sub="locally, in SQLite"
        />
        <SectionCard
          label="Avg Risk Index"
          value={avg != null ? avg.toFixed(3) : "—"}
          icon={<Gauge className="size-4" />}
          footer={
            avgVerdict ? <span style={{ color: verdictColor(avgVerdict) }}>{avgVerdict}</span> : "No runs yet"
          }
          sub="across all runs"
        />
        <SectionCard
          label="Blocked runs"
          value={stats?.blocked_runs ?? "—"}
          icon={
            stats && stats.blocked_runs > 0 ? (
              <ShieldAlert className="size-4 text-sev-l4" />
            ) : (
              <ShieldCheck className="size-4 text-sev-ok" />
            )
          }
          footer="Would fail a CI gate"
          sub="blocked = critical leak"
        />
      </div>

      {stats && stats.recent_runs.length > 0 && (
        <div className="mt-4">
          <DashboardCharts runs={stats.recent_runs} />
        </div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_320px]">
        <Card>
          <div className="flex items-center justify-between border-b border-border px-5 py-3">
            <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Recent runs
            </span>
            {stats && stats.recent_runs.length > 0 && <Badge variant="muted">{stats.recent_runs.length}</Badge>}
          </div>
          <div className="divide-y divide-border">
            {!stats?.recent_runs.length && (
              <div className="px-5 py-10 text-center text-sm text-muted-foreground">
                No runs yet. Create a project and run an agent, or try the{" "}
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

        <div className="space-y-4">
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
                    <span
                      className="font-mono text-xs tnum"
                      style={{ color: verdictColor(riVerdict(p.avg_risk_index)) }}
                    >
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
