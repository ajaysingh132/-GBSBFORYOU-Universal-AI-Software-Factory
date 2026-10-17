"""Small SQLite project brain for durable project records (single-instance MVP)."""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

def _db_path() -> Path:
    path = Path(os.getenv("FACTORY_DB_PATH", "data/factory.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def _connect():
    connection = sqlite3.connect(_db_path(), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            goal TEXT NOT NULL,
            constraints_json TEXT NOT NULL,
            repository_urls_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS blueprints (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            content TEXT NOT NULL,
            evidence_note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)
    return connection

def create_project(name: str, goal: str, constraints: list[str], repository_urls: list[str]) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    project = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "goal": goal.strip(),
        "constraints": constraints,
        "repository_urls": repository_urls,
        "status": "proposed",
        "created_at": now,
        "updated_at": now,
    }
    with _connect() as db:
        db.execute(
            "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (project["id"], project["name"], project["goal"],
             json.dumps(constraints), json.dumps(repository_urls),
             project["status"], now, now),
        )
    return project

def list_projects(limit: int = 50) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM projects ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_project(row) for row in rows]

def get_project(project_id: str) -> dict | None:
    with _connect() as db:
        row = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _row_to_project(row) if row else None

def _row_to_project(row) -> dict:
    return {
        "id": row["id"], "name": row["name"], "goal": row["goal"],
        "constraints": json.loads(row["constraints_json"]),
        "repository_urls": json.loads(row["repository_urls_json"]),
        "status": row["status"], "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def save_blueprint(project_id: str, provider: str, model: str, content: str, evidence_note: str) -> dict | None:
    now = datetime.now(timezone.utc).isoformat()
    blueprint = {
        "id": str(uuid.uuid4()), "project_id": project_id,
        "provider": provider, "model": model, "content": content,
        "evidence_note": evidence_note, "created_at": now,
    }
    with _connect() as db:
        exists = db.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not exists:
            return None
        db.execute(
            "INSERT INTO blueprints VALUES (?, ?, ?, ?, ?, ?, ?)",
            (blueprint["id"], project_id, provider, model, content, evidence_note, now),
        )
        db.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))
    return blueprint


def list_blueprints(project_id: str) -> list[dict]:
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM blueprints WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]
