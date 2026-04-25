from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .claude_code import extract_json_text


FALLBACK_QUIZ = [
    {
        "prompt": "When learning {concept}, what is the most useful first step?",
        "choices": [
            "Identify the key terms, relationships, and examples in {concept}",
            "Memorize every formula before seeing the idea",
            "Ignore the assumptions behind the explanation",
            "Skip examples and only read definitions",
        ],
        "answer": 0,
    },
    {
        "prompt": "What should a good explanation of {concept} help you understand?",
        "choices": [
            "How the main idea works and when to use it",
            "Why definitions are more important than examples",
            "How to avoid checking your reasoning",
            "Why one memorized answer works everywhere",
        ],
        "answer": 0,
    },
    {
        "prompt": "In {concept}, what is most important to track as the explanation develops?",
        "choices": [
            "What changes, what stays fixed, and why the result matters",
            "only the final answer",
            "as many symbols as possible",
            "the longest possible definition",
        ],
        "answer": 0,
    },
    {
        "prompt": "If {concept} feels confusing, which comparison is most useful?",
        "choices": [
            "Inputs, outputs, assumptions, and consequences",
            "font size and color",
            "a single word with no example",
            "a result with no reasoning",
        ],
        "answer": 0,
    },
    {
        "prompt": "After watching a lesson on {concept}, what should improve?",
        "choices": [
            "Your ability to apply the idea, interpret results, and notice limits",
            "copy an answer without understanding it",
            "avoid connecting the topic to evidence",
            "use one method for every situation",
        ],
        "answer": 0,
    },
]


def fallback_quiz(concept: str) -> list[dict]:
    questions = []
    for item in FALLBACK_QUIZ:
        question = dict(item)
        question["prompt"] = question["prompt"].format(concept=concept)
        question["choices"] = [choice.format(concept=concept) for choice in question["choices"]]
        questions.append(question)
    return questions


def _prompt(concept: str, research: str) -> str:
    return f"""
Create a five-question multiple-choice quiz for a pre/post learning assessment.

Topic: {concept}
Research context: {research or "None provided."}

Requirements:
- Write questions that directly test the named topic, not generic study strategy.
- Mention topic-specific terms, definitions, examples, or misconceptions in every question.
- Use the research context when it gives a concrete class level, use case, misconception, field, or example.
- Avoid revealing answers in the question wording.
- Each question must have exactly four choices.
- The correct answer must be a zero-based integer in `answer`.
- Keep choices short, specific, and plausible.
- Do not use placeholders, generic wording, TBDs, or meta questions about learning.
- Return only JSON with this shape:
{{"questions":[{{"prompt":"...","choices":["...","...","...","..."],"answer":0}}]}}
""".strip()


def normalize_quiz(raw: object, concept: str) -> list[dict]:
    if isinstance(raw, dict):
        raw_questions = raw.get("questions")
    else:
        raw_questions = raw
    if not isinstance(raw_questions, list):
        raise ValueError("Claude returned JSON without a questions array.")

    questions = []
    for item in raw_questions[:5]:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        choices = [str(choice).strip() for choice in item.get("choices") or [] if str(choice).strip()]
        try:
            answer = int(item.get("answer"))
        except (TypeError, ValueError):
            answer = -1
        placeholder_text = " ".join([prompt, *choices]).lower()
        has_placeholder = any(token in placeholder_text for token in ("tbd", "placeholder", "insert ", "..."))
        if prompt and len(choices) == 4 and 0 <= answer < 4 and not has_placeholder:
            questions.append({"prompt": prompt, "choices": choices, "answer": answer})

    if len(questions) != 5:
        raise ValueError(f"Claude returned {len(questions)} valid questions instead of 5.")
    return questions


def generate_quiz(
    *,
    concept: str,
    research: str,
    workdir: Path,
    output_path: Path,
    model: str,
) -> list[dict]:
    workdir.mkdir(parents=True, exist_ok=True)
    command = [
        "claude",
        "-p",
        "--model",
        model,
        "--system-prompt",
        "You are a JSON API for an education app. Return only valid JSON. Do not include prose.",
        "--output-format",
        "json",
        _prompt(concept, research),
    ]
    completed = subprocess.run(
        command,
        cwd=workdir,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "Claude question generation failed.").strip())

    outer = json.loads(completed.stdout)
    if outer.get("is_error"):
        raise RuntimeError(outer.get("result") or "Claude question generation returned an error.")

    parsed = json.loads(extract_json_text(outer.get("result") or ""))
    quiz = normalize_quiz(parsed, concept)
    output_path.write_text(json.dumps({"questions": quiz}, indent=2), encoding="utf-8")
    return quiz
