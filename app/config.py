from __future__ import annotations

import os
from pathlib import Path


def load_local_env(base_dir: Path) -> None:
    env_path = base_dir / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        cleaned = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), cleaned)


class Config:
    SECRET_KEY = "dev-secret-change-me"
    CLAUDE_CODE_MODEL = "claude-sonnet-4-6"
    CLAUDE_QUESTION_MODEL = "claude-haiku-4-5"
    CLAUDE_CODE_MAX_TURNS = None
    DEEPGRAM_API_KEY = ""
    DEEPGRAM_VOICE_MODEL = "aura-2-thalia-en"
    MAX_WORKERS = 2
    POLL_INTERVAL_MS = 1500
