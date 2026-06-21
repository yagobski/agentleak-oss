import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { ScanLine } from "lucide-react"
import { toast } from "sonner"
import { api, type AnalyzePayload, type Report, type Scenario } from "@/lib/api"
import { Card } from "@/components/ui/card"
import { ConfigPanel } from "@/features/ConfigPanel"
import { ResultsView } from "@/features/ResultsView"
import { PageHeader } from "@/layout/AppShell"

export function Playground() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(false)
  const [params] = useSearchParams()
  const initialScenarioId = params.get("scenario") ?? undefined

  useEffect(() => {
    api.scenarios().then(setScenarios).catch((e) => toast.error(`Failed to load scenarios: ${e.message}`))
  }, [])

  async function onAnalyze(payload: AnalyzePayload) {
    setLoading(true)
    try {
      setReport(await api.analyze(payload))
    } catch (e) {
      toast.error(`Analysis failed: ${(e as Error).message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="animate-fade-up">
      <PageHeader title="Playground" description="Score any trace instantly — nothing is saved." />
      <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
        <Card className="lg:sticky lg:top-6 lg:h-[calc(100vh-7rem)] lg:overflow-hidden">
          <ConfigPanel
            scenarios={scenarios}
            loading={loading}
            onAnalyze={onAnalyze}
            initialScenarioId={initialScenarioId}
          />
        </Card>
        <div className="min-w-0">
          {report ? (
            <ResultsView report={report} />
          ) : (
            <div className="flex min-h-[420px] flex-col items-center justify-center rounded-lg border border-dashed border-border p-10 text-center">
              <div className="relative mb-4 flex size-14 items-center justify-center overflow-hidden rounded-xl border border-border bg-card">
                <ScanLine className="size-6 text-primary" />
                <div className="pointer-events-none absolute inset-0 animate-scan bg-gradient-to-b from-transparent via-primary/20 to-transparent" />
              </div>
              <p className="max-w-sm text-sm text-muted-foreground">
                Pick a scenario or paste a trace, then click Analyze.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
