import { useEffect, useState } from "react"
import { Link, NavLink, Outlet, useLocation } from "react-router-dom"
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
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { ThemeToggle } from "@/features/ThemeToggle"

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/projects", label: "Projects", icon: FolderKanban, end: false },
  { to: "/playground", label: "Playground", icon: FlaskConical, end: false },
  { to: "/scenarios", label: "Scenarios", icon: Library, end: false },
]

function isActivePath(pathname: string, to: string, end: boolean): boolean {
  return end ? pathname === to : pathname === to || pathname.startsWith(`${to}/`)
}

function sectionFor(pathname: string): { label: string; to: string } {
  const all = [...NAV, { to: "/settings", label: "Settings", icon: Settings, end: false }]
  const match = all.find((n) => isActivePath(pathname, n.to, n.to === "/"))
  return match ? { label: match.label, to: match.to } : { label: "Dashboard", to: "/" }
}

function AppSidebar() {
  const { pathname } = useLocation()
  const [version, setVersion] = useState("")
  useEffect(() => {
    api.meta().then((m) => setVersion(m.version)).catch(() => {})
  }, [])

  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild className="data-[slot=sidebar-menu-button]:!p-1.5">
              <Link to="/">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary/15 text-primary">
                  <ScanLine className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">
                    Agent<span className="text-primary">Leak</span>
                  </span>
                  <span className="truncate text-xs text-muted-foreground">Privacy auditor</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Platform</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV.map((item) => (
                <SidebarMenuItem key={item.to}>
                  <SidebarMenuButton asChild isActive={isActivePath(pathname, item.to, item.end)} tooltip={item.label}>
                    <NavLink to={item.to} end={item.end}>
                      <item.icon />
                      <span>{item.label}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild isActive={isActivePath(pathname, "/settings", false)} tooltip="Settings">
              <NavLink to="/settings">
                <Settings />
                <span>Settings</span>
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <div className="flex items-center justify-between gap-2 px-2 py-1.5 text-[11px] text-muted-foreground group-data-[collapsible=icon]:hidden">
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="size-3.5 text-sev-ok" /> 100% local
              </span>
              {version && <span className="font-mono">v{version}</span>}
            </div>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}

function SiteHeader() {
  const { pathname } = useLocation()
  const section = sectionFor(pathname)
  const isDetail = pathname !== section.to && pathname !== "/"

  return (
    <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="flex w-full items-center gap-2 px-4 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="mr-1 h-4" />
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem className="hidden sm:block">
              <BreadcrumbLink asChild>
                <Link to="/">AgentLeak</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator className="hidden sm:block" />
            <BreadcrumbItem>
              {isDetail ? (
                <BreadcrumbLink asChild>
                  <Link to={section.to}>{section.label}</Link>
                </BreadcrumbLink>
              ) : (
                <BreadcrumbPage>{section.label}</BreadcrumbPage>
              )}
            </BreadcrumbItem>
            {isDetail && (
              <>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage>Detail</BreadcrumbPage>
                </BreadcrumbItem>
              </>
            )}
          </BreadcrumbList>
        </Breadcrumb>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}

export function AppShell() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex flex-1 flex-col gap-4 p-4 lg:p-6">
          <div className="mx-auto w-full max-w-[1180px]">
            <Outlet />
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
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
