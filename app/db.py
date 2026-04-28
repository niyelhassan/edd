from __future__ import annotations

import sqlite3

from flask import Flask, current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    concept TEXT NOT NULL,
    research TEXT NOT NULL DEFAULT '',
    audience TEXT NOT NULL,
    duration_label TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    provider TEXT NOT NULL DEFAULT 'claude-agent-sdk',
    model TEXT NOT NULL DEFAULT 'claude-sonnet-4-6',
    voice_model TEXT NOT NULL,
    render_quality TEXT NOT NULL,
    style_notes TEXT NOT NULL,
    color_theme TEXT NOT NULL DEFAULT 'blue',
    status TEXT NOT NULL,
    current_step TEXT NOT NULL,
    title TEXT,
    storyboard_path TEXT,
    code_path TEXT,
    video_path TEXT,
    token_usage_json TEXT,
    quiz_token_usage_json TEXT,
    pre_score INTEGER,
    post_score INTEGER,
    quiz_json TEXT,
    survey_json TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS job_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs (id)
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA)
    _migrate_schema(db)
    db.commit()


def _migrate_schema(db: sqlite3.Connection) -> None:
    columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)").fetchall()}
    migrations = {
        "research": "ALTER TABLE jobs ADD COLUMN research TEXT NOT NULL DEFAULT ''",
        "provider": "ALTER TABLE jobs ADD COLUMN provider TEXT NOT NULL DEFAULT 'claude-agent-sdk'",
        "model": "ALTER TABLE jobs ADD COLUMN model TEXT NOT NULL DEFAULT 'claude-sonnet-4-6'",
        "token_usage_json": "ALTER TABLE jobs ADD COLUMN token_usage_json TEXT",
        "pre_score": "ALTER TABLE jobs ADD COLUMN pre_score INTEGER",
        "post_score": "ALTER TABLE jobs ADD COLUMN post_score INTEGER",
        "quiz_json": "ALTER TABLE jobs ADD COLUMN quiz_json TEXT",
        "survey_json": "ALTER TABLE jobs ADD COLUMN survey_json TEXT",
        "color_theme": "ALTER TABLE jobs ADD COLUMN color_theme TEXT NOT NULL DEFAULT 'blue'",
        "quiz_token_usage_json": "ALTER TABLE jobs ADD COLUMN quiz_token_usage_json TEXT",
    }
    for column, statement in migrations.items():
        if column not in columns:
            db.execute(statement)


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
