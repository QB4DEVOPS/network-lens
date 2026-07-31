"""SQLite snapshot store."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.models.project import Project

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "snapshots.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            label TEXT,
            model_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def append_snapshot(project: Project, label: str | None = None) -> int:
    conn = _conn()
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) FROM snapshots WHERE project_id = ?",
        (project.id,),
    ).fetchone()
    seq = int(row[0]) + 1
    conn.execute(
        "INSERT INTO snapshots (project_id, seq, label, model_json) VALUES (?, ?, ?, ?)",
        (project.id, seq, label, project.model_dump_json()),
    )
    conn.commit()
    conn.close()
    return seq


def list_snapshots(project_id: str) -> list[dict[str, object]]:
    conn = _conn()
    rows = conn.execute(
        "SELECT seq, label, created_at FROM snapshots WHERE project_id = ? ORDER BY seq",
        (project_id,),
    ).fetchall()
    conn.close()
    return [{"seq": r[0], "label": r[1], "created_at": r[2]} for r in rows]


def get_snapshot(project_id: str, seq: int) -> Project | None:
    conn = _conn()
    row = conn.execute(
        "SELECT model_json FROM snapshots WHERE project_id = ? AND seq = ?",
        (project_id, seq),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return Project.model_validate(json.loads(row[0]))
