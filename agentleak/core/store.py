"""Local persistence for the AgentLeak platform — projects and runs.

Backed by SQLite (stdlib, no extra dependency), stored under a local data
directory (``$AGENTLEAK_HOME`` or ``~/.agentleak``). Everything stays on the
user's machine, consistent with the product's local-only guarantee.

A *project* represents an agent under test (its detector config, vault scope,
and agent type for SDK wiring). A *run* is one stored analysis of that agent.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from ..integrations.registry import framework_ids

# Valid agent frameworks come from the pluggable registry (extensible).
AGENT_TYPES = framework_ids()


def data_dir() -> Path:
    raw = os.environ.get("AGENTLEAK_HOME") or os.path.join(Path.home(), ".agentleak")
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Store:
    """Thread-safe-enough SQLite store (one connection per call)."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or str(data_dir() / "agentleak.db")
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init(self) -> None:
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    agent_type TEXT NOT NULL DEFAULT 'generic',
                    description TEXT DEFAULT '',
                    config TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )"""
            )
            c.execute(
                """CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    source TEXT DEFAULT 'manual',
                    agent_name TEXT DEFAULT '',
                    risk_index REAL DEFAULT 0,
                    verdict TEXT DEFAULT '',
                    blocked INTEGER DEFAULT 0,
                    leaked INTEGER DEFAULT 0,
                    report TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )"""
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id, created_at)")
            c.execute(
                """CREATE TABLE IF NOT EXISTS scenarios (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    domain TEXT NOT NULL DEFAULT 'custom',
                    description TEXT DEFAULT '',
                    sensitive_data TEXT NOT NULL DEFAULT '[]',
                    tags TEXT NOT NULL DEFAULT '[]',
                    difficulty TEXT DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'custom',
                    pack_id TEXT DEFAULT '',
                    origin_id TEXT DEFAULT '',
                    trace TEXT NOT NULL,
                    created_at REAL NOT NULL
                )"""
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_scenarios_pack ON scenarios(pack_id, origin_id)")

    # -- projects -------------------------------------------------------
    def create_project(
        self,
        name: str,
        *,
        agent_type: str = "generic",
        description: str = "",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        pid = _new_id("proj")
        now = _now()
        if agent_type not in AGENT_TYPES:
            agent_type = "generic"
        with self._conn() as c:
            c.execute(
                "INSERT INTO projects (id, name, agent_type, description, config, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (pid, name.strip() or "Untitled", agent_type, description, json.dumps(config or {}), now, now),
            )
        return self.get_project(pid)  # type: ignore[return-value]

    def list_projects(self) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        return [self._project_row(r) for r in rows]

    def get_project(self, pid: str) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
            if not row:
                return None
            project = self._project_row(row)
            agg = c.execute(
                "SELECT COUNT(*) n, AVG(risk_index) avg_ri FROM runs WHERE project_id=?", (pid,)
            ).fetchone()
            last = c.execute(
                "SELECT * FROM runs WHERE project_id=? ORDER BY created_at DESC LIMIT 1", (pid,)
            ).fetchone()
        project["run_count"] = agg["n"] or 0
        project["avg_risk_index"] = round(agg["avg_ri"], 4) if agg["avg_ri"] is not None else None
        project["last_run"] = self._run_summary(last) if last else None
        return project

    def get_project_by_name(self, name: str) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute("SELECT id FROM projects WHERE name=? ORDER BY created_at LIMIT 1", (name,)).fetchone()
        return self.get_project(row["id"]) if row else None

    def update_project(self, pid: str, **fields: Any) -> dict[str, Any] | None:
        allowed = {"name", "agent_type", "description", "config"}
        sets, vals = [], []
        for k, v in fields.items():
            if k not in allowed or v is None:
                continue
            sets.append(f"{k}=?")
            vals.append(json.dumps(v) if k == "config" else v)
        if not sets:
            return self.get_project(pid)
        sets.append("updated_at=?")
        vals.append(_now())
        vals.append(pid)
        with self._conn() as c:
            cur = c.execute(f"UPDATE projects SET {', '.join(sets)} WHERE id=?", vals)
            if cur.rowcount == 0:
                return None
        return self.get_project(pid)

    def delete_project(self, pid: str) -> bool:
        with self._conn() as c:
            c.execute("DELETE FROM runs WHERE project_id=?", (pid,))
            cur = c.execute("DELETE FROM projects WHERE id=?", (pid,))
            return cur.rowcount > 0

    def touch_project(self, pid: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE projects SET updated_at=? WHERE id=?", (_now(), pid))

    # -- runs -----------------------------------------------------------
    def create_run(self, project_id: str, report: dict[str, Any], *, source: str = "manual") -> dict[str, Any]:
        rid = _new_id("run")
        now = _now()
        summary = report.get("summary", {})
        with self._conn() as c:
            c.execute(
                "INSERT INTO runs (id, project_id, created_at, source, agent_name, risk_index, verdict, blocked, leaked, report)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    rid, project_id, now, source,
                    report.get("agent_name", ""),
                    float(report.get("risk_index", 0)),
                    report.get("verdict", ""),
                    1 if report.get("blocked") else 0,
                    int(summary.get("leaked_secrets", 0)),
                    json.dumps(report),
                ),
            )
        self.touch_project(project_id)
        return self.get_run(rid)  # type: ignore[return-value]

    def list_runs(self, project_id: str | None = None, *, limit: int = 200) -> list[dict[str, Any]]:
        with self._conn() as c:
            if project_id:
                rows = c.execute(
                    "SELECT * FROM runs WHERE project_id=? ORDER BY created_at DESC LIMIT ?", (project_id, limit)
                ).fetchall()
            else:
                rows = c.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._run_summary(r) for r in rows]

    def get_run(self, rid: str) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
        if not row:
            return None
        summary = self._run_summary(row)
        summary["report"] = json.loads(row["report"])
        return summary

    def delete_run(self, rid: str) -> bool:
        with self._conn() as c:
            return c.execute("DELETE FROM runs WHERE id=?", (rid,)).rowcount > 0

    # -- scenarios ------------------------------------------------------
    def create_scenario(
        self,
        name: str,
        trace: dict[str, Any],
        *,
        domain: str = "custom",
        description: str = "",
        sensitive_data: list[str] | None = None,
        tags: list[str] | None = None,
        difficulty: str = "",
        source: str = "custom",
        pack_id: str = "",
        origin_id: str = "",
    ) -> dict[str, Any]:
        sid = _new_id("sce")
        with self._conn() as c:
            c.execute(
                "INSERT INTO scenarios (id, name, domain, description, sensitive_data, tags,"
                " difficulty, source, pack_id, origin_id, trace, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    sid, name.strip() or "Untitled scenario", domain, description,
                    json.dumps(sensitive_data or []), json.dumps(tags or []),
                    difficulty, source, pack_id, origin_id, json.dumps(trace), _now(),
                ),
            )
        return self.get_scenario(sid)  # type: ignore[return-value]

    def list_scenarios(self) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM scenarios ORDER BY created_at DESC").fetchall()
        return [self._scenario_row(r, with_trace=False) for r in rows]

    def get_scenario(self, sid: str, *, with_trace: bool = True) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM scenarios WHERE id=?", (sid,)).fetchone()
        return self._scenario_row(row, with_trace=with_trace) if row else None

    def delete_scenario(self, sid: str) -> bool:
        with self._conn() as c:
            return c.execute("DELETE FROM scenarios WHERE id=?", (sid,)).rowcount > 0

    def scenario_exists(self, pack_id: str, origin_id: str) -> bool:
        """True if a scenario from this pack/origin was already imported."""
        if not origin_id:
            return False
        with self._conn() as c:
            row = c.execute(
                "SELECT 1 FROM scenarios WHERE pack_id=? AND origin_id=? LIMIT 1",
                (pack_id, origin_id),
            ).fetchone()
        return row is not None

    def count_pack_scenarios(self, pack_id: str) -> int:
        """How many scenarios from a given pack are currently imported."""
        with self._conn() as c:
            row = c.execute(
                "SELECT COUNT(*) n FROM scenarios WHERE pack_id=?", (pack_id,)
            ).fetchone()
        return int(row["n"] or 0)

    # -- stats ----------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        with self._conn() as c:
            p = c.execute("SELECT COUNT(*) n FROM projects").fetchone()["n"]
            r = c.execute("SELECT COUNT(*) n, AVG(risk_index) avg, SUM(blocked) blocked FROM runs").fetchone()
            recent = c.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT 8").fetchall()
        return {
            "projects": p,
            "runs": r["n"] or 0,
            "avg_risk_index": round(r["avg"], 4) if r["avg"] is not None else None,
            "blocked_runs": r["blocked"] or 0,
            "recent_runs": [self._run_summary(x) for x in recent],
        }

    # -- row mappers ----------------------------------------------------
    @staticmethod
    def _project_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "agent_type": row["agent_type"],
            "description": row["description"],
            "config": json.loads(row["config"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _run_summary(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "created_at": row["created_at"],
            "source": row["source"],
            "agent_name": row["agent_name"],
            "risk_index": row["risk_index"],
            "verdict": row["verdict"],
            "blocked": bool(row["blocked"]),
            "leaked_secrets": row["leaked"],
        }

    @staticmethod
    def _scenario_row(row: sqlite3.Row, *, with_trace: bool) -> dict[str, Any]:
        data = {
            "id": row["id"],
            "name": row["name"],
            "domain": row["domain"],
            "description": row["description"],
            "sensitive_data": json.loads(row["sensitive_data"]),
            "tags": json.loads(row["tags"]),
            "difficulty": row["difficulty"],
            "source": row["source"],
            "pack_id": row["pack_id"],
            "origin_id": row["origin_id"],
            "created_at": row["created_at"],
            "builtin": False,
        }
        if with_trace:
            data["trace"] = json.loads(row["trace"])
        return data
