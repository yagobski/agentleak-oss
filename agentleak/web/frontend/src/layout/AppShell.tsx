import { useEffect, useState } from "react"
import { NavLink, Outlet } from "react-router-dom"
import {
  FlaskConical,
  FolderKanban,
  LayoutDashboard,
  Library,
  ScanLine,
  Settings,
  ShieldCheck,
} from "lucide-react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import { ThemeToggle } from "@/features/ThemeToggle"

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/projects", label: "Projects", icon: FolderKanban, end: false },
  { to: "/playground", label: "Playground", icon: FlaskConical, end: false },
  { to: "/scenarios", label: "Scenarios", icon: Library, end: false },
  { to: "/settings", label: "Settings", icon: Settings, end: false },
]

export function AppShell() {
  const [version, setVersion] = useState("")
  useEffect(() => {
    api.meta().then((m) => setVersion(m.version)).catch(() => {})
  }, [])

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 flex h-screen w-16 shrink-0 flex-col border-r border-border bg-card/40 lg:w-60">
        <div className="flex h-14 items-center gap-2.5 px-4">
          <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary/15 text-primary">
            <ScanLine className="size-4" />
          </div>
          <span className="hidden text-[15px] font-semibold tracking-tight lg:inline">
            Agent<span className="text-primary">Leak</span>
          </span>
        </div>

        <nav className="flex-1 space-y-1 px-2 py-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  "lg:justify-start justify-center",
                  isActive
                    ? "bg-primary/12 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )
              }
            >
              <item.icon className="size-4 shrink-0" />
              <span className="hidden lg:inline">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="space-y-2 border-t border-border p-3">
          <div className="hidden items-center gap-1.5 px-1 text-[11px] text-muted-foreground lg:flex">
            <ShieldCheck className="size-3.5 text-sev-ok" /> 100% local
          </div>
          <div className="flex items-center justify-between">
            {version && <span className="hidden font-mono text-[11px] text-muted-foreground lg:inline">v{version}</span>}
            <ThemeToggle />
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-[1180px] px-5 py-6 lg:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: string
  actions?: React.ReactNode
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions}
    </div>
  )
}
