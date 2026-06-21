"""Bundled scenario packs load, convert, and produce leaking traces."""

from __future__ import annotations

import pytest

from agentleak import AgentLeakRunner
from agentleak.core.trace import Trace
from agentleak.scenarios.packs import expand_pack, list_packs, load_pack


def test_builtin_packs_present():
    ids = {p["id"] for p in list_packs()}
    assert {"agentleak_bench", "ai4privacy_probes"} <= ids
    for pack in list_packs():
        assert pack["count"] > 0
        assert pack["name"] and pack["source"]


def test_load_pack_unknown_raises():
    with pytest.raises(KeyError):
        load_pack("does_not_exist")


def test_expand_pack_yields_traces_with_origin():
    entries = expand_pack("agentleak_bench")
    assert len(entries) == len(load_pack("agentleak_bench")["scenarios"])
    for meta, trace in entries:
        assert isinstance(trace, Trace)
        assert meta["pack_id"] == "agentleak_bench"
        assert meta["origin_id"]  # every entry is traceable to its source


@pytest.mark.parametrize("pack_id", ["agentleak_bench", "ai4privacy_probes"])
def test_every_pack_scenario_leaks(pack_id: str):
    """Each bundled scenario should be a meaningful (scoring) leak test."""
    runner = AgentLeakRunner()
    for _meta, trace in expand_pack(pack_id):
        report = runner.analyze(trace).to_dict()
        assert report["summary"]["leaked_secrets"] > 0, f"{_meta['origin_id']} did not leak"


def test_bench_pack_is_balanced_across_verticals():
    domains = [meta["domain"] for meta, _ in expand_pack("agentleak_bench")]
    assert set(domains) == {"healthcare", "finance", "legal", "corporate"}
