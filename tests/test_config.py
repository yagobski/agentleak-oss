"""Config loading and custom-detector wiring tests."""

from __future__ import annotations

from agentleak import AgentLeakRunner, Trace
from agentleak.core.config import DEFAULT_CONFIG_YAML, Config


def test_default_config_yaml_parses(tmp_path):
    p = tmp_path / "agentleak.yaml"
    p.write_text(DEFAULT_CONFIG_YAML)
    cfg = Config.load(str(p))
    assert cfg.detectors.pii is True
    assert cfg.detectors.finance is False
    assert cfg.scoring.fail_below == 40
    assert "tool_call" in cfg.channels


def test_config_defaults_when_empty():
    cfg = Config.from_dict({})
    assert cfg.project.name == "agentleak-project"
    assert cfg.scoring.weights == [1, 2, 3, 4]
    assert cfg.privacy.redact_values is True
    assert cfg.vault.is_set() is False


def test_vault_spec_from_config():
    cfg = Config.from_dict({"vault": {"levels": {1: 5, 2: 3, 3: 2, 4: 1}, "scope_def": "manifest v3"}})
    spec, scope = cfg.vault_spec()
    assert spec == {1: 5, 2: 3, 3: 2, 4: 1}
    assert scope == "manifest v3"


def test_custom_detector_runs_through_config():
    cfg = Config.from_dict({
        "detectors": {"pii": False, "secrets": False, "healthcare": False},
        "custom_detectors": [
            {"name": "proj", "pattern": r"PROJECT-[A-Z]{3}-[0-9]{4}",
             "severity": "high", "data_type": "internal_project"},
        ],
    })
    trace = Trace(run_id="r")
    trace.add_event("tool_call", "ref PROJECT-ABC-1234")
    result = AgentLeakRunner(cfg).analyze(trace)
    assert len(result.findings) == 1
    assert result.findings[0].data_type == "internal_project"
    assert result.findings[0].detector == "custom:proj"


def test_scoring_thresholds_propagate_to_result():
    cfg = Config.from_dict({"scoring": {"fail_below": 95, "block_on_critical": False}})
    trace = Trace(run_id="r")
    trace.add_event("log", "email a@b.com")
    result = AgentLeakRunner(cfg).analyze(trace)
    assert result.fail_below == 95
    assert result.block_on_critical is False
