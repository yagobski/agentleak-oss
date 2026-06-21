"""``agentleak`` command-line interface.

Commands: init, run, report, validate, scenarios, version.
"""

from __future__ import annotations

import json
import os

import typer

from . import __version__
from .core.config import DEFAULT_CONFIG_YAML, Config
from .core.report import AnalysisResult
from .core.runner import AgentLeakRunner
from .core.trace import Trace
from .reporters import normalize_formats, render, write_reports
from .scenarios import list_scenarios, load_example_trace

app = typer.Typer(
    add_completion=False,
    help="AgentLeak OSS — local privacy-leakage testing for AI agents.",
    no_args_is_help=True,
)

_VERDICT_COLORS = {
    "Pass": typer.colors.GREEN,
    "Conditional pass": typer.colors.YELLOW,
    "High risk": typer.colors.BRIGHT_YELLOW,
    "Fail": typer.colors.RED,
}
_LEVEL_COLORS = {
    "critical": typer.colors.RED,
    "high": typer.colors.BRIGHT_YELLOW,
    "medium": typer.colors.YELLOW,
    "low": typer.colors.GREEN,
    "none": typer.colors.WHITE,
}
_INTERNAL_CHANNELS = {
    "tool_call", "shared_memory", "log", "inter_agent_message", "generated_file",
}


# ----------------------------------------------------------------------
# version
# ----------------------------------------------------------------------
@app.command()
def version() -> None:
    """Print the AgentLeak version."""
    typer.echo(f"agentleak {__version__}")


# ----------------------------------------------------------------------
# init
# ----------------------------------------------------------------------
@app.command()
def init(
    path: str = typer.Argument(".", help="Directory to initialize."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing config."),
) -> None:
    """Scaffold an AgentLeak project (config + folders + a sample trace)."""
    root = os.path.abspath(path)
    os.makedirs(root, exist_ok=True)
    for sub in ("scenarios", "reports", "traces"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)

    config_path = os.path.join(root, "agentleak.yaml")
    if os.path.exists(config_path) and not force:
        typer.secho(f"! {config_path} already exists (use --force to overwrite).", fg=typer.colors.YELLOW)
    else:
        with open(config_path, "w", encoding="utf-8") as fh:
            fh.write(DEFAULT_CONFIG_YAML)
        typer.secho(f"✓ wrote {config_path}", fg=typer.colors.GREEN)

    # Drop a runnable sample trace so `agentleak run` works immediately.
    sample = load_example_trace("healthcare_patient_summary")
    sample_path = os.path.join(root, "traces", "example_trace.json")
    with open(sample_path, "w", encoding="utf-8") as fh:
        json.dump(sample.to_dict(), fh, indent=2)
    typer.secho(f"✓ wrote {sample_path}", fg=typer.colors.GREEN)

    typer.echo("")
    typer.echo("Next steps:")
    typer.echo("  agentleak run --trace traces/example_trace.json")
    typer.echo("  agentleak run --scenario healthcare_patient_summary")


# ----------------------------------------------------------------------
# validate
# ----------------------------------------------------------------------
@app.command()
def validate(
    config: str = typer.Argument("agentleak.yaml", help="Path to the config file."),
    trace: str | None = typer.Option(None, "--trace", "-t", help="Also validate a trace file."),
) -> None:
    """Validate a configuration (and optionally a trace) file."""
    ok = True
    try:
        cfg = Config.load(config)
        typer.secho(f"✓ config valid: {config}", fg=typer.colors.GREEN)
        typer.echo(f"  detectors: {', '.join(k for k, v in cfg.detectors.as_dict().items() if v) or 'none'}")
        typer.echo(f"  channels:  {len(cfg.channels)} · scenarios: {len(cfg.scenarios)}")
        normalize_formats(cfg.reports.formats)
    except FileNotFoundError:
        typer.secho(f"✗ config not found: {config}", fg=typer.colors.RED)
        ok = False
    except Exception as exc:  # noqa: BLE001 - surface any validation error
        typer.secho(f"✗ invalid config: {exc}", fg=typer.colors.RED)
        ok = False

    if trace:
        try:
            t = Trace.from_json_file(trace)
            typer.secho(f"✓ trace valid: {trace} ({len(t.events)} events)", fg=typer.colors.GREEN)
        except Exception as exc:  # noqa: BLE001
            typer.secho(f"✗ invalid trace: {exc}", fg=typer.colors.RED)
            ok = False

    raise typer.Exit(code=0 if ok else 1)


# ----------------------------------------------------------------------
# scenarios
# ----------------------------------------------------------------------
@app.command()
def scenarios() -> None:
    """List the built-in scenarios."""
    for s in list_scenarios():
        typer.secho(s.id, fg=typer.colors.CYAN, bold=True)
        typer.echo(f"  {s.description}")
        typer.echo(f"  domain: {s.domain} · sensitive: {', '.join(s.sensitive_data)}")


# ----------------------------------------------------------------------
# serve (web GUI)
# ----------------------------------------------------------------------
@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind."),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open a browser."),
) -> None:
    """Launch the local web GUI (requires the [gui] extra)."""
    try:
        from .web import run_server
    except Exception as exc:  # noqa: BLE001
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    typer.secho(f"AgentLeak GUI → http://{host}:{port}  (Ctrl+C to stop)", fg=typer.colors.GREEN)
    try:
        run_server(host=host, port=port, open_browser=not no_browser)
    except RuntimeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc


