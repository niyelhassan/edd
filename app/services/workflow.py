from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from flask import current_app

from .captions import write_captions
from .claude_code import ClaudeCodeError, run_claude_json
from .deepgram_tts import DeepgramError, DeepgramTTSClient
from .manim_builder import build_manim_module
from .media import MediaError, concat_clips, extract_thumbnail, mux_video_with_audio, probe_duration, render_scene
from .question_generation import VIDEO_CATEGORIES, _normalize_category, _normalize_quiz
from .repository import add_log, get_job, update_job
from .template_registry import VALID_LAYOUTS, content_layout_prompt


VALID_COLOR_THEMES = ("blue", "violet", "green", "amber", "rose", "slate")
VALID_EXPLANATION_LEVELS = ("high_school", "college", "expert")

_EXPLANATION_LEVEL_GUIDANCE = {
    "high_school": (
        "Target audience is a high school student. Use plain language, define technical terms "
        "on first use, rely on concrete examples, keep equations minimal, and build each idea "
        "from the ground up."
    ),
    "college": (
        "Target audience is a college student. Assume basic familiarity with the domain "
        "but explain technical terms clearly. "
        "Balance conceptual intuition with precise language, and use equations where they add clarity."
    ),
    "expert": (
        "Target audience is an advanced learner or domain expert. "
        "Use precise technical vocabulary, skip over introductory context, go deep on mechanism "
        "and derivation, assume fluency with standard notation, and highlight non-obvious insights."
    ),
}
FIXED_THANKS_NARRATION = "Thanks for watching. Take a moment to review the key idea, then try the quiz to see what stuck."
FIXED_THANKS_HOOK = ""


class WorkflowError(RuntimeError):
    pass


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "scene"


