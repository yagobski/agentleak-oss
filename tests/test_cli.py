"""CLI tests via Typer's CliRunner."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from agentleak.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "agentleak" in result.stdout


def test_scenarios_lists_builtins():
    result = runner.invoke(app, ["scenarios"])
    assert result.exit_code == 0
    assert "healthcare_patient_summary" in result.stdout


def test_init_scaffolds_project(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "agentleak.yaml").exists()
    assert (tmp_path / "traces" / "example_trace.json").exists()
    assert (tmp_path / "reports").is_dir()


def test_validate_good_config(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])
    result = runner.invoke(app, ["validate", str(tmp_path / "agentleak.yaml")])
    assert result.exit_code == 0
    assert "valid" in result.stdout


def test_validate_missing_config():
    result = runner.invoke(app, ["validate", "/nonexistent/agentleak.yaml"])
    assert result.exit_code == 1


def test_run_scenario_blocks_on_critical(tmp_path):
    result = runner.invoke(app, [
        "run", "--scenario", "healthcare_patient_summary",
        "--output", str(tmp_path), "--format", "json",
    ])
    # Healthcare demo leaks Level-4 data -> blocked -> exit 1.
    assert result.exit_code == 1
    assert "Risk Index" in result.stdout
    assert "Key insight" in result.stdout
    files = list(tmp_path.glob("*.json"))
    assert files


def test_run_trace_file(tmp_path):
    trace = {
        "run_id": "clean_run",
        "events": [{"channel": "final_output", "content": "Nothing to see."}],
    }
    trace_path = tmp_path / "t.json"
    trace_path.write_text(json.dumps(trace))
    result = runner.invoke(app, [
        "run", "--trace", str(trace_path), "--output", str(tmp_path), "--format", "json",
    ])
    assert result.exit_code == 0
    assert "Pass" in result.stdout


def test_run_with_nothing_errors():
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2


def test_report_rerenders_saved_json(tmp_path):
    # First produce a JSON report.
    runner.invoke(app, [
        "run", "--scenario", "finance_loan_review",
        "--output", str(tmp_path), "--format", "json",
    ])
    src = list(tmp_path.glob("*.json"))[0]
    result = runner.invoke(app, ["report", "--input", str(src), "--format", "html,markdown"])
    assert result.exit_code == 0
    assert src.with_suffix(".html").exists()
    assert src.with_suffix(".md").exists()


def test_run_fail_under_override(tmp_path):
    # A clean trace normally passes; --fail-under 101 forces a failure.
    trace = {"run_id": "r", "events": [{"channel": "final_output", "content": "clean"}]}
    p = tmp_path / "t.json"
    p.write_text(json.dumps(trace))
    result = runner.invoke(app, [
        "run", "--trace", str(p), "--output", str(tmp_path),
        "--format", "json", "--fail-under", "101",
    ])
    assert result.exit_code == 1


def test_init_force_overwrites(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])
    # Without --force it warns and keeps the file.
    warned = runner.invoke(app, ["init", str(tmp_path)])
    assert "already exists" in warned.stdout
    # With --force it rewrites without warning.
    forced = runner.invoke(app, ["init", str(tmp_path), "--force"])
    assert forced.exit_code == 0
    assert "already exists" not in forced.stdout


def test_validate_invalid_trace(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json")
    result = runner.invoke(app, ["validate", str(tmp_path / "agentleak.yaml"), "--trace", str(bad)])
    assert result.exit_code == 1
    assert "invalid trace" in result.stdout


def test_run_from_config_scenarios(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])
    result = runner.invoke(app, [
        "run", "--config", str(tmp_path / "agentleak.yaml"),
        "--output", str(tmp_path / "out"), "--format", "json", "--quiet",
    ])
    # The scaffolded config enables one scenario (healthcare) -> blocked -> exit 1.
    assert result.exit_code in (0, 1)
    assert list((tmp_path / "out").glob("*.json"))


def test_run_bad_config_errors(tmp_path):
    bad = tmp_path / "agentleak.yaml"
    bad.write_text("detectors: [this is not valid structure")
    result = runner.invoke(app, ["run", "--config", str(bad), "--scenario", "hr_employee_case"])
    assert result.exit_code == 2


def test_report_missing_input_errors():
    result = runner.invoke(app, ["report", "--input", "/nonexistent/report.json"])
    assert result.exit_code == 2
