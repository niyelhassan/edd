from __future__ import annotations

import json
import subprocess
from pathlib import Path


class CodexCliError(RuntimeError):
    pass


def strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def run_codex_prompt(
    *,
    prompt: str,
    workdir: Path,
    output_path: Path,
    model: str,
    reasoning_effort: str = "medium",
    schema_path: Path | None = None,
    timeout_seconds: int = 900,
) -> str:
    workdir = workdir.resolve()
    output_path = output_path.resolve()
    schema_path = schema_path.resolve() if schema_path is not None else None

    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "codex",
        "-a",
        "never",
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "-s",
        "workspace-write",
        "-C",
        str(workdir),
        "-c",
        f"reasoning_effort=\"{reasoning_effort}\"",
        "-m",
        model,
        "-o",
        str(output_path),
    ]
    if schema_path is not None:
        command.extend(["--output-schema", str(schema_path)])
    command.append(prompt)

    completed = subprocess.run(
        command,
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "Unknown Codex CLI error"
        raise CodexCliError(detail)
    if not output_path.exists():
        raise CodexCliError("Codex completed without writing an output file.")
    return output_path.read_text(encoding="utf-8")


def run_codex_json(
    *,
    prompt: str,
    workdir: Path,
    output_path: Path,
    model: str,
    reasoning_effort: str = "medium",
    schema_path: Path,
    timeout_seconds: int = 900,
) -> dict:
    raw = run_codex_prompt(
        prompt=prompt,
        workdir=workdir,
        output_path=output_path,
        model=model,
        reasoning_effort=reasoning_effort,
        schema_path=schema_path,
        timeout_seconds=timeout_seconds,
    )
    try:
        return json.loads(strip_markdown_fences(raw))
    except json.JSONDecodeError as exc:
        raise CodexCliError(f"Codex returned invalid JSON: {exc}") from exc