def _class_name(index: int, slug: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", slug)
    title = "".join(word.capitalize() for word in words[:4]) or f"Scene{index:02d}"
    return f"Scene{index:02d}{title}"


def _storyboard_schema_path() -> Path:
    return Path(__file__).resolve().parent.parent / "schemas" / "storyboard.schema.json"


def _storyboard_scene_limits() -> tuple[int, int]:
    schema = json.loads(_storyboard_schema_path().read_text(encoding="utf-8"))
    scenes = schema.get("properties", {}).get("scenes", {})
    return int(scenes.get("minItems", 3)), int(scenes.get("maxItems", 8))


def _target_content_scene_count(duration_seconds: int) -> int:
    """Content scenes between the title card and the takeaways/thanks closers."""
    if duration_seconds <= 75:
        return 2
    if duration_seconds <= 210:
        return 3
    return 5


def _normalize_color_theme(value: str | None) -> str:
    theme = (value or "blue").strip().lower()
    return theme if theme in VALID_COLOR_THEMES else "blue"


def _fixed_thanks_scene() -> dict:
    return {
        "slug": "thanks-for-watching",
        "headline": "Thanks for watching",
        "hook": FIXED_THANKS_HOOK,
        "narration": FIXED_THANKS_NARRATION,
        "layout": "thanks",
        "visual_goal": "Show a simple closing thank-you card.",
        "key_points": [],
        "visual_items": [],
        "highlight_terms": [],
        "equations": [],
        "takeaway": "",
    }


def _norm_for_compare(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _is_distinct_text(candidate: str, *others: str) -> bool:
    cand = _norm_for_compare(candidate)
    if not cand:
        return False
    for other in others:
        oth = _norm_for_compare(other)
        if not oth:
            continue
        if cand == oth or cand in oth or oth in cand:
            return False
    return True


def _looks_like_narration_fragment(item: str, narration: str) -> bool:
    if not item:
        return True
    text = item.strip()
    if len(text) >= 6 and text.rstrip().endswith((",", ";", "-", "—", "–")):
        return True
    n_item = _norm_for_compare(text)
    n_narration = _norm_for_compare(narration)
    if n_item and n_narration and len(n_item) >= 30 and n_item in n_narration:
        return True
    return False


def _filter_visual_strings(values, narration: str, *, exclude=()):
    seen = {_norm_for_compare(v) for v in exclude if v}
    cleaned = []
    for v in values or []:
        text = (str(v) or "").strip()
        if not text:
            continue
        norm = _norm_for_compare(text)
        if norm in seen or _looks_like_narration_fragment(text, narration):
            continue
        seen.add(norm)
        cleaned.append(text)
    return cleaned


def _truncate_clean(value: str, limit: int) -> str:
    value = (value or "").strip()
    if len(value) <= limit:
        return value
    cut = value[:limit].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0].rstrip()
    return cut.rstrip(",;:.-")


def _normalize_explanation_level(value: str | None) -> str:
    aliases = {
        "beginner": "high_school",
        "intermediate": "college",
        "advanced": "expert",
    }
    level = (value or "high_school").strip().lower()
    level = aliases.get(level, level)
    return level if level in VALID_EXPLANATION_LEVELS else "high_school"


def _build_storyboard_prompt(job: dict) -> str:
    content_scenes = _target_content_scene_count(int(job["duration_seconds"]))
    total_scenes = content_scenes + 2  # title_card + content + summary; app appends thanks.
    total_words = int(round(job["duration_seconds"] * 2.5))
    per_scene_words = max(35, int(round(total_words / max(content_scenes + 1, 1))))
    research = (job.get("research") or "").strip()
    level = _normalize_explanation_level(job.get("explanation_level"))
    level_guidance = _EXPLANATION_LEVEL_GUIDANCE[level]
    categories = ", ".join(VIDEO_CATEGORIES)
    return f"""
Return one JSON object only. No markdown. No prose.

Topic: {job["concept"]}
Research area: {research or "general"}
Level: {level} — {level_guidance}
Runtime target: {job["duration_seconds"]} seconds
Narration target: about {per_scene_words} words per scene, {total_words} words total
Category: choose one of {categories}

Top-level JSON keys, in this order:
title, summary, learning_objective, closing_takeaway, category, scenes, quiz

Scenes must be chronological and appear in viewing order:
1. `title_card`: title plus one short `hook`; empty `key_points`, `visual_items`, `highlight_terms`, `equations`; `takeaway` is "".
2. Scenes 2-{1 + content_scenes}: exactly {content_scenes} content scenes. Each scene teaches the next required idea in order. One idea per scene.
3. Scene {total_scenes}: `summary`. No new ideas. Include one `takeaway` and 2-3 `key_points`.

Use exactly {total_scenes} scenes. The app adds the final thank-you scene.

Allowed content layouts:
{content_layout_prompt()}

Scene fields:
- `slug`: short kebab-case id
- `headline`: specific Title Case title, max 48 characters (must fit one line)
- `hook`: short framing line, max 70 characters
- `narration`: what the viewer hears for this scene only
- `layout`: one allowed layout
- `visual_goal`: one sentence describing the frame
- `key_points`: short standalone display text, max 8 items
- `visual_items`: short labels only, max 6 items
- `highlight_terms`: 1-3 word concept labels, max 6 items
- `equations`: compact LaTeX strings, max 8 items
- `takeaway`: one sentence, max 80 characters
- `data_points`: only for charts; objects like {{"label": "A", "value": 42}}

Layout-specific requirements:
- `flow`: 3-4 ordered stage labels in `visual_items`; matching descriptions in `key_points`.
- `timeline`: 3-5 ordered milestone labels in `visual_items`; matching descriptions in `key_points`.
- `comparison`: exactly two thing-names in `visual_items` — these become the panel headers (e.g. ["Brushed Motor", "Brushless Motor"]). Required.
- `before_after`: exactly two state labels in `visual_items`.
- `equation`: 1-2 equations; symbol names in `highlight_terms`; definitions in matching `key_points`.
- `step_derivation`: 2-8 equation steps; short step names in `visual_items`.
- chart layouts: provide numeric `data_points`.
- Use `statement` as a default when no other visual layout fits naturally.

No repetition:
- Do not reuse or paraphrase the same phrase in `headline`, `hook`, `takeaway`, `key_points`, `visual_items`, or `highlight_terms`.
- Do not copy narration sentences into display fields.

Quiz comes after `scenes`:
- `quiz` must be an object: {{"questions": [...]}}.
- Generate exactly 5 questions after planning the scenes.
- Use key `prompt`, not `question`.
- Each question has exactly 4 choices and zero-based integer `answer`.
- Correct answers must be explicitly taught by the scenes.
- Do not write "according to the lesson" or "in the video".

Return valid JSON matching the schema.
""".strip()


def _repair_storyboard_candidate(raw: object, job: dict) -> object:
    if not isinstance(raw, dict):
        return raw

    storyboard = dict(raw)
    scenes = storyboard.get("scenes") if isinstance(storyboard.get("scenes"), list) else []
    title = str(storyboard.get("title") or job.get("concept") or "Lesson").strip()
    storyboard["title"] = title

    if not str(storyboard.get("summary") or "").strip():
        summary_scene = next((s for s in reversed(scenes) if isinstance(s, dict) and s.get("layout") == "summary"), None)
        storyboard["summary"] = str(
            (summary_scene or {}).get("takeaway")
            or (summary_scene or {}).get("narration")
            or f"A concise explanation of {title}."
        ).strip()

    if not str(storyboard.get("learning_objective") or "").strip():
        storyboard["learning_objective"] = f"Understand the core idea of {title} and apply it to the provided examples."

    if not str(storyboard.get("closing_takeaway") or "").strip():
        storyboard["closing_takeaway"] = str(storyboard.get("summary") or f"{title} has one core idea to remember.").strip()

    quiz = storyboard.get("quiz")
    if isinstance(quiz, list):
        quiz = {"questions": quiz}
    if isinstance(quiz, dict):
        questions = []
        for item in quiz.get("questions") or []:
            if not isinstance(item, dict):
                continue
            question = dict(item)
            if "prompt" not in question and "question" in question:
                question["prompt"] = question.pop("question")
            if "prompt" not in question and "text" in question:
                question["prompt"] = question.pop("text")
            questions.append(question)
        storyboard["quiz"] = {"questions": questions}

    return storyboard


def _order_storyboard_for_storage(storyboard: dict) -> dict:
    ordered_keys = (
        "title",
        "summary",
        "learning_objective",
        "closing_takeaway",
        "category",
        "color_theme",
        "scenes",
        "quiz",
    )
    ordered = {key: storyboard[key] for key in ordered_keys if key in storyboard}
    for key, value in storyboard.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _validate_storyboard_payload(storyboard: object, *, min_scenes: int) -> dict:
    if not isinstance(storyboard, dict):
        raise WorkflowError(f"Storyboard JSON must be an object, got {type(storyboard).__name__}.")
    for field in ("title", "summary", "learning_objective", "closing_takeaway"):
        if not str(storyboard.get(field) or "").strip():
            raise WorkflowError(f"Storyboard JSON must include `{field}`.")
    category = str(storyboard.get("category") or "").strip()
    if category not in VIDEO_CATEGORIES:
        raise WorkflowError("Storyboard JSON must include a valid category.")
    scenes = storyboard.get("scenes")
    if not isinstance(scenes, list):
        raise WorkflowError("Storyboard JSON must include a scenes array.")
    if len(scenes) < min_scenes:
        raise WorkflowError(f"Storyboard returned {len(scenes)} scenes, need at least {min_scenes}.")
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise WorkflowError(f"Scene {index} must be an object.")
    _normalize_quiz(storyboard.get("quiz") or {})
    return storyboard


class VideoWorkflow:
    def __init__(self) -> None:
        self.app = current_app
        self.tts = DeepgramTTSClient(self.app.config["DEEPGRAM_API_KEY"])

    def run(self, job_id: str) -> None:
        job = get_job(job_id)
        if job is None:
            return

        job_root = Path(self.app.config["JOBS_DIR"]) / job_id
        agent_dir = job_root / "agent"
        audio_dir = job_root / "audio"
        render_dir = job_root / "renders"
        clips_dir = job_root / "clips"
        final_dir = job_root / "final"
        for directory in (agent_dir, audio_dir, render_dir, clips_dir, final_dir):
            directory.mkdir(parents=True, exist_ok=True)

        try:
            self._require_tools()
            self._check_canceled(job_id)

            update_job(job_id, status="running", current_step="Starting job", error_message=None)
            add_log(job_id, "Renderer started.")

            self._set_state(job_id, status="running", current_step="Planning storyboard")
            storyboard = self._generate_storyboard(job, agent_dir)
            self._check_canceled(job_id)

            self._set_state(job_id, current_step="Synthesizing narration")
            storyboard = self._generate_audio(job, storyboard, audio_dir)
            self._check_canceled(job_id)

            self._set_state(job_id, current_step="Preparing scenes")
            code_path = self._build_scene_module(job, storyboard, agent_dir)
            self._check_canceled(job_id)

            final_video = self._render_and_assemble(job, storyboard, code_path, render_dir, clips_dir, final_dir)
            self._check_canceled(job_id)

            update_job(
                job_id,
                status="completed",
                current_step="Completed",
                video_path=str(final_video),
                completed_at=self._now(),
                error_message=None,
            )
            add_log(job_id, f"Final video ready: {final_video.name}")
        except (ClaudeCodeError, DeepgramError, MediaError, WorkflowError) as exc:
            latest = get_job(job_id)
            if latest and latest.get("status") == "canceled":
                update_job(job_id, current_step="Canceled", error_message="Stopped by user.")
                add_log(job_id, "Renderer stopped after cancellation.", level="warning")
                return
            update_job(job_id, status="failed", current_step="Failed", error_message=str(exc))
            add_log(job_id, f"Job failed: {exc}", level="error")
        except Exception as exc:
            update_job(job_id, status="failed", current_step="Failed", error_message=str(exc))
            add_log(job_id, f"Unexpected failure: {exc}", level="error")

    def _require_tools(self) -> None:
        missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
        if missing:
            raise WorkflowError(f"Missing required tools: {', '.join(missing)}")

    def _set_state(self, job_id: str, **fields) -> None:
        self._check_canceled(job_id)
        update_job(job_id, **fields)
        if "current_step" in fields:
            add_log(job_id, fields["current_step"])

    def _check_canceled(self, job_id: str) -> None:
        latest = get_job(job_id)
        if latest and latest.get("status") == "canceled":
            raise WorkflowError("Stopped by user.")

    def _generate_storyboard(self, job: dict, agent_dir: Path) -> dict:
        storyboard_path = agent_dir / "storyboard.json"
        min_scenes, max_scenes = _storyboard_scene_limits()
        add_log(
            job["id"],
            f"Claude storyboard: model {self.app.config['CLAUDE_CODE_MODEL']}",
        )
        prompt = _build_storyboard_prompt(job)
        last_error: Exception | None = None
        storyboard: dict | None = None
        token_usage: dict | None = None
        for attempt in range(2):
            attempt_path = agent_dir / f"storyboard.raw{attempt + 1}.json"
            attempt_prompt = prompt
            if attempt:
                attempt_prompt = (
                    f"{prompt}\n\n"
                    "Your previous response was invalid. Return one JSON object only. "
                    "The top-level value must be an object with title, summary, learning_objective, "
                    "closing_takeaway, category, scenes, and quiz. It must not be a list. "
                    "Quiz must be an object with a questions array, and each question uses the key prompt."
                )
                add_log(job["id"], f"Retrying storyboard after invalid JSON: {last_error}", level="warning")
            try:
                candidate, candidate_usage = run_claude_json(
                    prompt=attempt_prompt,
                    workdir=agent_dir,
                    output_path=attempt_path,
                    model=self.app.config["CLAUDE_CODE_MODEL"],
                    max_turns=self.app.config["CLAUDE_CODE_MAX_TURNS"],
                    permission_mode="default",
                    system_prompt=(
                        "Return only the requested JSON object. Do not return a plan, markdown, prose, "
                        "tool calls, or a top-level array."
                    ),
                )
                candidate = _repair_storyboard_candidate(candidate, job)
                storyboard = _validate_storyboard_payload(candidate, min_scenes=min_scenes)
                token_usage = candidate_usage
                break
            except (ClaudeCodeError, WorkflowError, ValueError) as exc:
                last_error = exc
        if storyboard is None or token_usage is None:
            raise WorkflowError(f"Storyboard generation returned invalid JSON: {last_error}")

        scenes = storyboard.get("scenes") or []
        if len(scenes) > max_scenes:
            scenes = scenes[:max_scenes]
            storyboard["scenes"] = scenes

        color_theme = _normalize_color_theme(job.get("color_theme"))
        storyboard["color_theme"] = color_theme
        storyboard["title"] = str(storyboard["title"]).strip()
        storyboard["summary"] = str(storyboard["summary"]).strip()
        storyboard["learning_objective"] = str(storyboard["learning_objective"]).strip()
        storyboard["closing_takeaway"] = str(storyboard["closing_takeaway"]).strip()
        category = _normalize_category(storyboard)
        quiz = _normalize_quiz(storyboard.get("quiz") or {})
        storyboard["category"] = category
        storyboard["quiz"] = {"questions": quiz}

        expected_scene_count = _target_content_scene_count(int(job["duration_seconds"])) + 2
        if len(scenes) > expected_scene_count:
            scenes = scenes[:expected_scene_count]
            storyboard["scenes"] = scenes

        # Force structural slots: first = title_card, last generated scene = summary.
        if scenes:
            scenes[0]["layout"] = "title_card"
        if len(scenes) >= 2:
            scenes[-1]["layout"] = "summary"

        if not scenes or scenes[-1].get("layout") != "thanks":
            scenes.append(_fixed_thanks_scene())
        else:
            scenes[-1].update(_fixed_thanks_scene())
        storyboard["scenes"] = scenes

        for index, scene in enumerate(scenes, start=1):
            if scene.get("layout") == "thanks":
                scene.update(_fixed_thanks_scene())
            headline = (scene.get("headline") or scene.get("title") or f"{job['concept']} part {index}").strip()
            scene["headline"] = _truncate_clean(headline, 48)
            scene["slug"] = _slugify(scene.get("slug") or scene["headline"] or f"scene-{index}")
            scene["class_name"] = _class_name(index, scene["slug"])

            scene["narration"] = (
                scene.get("narration")
                or f"This scene introduces {scene['headline']} as part of {job['concept']}."
            ).strip()

            hook_raw = (scene.get("hook") or "").strip()
            scene["hook"] = (
                _truncate_clean(hook_raw, 70)
                if _is_distinct_text(hook_raw, scene["headline"]) else ""
            )
            takeaway_raw = (scene.get("takeaway") or "").strip()
            scene["takeaway"] = (
                _truncate_clean(takeaway_raw, 80)
                if _is_distinct_text(takeaway_raw, scene["headline"], scene["hook"]) else ""
            )

            scene["visual_goal"] = (scene.get("visual_goal") or f"Show {scene['headline']}.").strip()
            layout = (scene.get("layout") or "auto").strip().lower() or "auto"
            if layout in ("axes", "axes_plot", "distribution", "bullets"):
                layout = "auto"
            if layout not in VALID_LAYOUTS:
                layout = "auto"
            scene["layout"] = layout
            scene["scene_variant"] = "basic"

            narration = scene["narration"]
            shown = (scene["headline"], scene["hook"], scene["takeaway"])

            highlight = _filter_visual_strings(scene.get("highlight_terms"), narration, exclude=shown)[:6]
            scene["highlight_terms"] = highlight or [scene["headline"]]
            scene["visual_items"] = _filter_visual_strings(
                scene.get("visual_items"), narration,
                exclude=shown + tuple(scene["highlight_terms"]),
            )[:6]
            scene["key_points"] = _filter_visual_strings(scene.get("key_points"), narration, exclude=shown)[:8]
            max_equations = 8 if scene["layout"] == "step_derivation" else 2
            equations = [str(eq).strip() for eq in (scene.get("equations") or []) if str(eq).strip()][:max_equations]
            scene["equations"] = equations
            data_points = []
            for point in scene.get("data_points") or []:
                if not isinstance(point, dict):
                    continue
                label = _truncate_clean(str(point.get("label") or ""), 28)
                try:
                    value = float(point.get("value"))
                except (TypeError, ValueError):
                    continue
                if label:
                    data_points.append({"label": label, "value": value})
                if len(data_points) >= 6:
                    break
            if data_points:
                scene["data_points"] = data_points
            else:
                scene.pop("data_points", None)
            if scene["layout"] == "thanks":
                class_name = scene["class_name"]
                scene_number = scene.get("scene_number")
                scene_total = scene.get("scene_total")
                scene.update(_fixed_thanks_scene())
                scene["class_name"] = class_name
                if scene_number is not None:
                    scene["scene_number"] = scene_number
                if scene_total is not None:
                    scene["scene_total"] = scene_total

        storyboard = _order_storyboard_for_storage(storyboard)
        storyboard_path.write_text(json.dumps(storyboard, indent=2), encoding="utf-8")

        update_job(
            job["id"],
            title=storyboard.get("title") or job["concept"],
            storyboard_path=str(storyboard_path),
            token_usage_json=json.dumps(token_usage),
            quiz_json=json.dumps({"status": "ready", "category": category, "questions": quiz}),
            topic_category=category,
        )
        add_log(job["id"], f"Storyboard ready: {len(scenes)} scenes, theme {color_theme}, level {_normalize_explanation_level(job.get('explanation_level'))}.")
        add_log(
            job["id"],
            f"Storyboard tokens: {token_usage['stage_totals']['storyboard']} (in {token_usage['input_tokens']} / out {token_usage['output_tokens']}).",
        )
        add_log(job["id"], f"Quiz included in storyboard ({len(quiz)} questions, category {category}).")
        return storyboard

    def _generate_audio(self, job: dict, storyboard: dict, audio_dir: Path) -> dict:
        for index, scene in enumerate(storyboard["scenes"], start=1):
            self._check_canceled(job["id"])
            output_path = audio_dir / f"{index:02d}_{scene['slug']}.mp3"
            duration = self.tts.synthesize(
                text=scene["narration"],
                output_path=output_path,
                model=job["voice_model"],
            )
            scene["audio_path"] = str(output_path)
            scene["target_duration_seconds"] = duration
            add_log(job["id"], f"Scene {index}/{len(storyboard['scenes'])} narration synthesized ({duration:.1f}s).")

        storyboard_file = Path(job.get("storyboard_path") or audio_dir.parent / "agent" / "storyboard.json")
        storyboard_file.write_text(json.dumps(storyboard, indent=2), encoding="utf-8")
        return storyboard

    def _build_scene_module(self, job: dict, storyboard: dict, agent_dir: Path) -> Path:
        module_path = agent_dir / "generated_scenes.py"
        build_manim_module(storyboard=storyboard, output_path=module_path)
        update_job(job["id"], code_path=str(module_path))
        add_log(job["id"], "Scene module prepared.")
        return module_path

    def _render_and_assemble(
        self, job: dict, storyboard: dict, module_path: Path,
        render_dir: Path, clips_dir: Path, final_dir: Path,
    ) -> Path:
        clip_paths = []
        clip_durations: list[float] = []
        for index, scene in enumerate(storyboard["scenes"], start=1):
            self._check_canceled(job["id"])
            self._set_state(job["id"], current_step=f"Rendering scene {index} of {len(storyboard['scenes'])}")
            add_log(job["id"], f"Rendering scene {index}: {scene['headline']}")
            scene_media_dir = render_dir / scene["slug"]
            silent_video = render_scene(
                module_path=module_path,
                class_name=scene["class_name"],
                media_dir=scene_media_dir,
            )
            clip_path = clips_dir / f"{index:02d}_{scene['slug']}.mp4"
            mux_video_with_audio(
                video_path=silent_video,
                audio_path=Path(scene["audio_path"]),
                output_path=clip_path,
            )
            try:
                clip_durations.append(probe_duration(clip_path))
            except MediaError:
                clip_durations.append(float(scene.get("target_duration_seconds") or 0) or 6.0)
            clip_paths.append(clip_path)
            add_log(job["id"], f"Scene {index} clip assembled.")
            self._check_canceled(job["id"])

        self._set_state(job["id"], current_step="Finalizing video")
        final_video = final_dir / f"{_slugify(job['concept'])}.mp4"
        concat_clips(clip_paths=clip_paths, output_path=final_video, workdir=final_dir)

        try:
            write_captions(
                scenes=storyboard["scenes"],
                output_path=final_dir / "captions.vtt",
                scene_durations=clip_durations,
            )
            add_log(job["id"], "Captions generated.")
        except Exception as exc:
            add_log(job["id"], f"Caption generation skipped: {exc}", level="warning")

        try:
            extract_thumbnail(
                video_path=final_video,
                output_path=final_dir / "thumbnail.jpg",
                title_duration=clip_durations[0] if clip_durations else None,
            )
            add_log(job["id"], "Thumbnail extracted.")
        except Exception as exc:
            add_log(job["id"], f"Thumbnail extraction skipped: {exc}", level="warning")

        return final_video

    def _now(self) -> str:
        from .repository import utc_now
        return utc_now()
