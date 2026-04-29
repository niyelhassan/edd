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
from .question_generation import generate_quiz_from_storyboard
from .repository import add_log, get_job, update_job
from .template_registry import VALID_LAYOUTS, content_layout_prompt


VALID_COLOR_THEMES = ("blue", "violet", "green", "amber", "rose", "slate")
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
    if n_item and n_narration and len(n_item) >= 12 and n_item in n_narration:
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


def _build_storyboard_prompt(job: dict) -> str:
    min_scenes, max_scenes = _storyboard_scene_limits()
    content_scenes = _target_content_scene_count(int(job["duration_seconds"]))
    total_scenes = content_scenes + 2  # title_card + content + summary; app appends thanks.
    total_words = int(round(job["duration_seconds"] * 2.5))
    per_scene_words = max(35, int(round(total_words / max(content_scenes + 1, 1))))
    research = (job.get("research") or "").strip()
    return f"""
You are storyboarding a short, visual-first explainer video for advanced high school students.

Topic: {job["concept"]}
Research context: {research or "None provided. Use stable background knowledge appropriate for an advanced high school student."}
Target runtime: about {job["duration_seconds"]} seconds.
Total scenes: exactly {total_scenes} ({content_scenes} content scenes between an opening title and closing key-takeaways scene).

REQUIRED STRUCTURE (in order):
1. Scene 1 — `title_card`: lesson title with one short framing line in `hook`. Empty `key_points`, `visual_items`, `equations`. Set `takeaway` to "".
2. Scenes 2..{1 + content_scenes} — content scenes that each teach one distinct visual idea. Choose the layout that best reveals the visual idea — not the safest choice.
3. Scene {2 + content_scenes} — `summary`: bold one-sentence `takeaway` plus 2–3 short `key_points` that crystallize the lesson. No new material.

Do not create a thank-you or sign-off scene. The application adds the fixed closing card after this storyboard.

Available content layouts (pick the one that matches the visual idea):
{content_layout_prompt()}

LAYOUT DIVERSITY — CRITICAL:
- No two content scenes may use the same layout. Every content scene must have a different layout type.
- `bullets` is an emergency fallback only — avoid it whenever a more visual layout fits.
- `statement` is the right choice for one powerful insight, principle, or memorable definition — use it at least once when the topic has a central idea worth stating boldly.
- Use charts (`bar_chart`, `line_chart`, `proportional_chart`) whenever there are quantitative comparisons or distributions.
- Use `flow` or `timeline` for any sequential process or historical progression.
- Mix diagram layouts (`network`, `cause_effect`) with equation and chart layouts to vary visual rhythm.

VISUAL STYLE:
- Each scene is a polished 16:9 research explainer frame: off-white background, dark slate typography, accent color, thin bottom rule, white cards, generous spacing.
- Labels must be short and slide-ready — they appear as visual elements, not prose.
- For `statement`: put the key insight in `takeaway`, the eyebrow label in `highlight_terms[0]`, and 1–2 supporting clauses in `key_points`.
- For `flow`: provide concise 2–5 word labels as `visual_items` and matching one-line descriptions as `key_points`.
- For `timeline` / `network` / `cause_effect`: provide concise 2–5 word labels as `visual_items` that read well as node text. For `network`, use `highlight_terms[0]` as the center node and `key_points` as child descriptions.
- For `comparison` / `before_after`: provide exactly two short labels as `visual_items[0]` and `visual_items[1]`.
- For `equation`: provide compact LaTeX in `equations`; symbol/component meanings as `highlight_terms`; short definitions may go in `key_points`.
- For `step_derivation`: provide up to 6 compact LaTeX lines in `equations` and short step labels in `visual_items`.
- For charts: use `data_points` with concrete labels and values whenever the topic supports them; keep labels under 20 chars and include a short interpretation in `takeaway` or `key_points`.
- Headlines must be specific and descriptive — no generic "Introduction" or "Overview". Each headline should stand alone as a meaningful title.

CONTENT REQUIREMENTS:
- Each content scene teaches exactly one visual idea; narration describes only what is on screen for that scene.
- Aim for {per_scene_words} words of narration per scene; total near {total_words} words.
- ZERO REPETITION: `headline`, `hook`, `takeaway`, every entry of `key_points`, `visual_items`, `highlight_terms` must be distinct phrases — no paraphrases or substring matches across any field.
- `headline`: Title Case, max 60 chars, never repeats anything from `hook` or `takeaway`.
- `hook`: one short framing line, distinct from `headline`, max 70 chars.
- `takeaway`: one sentence, distinct from `headline` and `hook`, max 90 chars.
- `visual_items`: short noun-phrase labels only (max 40 chars each). Never sentences, never narration fragments, never end in punctuation.
- `key_points`: short standalone clauses (max 90 chars each), never substrings of `narration`.
- `highlight_terms`: 1–3 word concept names (max 24 chars). No filler like "Topic" or "Concept".
- `equations`: compact LaTeX, max 80 chars. Up to 6 for `step_derivation`; 1–2 for `equation`.
- `data_points` must be {{"label": "Short Label", "value": 42.0}} with numeric values.
- Build the lesson so the viewer leaves able to answer concrete questions — name specific quantities, contrasts, or misconceptions worth quizzing.
- Tie all examples to the research context when provided.
- Return ONLY JSON matching the provided schema. No prose outside the schema.
""".strip()


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

            update_job(job_id, status="running", current_step="Starting job", error_message=None)
            add_log(job_id, "Worker started.")

            self._set_state(job_id, status="running", current_step="Planning storyboard")
            storyboard = self._generate_storyboard(job, agent_dir)

            # Now that we have the storyboard, kick off the quiz: it can be answered
            # directly from what the video is going to teach.
            self._generate_quiz(job, storyboard, agent_dir)

            self._set_state(job_id, current_step="Synthesizing narration")
            storyboard = self._generate_audio(job, storyboard, audio_dir)

            self._set_state(job_id, current_step="Preparing scenes")
            code_path = self._build_scene_module(job, storyboard, agent_dir)

            final_video = self._render_and_assemble(job, storyboard, code_path, render_dir, clips_dir, final_dir)

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
        update_job(job_id, **fields)
        if "current_step" in fields:
            add_log(job_id, fields["current_step"])

    def _generate_storyboard(self, job: dict, agent_dir: Path) -> dict:
        storyboard_path = agent_dir / "storyboard.json"
        min_scenes, max_scenes = _storyboard_scene_limits()
        add_log(
            job["id"],
            f"Claude planning: model {self.app.config['CLAUDE_CODE_MODEL']}",
        )
        storyboard, token_usage = run_claude_json(
            prompt=_build_storyboard_prompt(job),
            workdir=agent_dir,
            output_path=storyboard_path,
            model=self.app.config["CLAUDE_CODE_MODEL"],
            max_turns=self.app.config["CLAUDE_CODE_MAX_TURNS"],
        )
        scenes = storyboard.get("scenes") or []
        if len(scenes) < min_scenes:
            raise WorkflowError(f"Storyboard returned {len(scenes)} scenes, need at least {min_scenes}.")
        if len(scenes) > max_scenes:
            scenes = scenes[:max_scenes]
            storyboard["scenes"] = scenes

        color_theme = _normalize_color_theme(job.get("color_theme"))
        storyboard["color_theme"] = color_theme
        storyboard["title"] = storyboard.get("title") or job["concept"]
        storyboard["summary"] = storyboard.get("summary") or f"A concise explainer about {job['concept']}."
        storyboard["learning_objective"] = storyboard.get("learning_objective") or f"Understand the core idea behind {job['concept']}."
        storyboard["closing_takeaway"] = storyboard.get("closing_takeaway") or f"Use {job['concept']} by tracking the assumptions, changes, and result."

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
            scene["headline"] = _truncate_clean(headline, 60)
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
                _truncate_clean(takeaway_raw, 90)
                if _is_distinct_text(takeaway_raw, scene["headline"], scene["hook"]) else ""
            )

            scene["visual_goal"] = (scene.get("visual_goal") or f"Show {scene['headline']}.").strip()
            layout = (scene.get("layout") or "auto").strip().lower() or "auto"
            if layout == "axes":
                layout = "axes_plot"
            if layout not in VALID_LAYOUTS:
                layout = "auto"
            scene["layout"] = layout
            scene["scene_variant"] = "basic"

            narration = scene["narration"]
            shown = (scene["headline"], scene["hook"], scene["takeaway"])

            highlight = _filter_visual_strings(scene.get("highlight_terms"), narration, exclude=shown)[:4]
            scene["highlight_terms"] = highlight or [scene["headline"]]
            scene["visual_items"] = _filter_visual_strings(
                scene.get("visual_items"), narration,
                exclude=shown + tuple(scene["highlight_terms"]),
            )[:5]
            scene["key_points"] = _filter_visual_strings(scene.get("key_points"), narration, exclude=shown)[:5]
            max_equations = 6 if scene["layout"] == "step_derivation" else 2
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

        storyboard_path.write_text(json.dumps(storyboard, indent=2), encoding="utf-8")

        update_job(
            job["id"],
            title=storyboard.get("title") or job["concept"],
            storyboard_path=str(storyboard_path),
            token_usage_json=json.dumps(token_usage),
        )
        add_log(job["id"], f"Storyboard ready: {len(scenes)} scenes, theme {color_theme}.")
        add_log(
            job["id"],
            f"Storyboard tokens: {token_usage['stage_totals']['storyboard']} (in {token_usage['input_tokens']} / out {token_usage['output_tokens']}).",
        )
        return storyboard

    def _generate_quiz(self, job: dict, storyboard: dict, agent_dir: Path) -> None:
        quiz_dir = agent_dir.parent / "quiz"
        quiz_dir.mkdir(parents=True, exist_ok=True)
        try:
            quiz, usage = generate_quiz_from_storyboard(
                concept=job["concept"],
                research=job.get("research") or "",
                storyboard=storyboard,
                workdir=quiz_dir,
                output_path=quiz_dir / "questions.json",
                model=self.app.config["CLAUDE_QUESTION_MODEL"],
            )
        except Exception as exc:
            update_job(job["id"], quiz_json=json.dumps({"status": "error", "error": str(exc)}))
            add_log(job["id"], f"Question generation failed: {exc}", level="error")
            return

        update_job(
            job["id"],
            quiz_json=json.dumps({"status": "ready", "questions": quiz}),
            quiz_token_usage_json=json.dumps(usage),
        )
        add_log(
            job["id"],
            f"Quiz ready ({self.app.config['CLAUDE_QUESTION_MODEL']}, {usage.get('total_tokens', 0)} tokens).",
        )

    def _generate_audio(self, job: dict, storyboard: dict, audio_dir: Path) -> dict:
        for index, scene in enumerate(storyboard["scenes"], start=1):
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
