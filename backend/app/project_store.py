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
    connection.execute("""
        CREATE TABLE IF NOT EXISTS code_proposals (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            files_json TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence_note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS project_tasks (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
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


TASK_STATUSES = {"proposed", "in_progress", "blocked", "verified"}


def create_task(project_id: str, title: str, description: str = "") -> dict | None:
    now = datetime.now(timezone.utc).isoformat()
    task = {
        "id": str(uuid.uuid4()), "project_id": project_id, "title": title.strip(),
        "description": description.strip(), "status": "proposed", "evidence": "",
        "created_at": now, "updated_at": now,
    }
    with _connect() as db:
        if not db.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone():
            return None
        db.execute(
            "INSERT INTO project_tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (task["id"], project_id, task["title"], task["description"], task["status"],
             task["evidence"], now, now),
        )
    return task


def list_tasks(project_id: str) -> list[dict]:
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM project_tasks WHERE project_id = ? ORDER BY created_at ASC",
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_task(project_id: str, task_id: str, status: str, evidence: str = "") -> dict | None:
    if status not in TASK_STATUSES:
        raise ValueError("status must be proposed, in_progress, blocked, or verified")
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as db:
        row = db.execute(
            "SELECT * FROM project_tasks WHERE id = ? AND project_id = ?",
            (task_id, project_id),
        ).fetchone()
        if not row:
            return None
        if status == "verified" and not evidence.strip():
            raise ValueError("evidence is required before marking a task verified")
        db.execute(
            "UPDATE project_tasks SET status = ?, evidence = ?, updated_at = ? WHERE id = ?",
            (status, evidence.strip(), now, task_id),
        )
        updated = db.execute("SELECT * FROM project_tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(updated)



def create_code_proposal(project_id: str, task_id: str, provider: str, model: str, files: list[dict], evidence_note: str) -> dict | None:
    now = datetime.now(timezone.utc).isoformat()
    proposal = {
        "id": str(uuid.uuid4()), "project_id": project_id, "task_id": task_id,
        "provider": provider, "model": model, "files": files,
        "status": "proposed", "evidence_note": evidence_note, "created_at": now,
    }
    with _connect() as db:
        task = db.execute(
            "SELECT id FROM project_tasks WHERE id = ? AND project_id = ?",
            (task_id, project_id),
        ).fetchone()
        if not task:
            return None
        db.execute(
            "INSERT INTO code_proposals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (proposal["id"], project_id, task_id, provider, model,
             json.dumps(files, ensure_ascii=False), proposal["status"], evidence_note, now),
        )
    return proposal


def list_code_proposals(project_id: str, task_id: str | None = None) -> list[dict]:
    with _connect() as db:
        if task_id:
            rows = db.execute(
                "SELECT * FROM code_proposals WHERE project_id = ? AND task_id = ? ORDER BY created_at DESC",
                (project_id, task_id),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM code_proposals WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["files"] = json.loads(item.pop("files_json"))
        result.append(item)
    return result
