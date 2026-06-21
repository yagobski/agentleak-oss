import { useEffect, useState } from "react"
import { ExternalLink, Github, ShieldCheck } from "lucide-react"
import { api, type Meta } from "@/lib/api"
import { Card } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { PageHeader } from "@/layout/AppShell"

export function Settings() {
  const [meta, setMeta] = useState<Meta | null>(null)
  useEffect(() => {
    api.meta().then(setMeta).catch(() => {})
  }, [])

  return (
    <div className="animate-fade-up max-w-2xl">
      <PageHeader title="Settings" description="About this AgentLeak instance." />

      <Card className="p-5">
        <div className="flex items-center gap-2 text-sm font-medium">
          <ShieldCheck className="size-4 text-sev-ok" /> Local & private
        </div>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Everything runs on this machine. Traces are analyzed in-process and stored in a local SQLite
          database under <code className="rounded bg-muted px-1.5 py-0.5 text-xs">$AGENTLEAK_HOME</code>{" "}
          (default <code className="rounded bg-muted px-1.5 py-0.5 text-xs">~/.agentleak</code>). No data
          leaves your machine.
        </p>

        <Separator className="my-4" />

        <dl className="grid grid-cols-2 gap-y-2.5 text-sm">
          <dt className="text-muted-foreground">Version</dt>
          <dd className="font-mono">{meta?.version ?? "—"}</dd>
          <dt className="text-muted-foreground">Scoring</dt>
          <dd>AgentRisk (RI = WSL / ρ_S)</dd>
          <dt className="text-muted-foreground">Detectors</dt>
          <dd className="font-mono text-xs">{meta?.detectors.join(", ")}</dd>
          <dt className="text-muted-foreground">Channels</dt>
          <dd className="font-mono text-xs">{meta?.channels.length} normalized</dd>
        </dl>

        <Separator className="my-4" />

        <div className="flex flex-wrap gap-4 text-sm">
          <a
            href="https://github.com/yagobski/agentleak-oss"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-primary hover:underline"
          >
            <Github className="size-4" /> Source
          </a>
          <a
            href="https://arxiv.org/abs/2602.11510"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-primary hover:underline"
          >
            <ExternalLink className="size-4" /> AgentRisk paper
          </a>
        </div>
      </Card>
    </div>
  )
}
