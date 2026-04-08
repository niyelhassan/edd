from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.db import get_db


DURATION_PRESETS = {
    "short": 50,
    "medium": 72,
    "long": 100,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def row_to_dict(row) -> dict:
    return dict(row) if row is not None else None


def create_job(
    *,
    concept: str,
    audience: str,
    duration_label: str,
    voice_model: str,
    render_quality: str,
    style_notes: str,
) -> str:
    now = utc_now()
    job_id = uuid.uuid4().hex[:12]
    duration_seconds = DURATION_PRESETS.get(duration_label, DURATION_PRESETS["medium"])
    db = get_db()
    db.execute(
        """
        INSERT INTO jobs (
            id, concept, audience, duration_label, duration_seconds, voice_model,
            render_quality, style_notes, status, current_step, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            concept,
            audience,
            duration_label,
            duration_seconds,
            voice_model,
            render_quality,
            style_notes,
            "queued",
            "Waiting for worker",
            now,
            now,
        ),
    )
    db.commit()
    add_log(job_id, "Job queued.")
    return job_id


def clone_job(source: dict) -> str:
    return create_job(
        concept=source["concept"],
        audience=source["audience"],
        duration_label=source["duration_label"],
        voice_model=source["voice_model"],
        render_quality=source["render_quality"],
        style_notes=source["style_notes"],
    )


def add_log(job_id: str, message: str, level: str = "info") -> None:
    db = get_db()
    db.execute(
        "INSERT INTO job_logs (job_id, timestamp, level, message) VALUES (?, ?, ?, ?)",
        (job_id, utc_now(), level, message),
    )
    db.commit()


def update_job(job_id: str, **fields) -> None:
    if not fields:
        return

    fields["updated_at"] = utc_now()
    assignments = ", ".join(f"{column} = ?" for column in fields)
    values = list(fields.values()) + [job_id]
    db = get_db()
    db.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", values)
    db.commit()


def get_job(job_id: str) -> dict | None:
    db = get_db()
    row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return row_to_dict(row)


def get_job_logs(job_id: str) -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT timestamp, level, message FROM job_logs WHERE job_id = ? ORDER BY id ASC",
        (job_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def list_jobs(limit: int = 20) -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def list_pending_jobs() -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT * FROM jobs
        WHERE status IN ('queued', 'running')
        ORDER BY created_at ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]
