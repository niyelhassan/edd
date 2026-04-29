from __future__ import annotations


VIDEO_CATEGORIES = (
    "CS & ML",
    "Statistics & probability",
    "Calculus",
    "Linear algebra",
    "Physics",
    "Chemistry",
    "Biology",
    "Other",
)


def _normalize_category(raw: object) -> str:
    if not isinstance(raw, dict):
        return "Other"
    category = str(raw.get("category") or "").strip()
    return category if category in VIDEO_CATEGORIES else "Other"


def _normalize_quiz(raw: object) -> list[dict]:
    raw_questions = raw.get("questions") if isinstance(raw, dict) else raw
    if not isinstance(raw_questions, list):
        raise ValueError("Claude returned JSON without a questions array.")

    questions = []
    for item in raw_questions[:5]:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or item.get("question") or "").strip()
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
