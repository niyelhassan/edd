from __future__ import annotations

import asyncio
import json
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from claude_agent_sdk import CLINotFoundError, ProcessError


class ClaudeCodeError(RuntimeError):
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


def _usage_dict(message: ResultMessage, *, max_turns: int | None) -> dict:
    usage = dict(message.usage or {})
    model_usage = dict(message.model_usage or {})
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    cache_read_tokens = int(usage.get("cache_read_input_tokens") or 0)
    cache_creation_tokens = int(usage.get("cache_creation_input_tokens") or 0)
    storyboard_total = input_tokens + output_tokens + cache_read_tokens + cache_creation_tokens
    return {
        "provider": "claude-agent-sdk",
        "total_tokens": storyboard_total,
        "stage_totals": {
            "storyboard": storyboard_total,
            "scene_prep_and_code": 0,
            "other": 0,
        },
        "max_turns": max_turns,
        "num_turns": message.num_turns,
        "duration_ms": message.duration_ms,
        "cost_usd": message.total_cost_usd,
        "session_id": message.session_id,
        "stop_reason": message.stop_reason,
        "model_usage": model_usage,
    }


async def _run_query(
    prompt: str,
    *,
    workdir: Path,
    model: str,
    max_turns: int | None,
    cli_path: str | None,
) -> ResultMessage:
    result: ResultMessage | None = None
    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=workdir,
                model=model,
                max_turns=max_turns,
                cli_path=cli_path,
                tools=[],
                permission_mode="plan",
                effort="low",
            ),
        ):
            if isinstance(message, ResultMessage):
                result = message
    except CLINotFoundError as exc:
        raise ClaudeCodeError("Claude Code CLI is not installed or not on PATH.") from exc
    except ProcessError as exc:
        detail = exc.stderr or str(exc)
        raise ClaudeCodeError(detail) from exc
    except Exception as exc:
        if result and result.result:
            return result
        raise ClaudeCodeError(str(exc)) from exc

    if result is None or not result.result:
        raise ClaudeCodeError("Claude Agent SDK returned no result.")
    if result.is_error or (result.result or "").startswith("API Error:"):
        raise ClaudeCodeError(result.result or "Claude Agent SDK returned an error.")
    return result


def run_claude_json(
    *,
    prompt: str,
    workdir: Path,
    output_path: Path,
    model: str,
    max_turns: int | None = None,
    cli_path: str | None = None,
    timeout_seconds: int = 900,
) -> tuple[dict, dict]:
    del timeout_seconds
    workdir = workdir.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for _ in range(2):
        try:
            result = asyncio.run(
                _run_query(prompt, workdir=workdir, model=model, max_turns=max_turns, cli_path=cli_path)
            )
            cleaned = strip_markdown_fences(result.result or "")
            parsed = json.loads(cleaned)
            output_path.write_text(cleaned, encoding="utf-8")
            return parsed, _usage_dict(result, max_turns=max_turns)
        except (ClaudeCodeError, json.JSONDecodeError) as exc:
            last_error = exc
    raise ClaudeCodeError(str(last_error) if last_error else "Claude Agent SDK failed.")


def run_claude_text(
    *,
    prompt: str,
    workdir: Path,
    output_path: Path,
    model: str,
    max_turns: int | None = None,
    cli_path: str | None = None,
    timeout_seconds: int = 900,
) -> tuple[str, dict]:
    del timeout_seconds
    workdir = workdir.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for _ in range(2):
        try:
            result = asyncio.run(
                _run_query(prompt, workdir=workdir, model=model, max_turns=max_turns, cli_path=cli_path)
            )
            cleaned = strip_markdown_fences(result.result or "")
            output_path.write_text(cleaned, encoding="utf-8")
            return cleaned, _usage_dict(result, max_turns=max_turns)
        except ClaudeCodeError as exc:
            last_error = exc
    raise ClaudeCodeError(str(last_error) if last_error else "Claude Agent SDK failed.")
