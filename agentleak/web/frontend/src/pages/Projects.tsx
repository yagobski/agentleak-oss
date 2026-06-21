import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Bot, Plus } from "lucide-react"
import { toast } from "sonner"
import { api, type Project } from "@/lib/api"
import { agentLabel } from "@/lib/agents"
import { useAgentTypes } from "@/lib/hooks"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { PageHeader } from "@/layout/AppShell"
import { riVerdict, verdictColor } from "@/lib/format"

function NewProjectDialog({ onCreated }: { onCreated: (p: Project) => void }) {
  const agentTypes = useAgentTypes()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [agentType, setAgentType] = useState("generic")
  const [description, setDescription] = useState("")
  const [busy, setBusy] = useState(false)

  async function submit() {
    if (!name.trim()) return toast.error("Project name is required")
    setBusy(true)
    try {
      const p = await api.createProject({ name: name.trim(), agent_type: agentType, description })
      toast.success(`Created “${p.name}”`)
      setOpen(false)
      setName("")
      setDescription("")
      onCreated(p)
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> New project
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New project</DialogTitle>
          <DialogDescription>A project is an agent under test. Connect it via the SDK after creating.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="support-bot" autoFocus />
          </div>
          <div className="space-y-1.5">
            <Label>Agent framework</Label>
            <Select value={agentType} onValueChange={setAgentType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {agentTypes.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Description (optional)</Label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} className="min-h-[60px]" />
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <DialogClose asChild>
            <Button variant="ghost">Cancel</Button>
          </DialogClose>
          <Button onClick={submit} disabled={busy}>
            Create project
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function Projects() {
  const [projects, setProjects] = useState<Project[]>([])
  const nav = useNavigate()
  const load = () => api.projects().then(setProjects).catch(() => {})
  useEffect(() => {
    load()
  }, [])

  return (
    <div className="animate-fade-up">
      <PageHeader
        title="Projects"
        description="Each project is an agent you audit over time."
        actions={<NewProjectDialog onCreated={(p) => nav(`/projects/${p.id}`)} />}
      />

      {!projects.length ? (
        <Card className="flex flex-col items-center justify-center gap-3 p-12 text-center">
          <Bot className="size-8 text-muted-foreground" />
          <div>
            <div className="font-medium">No projects yet</div>
            <p className="mt-1 text-sm text-muted-foreground">Create one to connect an agent and track its privacy over time.</p>
          </div>
          <NewProjectDialog onCreated={(p) => nav(`/projects/${p.id}`)} />
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`}>
              <Card className="h-full p-4 transition-colors hover:border-primary/40">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium">{p.name}</span>
                  <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                    {agentLabel(p.agent_type)}
                  </span>
                </div>
                {p.description && <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{p.description}</p>}
                <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
                  <span>{p.run_count ?? 0} runs</span>
                  {p.avg_risk_index != null ? (
                    <span className="font-mono tnum" style={{ color: verdictColor(riVerdict(p.avg_risk_index)) }}>
                      avg RI {p.avg_risk_index.toFixed(3)}
                    </span>
                  ) : (
                    <span>no runs yet</span>
                  )}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
