from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .claude_code import extract_json_text


def _summarize_storyboard(storyboard: dict) -> str:
    """Compact human-readable summary of the storyboard, used to ground the quiz."""
    lines = []
    title = storyboard.get("title") or ""
    summary = storyboard.get("summary") or ""
    objective = storyboard.get("learning_objective") or ""
    takeaway = storyboard.get("closing_takeaway") or ""
    if title:
        lines.append(f"Title: {title}")
    if summary:
        lines.append(f"Summary: {summary}")
    if objective:
        lines.append(f"Learning objective: {objective}")
    if takeaway:
        lines.append(f"Closing takeaway: {takeaway}")

    lines.append("\nScenes:")
    for i, scene in enumerate(storyboard.get("scenes") or [], start=1):
        layout = scene.get("layout") or ""
        if layout in {"thanks", "title_card"}:
            continue
        lines.append(f"\n{i}. {scene.get('headline', '')}  [{layout}]")
        narration = (scene.get("narration") or "").strip()
        if narration:
            lines.append(f"   Narration: {narration}")
        for key in ("key_points", "visual_items", "highlight_terms", "equations"):
            values = [str(v).strip() for v in (scene.get(key) or []) if str(v).strip()]
            if values:
                lines.append(f"   {key}: {', '.join(values)}")
        if scene.get("takeaway"):
            lines.append(f"   takeaway: {scene['takeaway']}")
    return "\n".join(lines)


def _prompt(concept: str, research: str, storyboard_summary: str) -> str:
    return f"""
Create a 5-question multiple-choice quiz for a pre/post learning assessment based ONLY on what the lesson covers.

Topic: {concept}
Research context: {research or "None provided."}

LESSON CONTENT (the entire ground truth — every correct answer must be derivable from this):
{storyboard_summary}

REQUIREMENTS:
- Every question must be answerable from the lesson content above. Do not test material the lesson does not teach.
- Mention topic-specific terms, definitions, examples, or misconceptions that appear in the lesson.
- Use the research context when it provides a concrete class level, field, misconception, or example.
- Each question has exactly four short, plausible choices.
- The correct answer is the zero-based index in `answer`.
- Do not reveal the answer in the question wording. Avoid placeholders, TBDs, or meta questions about learning.
- Return ONLY JSON in this shape:
{{"questions":[{{"prompt":"...","choices":["...","...","...","..."],"answer":0}}]}}
""".strip()


def _fallback_prompt(concept: str, research: str) -> str:
    return f"""
Create a 5-question multiple-choice quiz on the topic.

Topic: {concept}
Research context: {research or "None provided."}

Each question has 4 plausible short choices, one correct answer (zero-based `answer`).
Return ONLY JSON: {{"questions":[{{"prompt":"...","choices":["...","...","...","..."],"answer":0}}]}}
""".strip()


def _normalize_quiz(raw: object) -> list[dict]:
    raw_questions = raw.get("questions") if isinstance(raw, dict) else raw
    if not isinstance(raw_questions, list):
        raise ValueError("Claude returned JSON without a questions array.")

    questions = []
    for item in raw_questions[:5]:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        choices = [str(c).strip() for c in item.get("choices") or [] if str(c).strip()]
        try:
            answer = int(item.get("answer"))
        except (TypeError, ValueError):
            answer = -1
        placeholder = " ".join([prompt, *choices]).lower()
        if any(t in placeholder for t in ("tbd", "placeholder", "insert ", "...")):
            continue
        if prompt and len(choices) == 4 and 0 <= answer < 4:
            questions.append({"prompt": prompt, "choices": choices, "answer": answer})

    if len(questions) != 5:
        raise ValueError(f"Got {len(questions)} valid questions instead of 5.")
    return questions


def _run_claude(prompt: str, *, workdir: Path, model: str) -> tuple[dict, dict]:
    """Run Claude CLI in JSON mode, return (parsed_quiz_json, usage_dict)."""
    command = [
        "claude", "-p",
        "--model", model,
        "--system-prompt", "You are a JSON API for an education app. Return only valid JSON. Do not include prose.",
        "--output-format", "json",
        prompt,
    ]
    completed = subprocess.run(
        command, cwd=workdir, text=True, capture_output=True, timeout=120, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "Claude question generation failed.").strip())

    outer = json.loads(completed.stdout)
    if outer.get("is_error"):
        raise RuntimeError(outer.get("result") or "Claude question generation returned an error.")

    parsed = json.loads(extract_json_text(outer.get("result") or ""))
    raw_usage = outer.get("usage") or {}
    input_tokens = int(raw_usage.get("input_tokens") or 0)
    output_tokens = int(raw_usage.get("output_tokens") or 0)
    cache_read = int(raw_usage.get("cache_read_input_tokens") or 0)
    cache_create = int(raw_usage.get("cache_creation_input_tokens") or 0)
    usage = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_create,
        "total_tokens": input_tokens + output_tokens + cache_read + cache_create,
        "duration_ms": outer.get("duration_ms"),
        "cost_usd": outer.get("total_cost_usd"),
    }
    return parsed, usage


def generate_quiz_from_storyboard(
    *,
    concept: str,
    research: str,
    storyboard: dict,
    workdir: Path,
    output_path: Path,
    model: str,
) -> tuple[list[dict], dict]:
    workdir.mkdir(parents=True, exist_ok=True)
    storyboard_summary = _summarize_storyboard(storyboard)
    parsed, usage = _run_claude(_prompt(concept, research, storyboard_summary), workdir=workdir, model=model)
    quiz = _normalize_quiz(parsed)
    output_path.write_text(json.dumps({"questions": quiz}, indent=2), encoding="utf-8")
    return quiz, usage


def generate_quiz(
    *,
    concept: str,
    research: str,
    workdir: Path,
    output_path: Path,
    model: str,
) -> list[dict]:
    """Concept-only fallback (used by clones / older callers without a storyboard)."""
    workdir.mkdir(parents=True, exist_ok=True)
    parsed, _usage = _run_claude(_fallback_prompt(concept, research), workdir=workdir, model=model)
    quiz = _normalize_quiz(parsed)
    output_path.write_text(json.dumps({"questions": quiz}, indent=2), encoding="utf-8")
    return quiz
