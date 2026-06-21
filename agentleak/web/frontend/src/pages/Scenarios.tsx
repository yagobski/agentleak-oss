import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { FlaskConical } from "lucide-react"
import { api, type Scenario } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { PageHeader } from "@/layout/AppShell"

export function Scenarios() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  useEffect(() => {
    api.scenarios().then(setScenarios).catch(() => {})
  }, [])

  return (
    <div className="animate-fade-up">
      <PageHeader
        title="Scenarios"
        description="Built-in synthetic scenarios across regulated domains. All data is fictional."
        actions={
          <Button variant="outline" asChild>
            <Link to="/playground">
              <FlaskConical /> Open playground
            </Link>
          </Button>
        }
      />
      <div className="grid gap-3 md:grid-cols-2">
        {scenarios.map((s) => (
          <Card key={s.id} className="p-4">
            <div className="flex items-center justify-between gap-2">
              <code className="font-mono text-sm text-primary">{s.id}</code>
              <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                {s.domain}
              </span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{s.description}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {s.sensitive_data.map((d) => (
                <span key={d} className="rounded-full bg-secondary px-2 py-0.5 text-[11px] text-secondary-foreground">
                  {d}
                </span>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
