"""Importable scenario packs — curated bundles of external privacy scenarios.

A *pack* is a JSON file in this package holding a list of scenarios in some
external ``format`` (an AgentLeak spec, an ai4privacy record, or a raw trace).
Importing a pack converts each entry into an AgentLeak trace (via
:mod:`agentleak.scenarios.convert`) and stores it as a runnable scenario.

Packs ship with the wheel so the product works fully offline. To add more
scenarios from elsewhere (HuggingFace, GitHub, your own corpus), drop a pack
JSON file in this directory or upload individual scenarios via the GUI / API.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from ...core.trace import Trace
from ..convert import normalize_upload

_PACKAGE = "agentleak.scenarios.packs"


def _pack_files() -> list[str]:
    return sorted(
        p.name
        for p in resources.files(_PACKAGE).iterdir()
        if p.name.endswith(".json")
    )


def load_pack(pack_id: str) -> dict[str, Any]:
    """Load a pack's raw JSON by id (filename without extension)."""
    fname = f"{pack_id}.json"
    if fname not in _pack_files():
        known = ", ".join(p[:-5] for p in _pack_files())
        raise KeyError(f"Unknown pack '{pack_id}'. Available: {known}")
    raw = resources.files(_PACKAGE).joinpath(fname).read_text(encoding="utf-8")
    return json.loads(raw)


def list_packs() -> list[dict[str, Any]]:
    """Pack summaries (no scenario bodies) for listing in the UI."""
    out: list[dict[str, Any]] = []
    for fname in _pack_files():
        raw = json.loads(resources.files(_PACKAGE).joinpath(fname).read_text(encoding="utf-8"))
        out.append(
            {
                "id": raw.get("id", fname[:-5]),
                "name": raw.get("name", fname[:-5]),
                "description": raw.get("description", ""),
                "source": raw.get("source", ""),
                "format": raw.get("format", "agentleak_spec"),
                "count": len(raw.get("scenarios", [])),
            }
        )
    return out


def expand_pack(pack_id: str) -> list[tuple[dict[str, Any], Trace]]:
    """Load a pack and convert every scenario into ``(metadata, trace)``."""
    pack = load_pack(pack_id)
    results: list[tuple[dict[str, Any], Trace]] = []
    for entry in pack.get("scenarios", []):
        meta, trace = normalize_upload(entry)
        meta.setdefault("origin_id", entry.get("scenario_id") or entry.get("id") or "")
        meta["pack_id"] = pack_id
        results.append((meta, trace))
    return results


__all__ = ["list_packs", "load_pack", "expand_pack"]
