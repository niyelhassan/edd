from __future__ import annotations

import os
from pathlib import Path


def load_local_env(base_dir: Path) -> None:
    env_path = base_dir / ".env"
    if not env_path.exists():
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        raw_line = lines[index]
        index += 1
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        cleaned = value.strip().strip('"').strip("'")

        if cleaned == "{":
            json_lines = ["{"]
            depth = 1
            while index < len(lines) and depth > 0:
                json_line = lines[index]
                index += 1
                depth += json_line.count("{") - json_line.count("}")
                json_lines.append(json_line)
            cleaned = "\n".join(json_lines)

        os.environ.setdefault(key.strip(), cleaned)


class Config:
    SECRET_KEY = ""
    CLAUDE_CODE_MODEL = "claude-sonnet-4-6"
    CLAUDE_CODE_MAX_TURNS = None
    DEEPGRAM_API_KEY = ""
    DEEPGRAM_VOICE_MODEL = "aura-2-thalia-en"
    GOOGLE_RESULTS_SPREADSHEET_ID = ""
    GOOGLE_RESULTS_WORKSHEET_NAME = "results"
    GOOGLE_SERVICE_ACCOUNT_FILE = ""
    GOOGLE_SERVICE_ACCOUNT_JSON = ""
    POLL_INTERVAL_MS = 1500
