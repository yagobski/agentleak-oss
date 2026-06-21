import { useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { ArrowLeft, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { api, type Run } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { ResultsView } from "@/features/ResultsView"
import { timeAgo } from "@/features/RunRow"

export function RunView() {
  const { id } = useParams()
  const nav = useNavigate()
  const [run, setRun] = useState<Run | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!id) return
    api.run(id).then(setRun).catch((e) => setError(e.message))
  }, [id])

  async function remove() {
    if (!run) return
    try {
      await api.deleteRun(run.id)
      toast.success("Run deleted")
      nav(run.project_id ? `/projects/${run.project_id}` : "/")
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  if (error) return <div className="animate-fade-up text-sm text-sev-l4">Run not found.</div>
  if (!run) return <div className="animate-fade-up text-sm text-muted-foreground">Loading…</div>

  return (
    <div className="animate-fade-up">
      <div className="mb-5 flex items-center justify-between gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/projects/${run.project_id}`}>
            <ArrowLeft /> Back to project
          </Link>
        </Button>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">{run.source} · {timeAgo(run.created_at)}</span>
          <Button variant="ghost" size="sm" className="text-sev-l4" onClick={remove}>
            <Trash2 /> Delete
          </Button>
        </div>
      </div>
      <ResultsView report={run.report} />
    </div>
  )
}
