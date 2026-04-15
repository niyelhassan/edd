from __future__ import annotations

import shutil
from pathlib import Path


def resolve_claude_cli_path() -> str | None:
    direct = shutil.which("claude")
    if direct:
        return direct

    home = Path.home()
    candidates = sorted((home / ".nvm" / "versions" / "node").glob("*/bin/claude"), reverse=True)
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None