# ----------------------------------------------------------------------
# run
# ----------------------------------------------------------------------
@app.command()
def run(
    config: str | None = typer.Option(None, "--config", "-c", help="Config file (honors detector/scoring settings)."),
    scenario: str | None = typer.Option(None, "--scenario", "-s", help="Run a built-in scenario (or 'all')."),
    trace: str | None = typer.Option(None, "--trace", "-t", help="Analyze a trace JSON file."),
    output: str | None = typer.Option(None, "--output", "-o", help="Report output directory."),
    fmt: str = typer.Option("json,html,markdown", "--format", "-f", help="Comma-separated formats."),
    fail_under: int | None = typer.Option(None, "--fail-under", help="Exit non-zero if a score is below this."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Less console output."),
) -> None:
    """Analyze a trace (or scenario) and write privacy reports."""
    cfg: Config | None = None
    if config:
        try:
            cfg = Config.load(config)
        except Exception as exc:  # noqa: BLE001
            typer.secho(f"✗ could not load config: {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=2) from exc

    traces = _resolve_traces(trace, scenario, cfg)
    if not traces:
        typer.secho(
            "Nothing to run. Provide --trace, --scenario, or scenarios in --config.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    out_dir = output or (cfg.reports.output_dir if cfg else "reports")
    formats = [f for f in fmt.split(",") if f.strip()]
    runner = AgentLeakRunner(cfg)

    worst_blocked = False
    for _label, t in traces:
        result = runner.analyze(t)
        if fail_under is not None:
            result.fail_below = fail_under
        written = write_reports(result, out_dir, formats, basename=result.run_id)
        if not quiet:
            _print_result(result, written)
        worst_blocked = worst_blocked or result.blocked

    raise typer.Exit(code=1 if worst_blocked else 0)


# ----------------------------------------------------------------------
# report
# ----------------------------------------------------------------------
@app.command()
def report(
    input: str = typer.Option(..., "--input", "-i", help="A result.json produced by `run`."),
    fmt: str = typer.Option("html", "--format", "-f", help="Comma-separated formats to render."),
    output: str | None = typer.Option(None, "--output", "-o", help="Output directory."),
) -> None:
    """Re-render a saved JSON report into other formats."""
    try:
        with open(input, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        typer.secho(f"✗ could not read report: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    out_dir = output or os.path.dirname(os.path.abspath(input))
    basename = os.path.splitext(os.path.basename(input))[0]
    os.makedirs(out_dir, exist_ok=True)
    from .reporters import _EXTENSIONS  # local import: internal mapping

    for f in normalize_formats([x for x in fmt.split(",") if x.strip()]):
        content = render(data, f)
        path = os.path.join(out_dir, f"{basename}.{_EXTENSIONS[f]}")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        typer.secho(f"✓ {f}: {path}", fg=typer.colors.GREEN)


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _resolve_traces(
    trace: str | None, scenario: str | None, cfg: Config | None
) -> list[tuple[str, Trace]]:
    if trace:
        return [(trace, Trace.from_json_file(trace))]
    if scenario:
        if scenario == "all":
            return [(s.id, load_example_trace(s.id)) for s in list_scenarios() if s.example_trace]
        return [(scenario, load_example_trace(scenario))]
    if cfg and cfg.scenarios:
        out: list[tuple[str, Trace]] = []
        for ref in cfg.scenarios:
            if ref.enabled:
                try:
                    out.append((ref.id, load_example_trace(ref.id)))
                except (KeyError, ValueError):
                    typer.secho(f"! skipping unknown scenario '{ref.id}'", fg=typer.colors.YELLOW)
        return out
    return []


def _print_result(result: AnalysisResult, written: dict[str, str]) -> None:
    data = result.to_dict()
    verdict_color = _VERDICT_COLORS.get(result.verdict, typer.colors.WHITE)

    typer.echo("")
    typer.secho("AgentLeak Privacy Report (AgentRisk scoring)", bold=True)
    typer.echo(f"Agent: {result.agent_name} · run: {result.run_id} · events: {result.event_count}")
    typer.echo("")
    typer.secho(
        f"Risk Index: {data['risk_index']:.3f}   {result.verdict}   "
        f"(privacy {result.privacy_score}/100)",
        fg=verdict_color, bold=True,
    )
    lp = data["summary"]["level_profile"]
    s = data["summary"]
    typer.echo(
        f"WSL {data['wsl']} / ρ_S {data['rho_s']}  ·  "
        f"{s['leaked_secrets']} of {s['vault_secrets']} secrets leaked  "
        f"(L4 {lp['L4']}, L3 {lp['L3']}, L2 {lp['L2']}, L1 {lp['L1']})"
    )
    cs = data.get("compliance", {}).get("summary")
    if cs:
        color = typer.colors.GREEN if cs["non_compliant"] == 0 else typer.colors.BRIGHT_YELLOW
        typer.secho(
            f"Compliance: {cs['compliant']}/{cs['total']} frameworks clear "
            f"({cs['controls_at_risk']} control(s) at risk)",
            fg=color,
        )

    if data["channel_risks"]:
        typer.echo("")
        typer.echo("Risk by channel:")
        for cr in data["channel_risks"]:
            color = _LEVEL_COLORS.get(cr["level"], typer.colors.WHITE)
            typer.echo("  " + f"{cr['channel']:<22} ", nl=False)
            typer.secho(f"{cr['level_label']:<4}", fg=color, nl=False)
            typer.echo(f" RI {cr['ri']:.3f}  {cr['finding_count']} finding(s)")

    insight = _console_insight(data)
    if insight:
        typer.echo("")
        typer.secho("Key insight: ", fg=typer.colors.CYAN, bold=True, nl=False)
        typer.echo(insight)

    if result.blocked:
        typer.echo("")
        typer.secho("⛔ Blocked — this run would fail a CI privacy gate.", fg=typer.colors.RED, bold=True)

    if written:
        typer.echo("")
        for f, path in written.items():
            typer.secho(f"✓ {f:<8} {path}", fg=typer.colors.GREEN)


def _console_insight(data: dict) -> str | None:
    levels = {cr["channel"]: cr["level"] for cr in data.get("channel_risks", [])}
    output_level = levels.get("final_output", "none")
    internal = [c for c, lvl in levels.items() if c in _INTERNAL_CHANNELS and lvl != "none"]
    if output_level in {"none", "low"} and internal:
        return (
            "the final answer appears safe, but sensitive data leaked through "
            f"internal channels ({', '.join(internal)})."
        )
    return None


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
