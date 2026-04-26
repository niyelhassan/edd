from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from flask import current_app

from .claude_code import ClaudeCodeError, run_claude_json
from .deepgram_tts import DeepgramError, DeepgramTTSClient
from .manim_builder import build_manim_module
from .media import MediaError, concat_clips, mux_video_with_audio, render_scene
from .repository import add_log, get_job, update_job


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
    return int(scenes.get("minItems", 1)), int(scenes.get("maxItems", 10))


def _target_scene_count(job: dict, *, min_scene_count: int, max_scene_count: int) -> int:
    duration_seconds = int(job["duration_seconds"])
    concept = f"{job.get('concept', '')} {job.get('research', '')}".lower()
    base = 2 if duration_seconds <= 75 else 4 if duration_seconds <= 210 else 5
    complexity_terms = (
        "proof",
        "derive",
        "derivation",
        "quantum",
        "tensor",
        "lagrangian",
        "fourier",
        "eigen",
        "entropy",
        "bayes",
        "stochastic",
        "multivariable",
    )
    if any(term in concept for term in complexity_terms):
        base += 1
    return max(min_scene_count, min(max_scene_count, base))


def _default_visual_theme(text: str) -> str:
    return "brand_light"


_VALID_LAYOUTS = {
    "auto",
    "title_card",
    "summary",
    "bullets",
    "concept_map",
    "equation",
    "distribution",
    "axes_plot",
    "comparison",
    "timeline",
    "flow",
    "orbit",
    "bar_chart",
    "process",
    "network",
    "wave",
    "vector_field",
}

_VALID_THEMES = {"brand_light", "brand_dark"}


def _normalize_theme(theme: str | None) -> str:
    if not theme:
        return "brand_light"
    theme = theme.strip().lower()
    if theme in _VALID_THEMES:
        return theme
    legacy_dark = {"midnight", "dark"}
    if theme in legacy_dark:
        return "brand_dark"
    return "brand_light"


def _default_scene_variant(_: int, __: str) -> str:
    return "basic"


def _normalize_short_list(values: list[str] | None, fallback: list[str], *, limit: int) -> list[str]:
    cleaned = [str(value).strip() for value in (values or []) if str(value).strip()]
    if not cleaned:
        cleaned = fallback[:]
    return cleaned[:limit]


def _truncate_clean(value: str, limit: int) -> str:
    value = (value or "").strip()
    if len(value) <= limit:
        return value
    cut = value[:limit].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0].rstrip()
    return cut.rstrip(",;:.-")


def _build_storyboard_prompt(job: dict) -> str:
    min_scene_count, max_scene_count = _storyboard_scene_limits()
    target_scene_count = _target_scene_count(job, min_scene_count=min_scene_count, max_scene_count=max_scene_count)
    total_words = int(job["duration_seconds"] * 2.0)
    research = (job.get("research") or "").strip()
    return f"""
You are storyboarding a short, visual-first explainer video for high school students doing research who need to understand a complex math or science concept in the context of their field.

Topic: {job["concept"]}
Research context: {research or "None provided. Use broad, stable background knowledge appropriate for an advanced high school student."}
Audience: {job["audience"]}
Target runtime: about {job["duration_seconds"]} seconds
Scene count: choose between {min_scene_count} and {max_scene_count}, with a target of {target_scene_count}.
Style notes: {job["style_notes"] or "Calm, confident, technically accurate. Visual focus, sparse text, no jargon without grounding."}

The video is rendered with Manim against a curated set of animated scene templates. Pick the layout that best fits each scene. The visual carries the idea — text on screen is supportive, never a transcript of the narration.

Available `layout` values and when to use each:
- `title_card`: opening scene only. Sets the topic with a kinetic title.
- `equation`: the scene is centered on a single short equation that the viewer should see and understand. Provide 1 (or at most 2) compact equations in `equations` and 1 to 3 short labels for the symbols in `highlight_terms`.
- `distribution`: any scene about probability, p-values, statistical significance, normal/Gaussian distributions, sampling. Use `highlight_terms` for axis labels and the tail label.
- `axes_plot`: a scene that needs an x-y plot of a function (growth, decay, sine wave, log, parabola). Put axis labels in `highlight_terms` and 1 to 3 named points in `visual_items`.
- `comparison`: side-by-side contrast. Put the two thing-names in `visual_items` (left, right) and traits in `key_points`.
- `timeline`: history, evolution, ordered milestones. Use `visual_items` for 3 to 4 short milestone labels.
- `flow`: pipelines, processes, transformations from input -> ... -> output. Use `visual_items` for 3 to 4 short stage names.
- `process`: numbered procedural steps (derivation, method, recipe). Use `key_points` for 2 to 4 step descriptions, each one short clause.
- `network`: graphs, neural networks, social networks, relationships. Use `visual_items` for 3 to 5 short node names.
- `wave`: waves, signals, oscillation, frequency, Fourier. Use `highlight_terms` for amplitude/frequency style annotations.
- `vector_field`: gradient, flow field, force field, velocity field.
- `concept_map`: a central idea with 3 supporting concepts (hub-and-spoke). Put the central concept first in `highlight_terms`, then 3 supporting concepts in `visual_items`.
- `orbit`: a central object with rotating satellites (planets/electrons/dependencies).
- `bar_chart`: ranking, percentages, magnitude comparison. Use `visual_items` for 2 to 4 category labels.
- `bullets`: fallback when nothing more visual fits. Use sparingly.
- `summary`: closing scene only. Crystallizes the takeaway. Put a strong one-line `takeaway` and 2 to 3 short `key_points`.

Requirements for the storyboard:
- Open with a `title_card` scene and close with a `summary` scene whenever the runtime allows.
- Each middle scene must pick a layout whose visual genuinely matches what the narration is teaching. Do not default to `bullets` or `concept_map` when a more topic-specific layout exists.
- The narration of each scene must describe what is on screen for that scene (and only that scene). If the visual is a distribution, the narration talks about that distribution. If the visual is an equation, the narration walks through that equation. The viewer should never hear about something the visual is not showing.
- Narration is 2 to 4 sentences, conversational, suitable for voiceover. Total narration near {total_words} words across the full video.
- On-screen text is sparse. Headlines must read like clean titles (Title Case is fine, but never SHOUTY ALL CAPS). Bullets, labels, and visual items are short phrases, not full sentences.
- All on-screen text must fit cleanly: headlines max 60 chars, bullets max 90 chars, visual items max 40 chars, highlight terms max 24 chars. Keep them well under those caps so wrapping looks natural.
- Use clean spacing and proper capitalization. No trailing colons, no truncated phrases, no abbreviations the viewer would not understand.
- Equations are compact LaTeX, 60 chars max. Prefer named symbols the narration also says aloud.
- `scene_variant` should always be `basic`.
- Pick `visual_theme`: `brand_light` (default, off-white background) or `brand_dark` (use sparingly, when the topic is explicitly about something nighttime or visually striking on dark, e.g. astronomy, deep space).
- Tie the example or framing to the research context whenever it is provided.
- Return only JSON matching the provided schema. No prose outside the schema.
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
        missing = []
        for tool in ("ffmpeg", "ffprobe"):
            if shutil.which(tool) is None:
                missing.append(tool)
        if missing:
            raise WorkflowError(f"Missing required tools: {', '.join(missing)}")

    def _set_state(self, job_id: str, **fields) -> None:
        update_job(job_id, **fields)
        if "current_step" in fields:
            add_log(job_id, fields["current_step"])

    def _generate_storyboard(self, job: dict, agent_dir: Path) -> dict:
        storyboard_path = agent_dir / "storyboard.json"
        min_scene_count, max_scene_count = _storyboard_scene_limits()
        add_log(
            job["id"],
            (
                "Claude Code planning: "
                f"model {self.app.config['CLAUDE_CODE_MODEL']}, "
                f"max turns {self.app.config['CLAUDE_CODE_MAX_TURNS'] or 'default'}"
            ),
        )
        storyboard, token_usage = run_claude_json(
            prompt=_build_storyboard_prompt(job),
            workdir=agent_dir,
            output_path=storyboard_path,
            model=self.app.config["CLAUDE_CODE_MODEL"],
            max_turns=self.app.config["CLAUDE_CODE_MAX_TURNS"],
        )
        scenes = storyboard.get("scenes") or []
        if not scenes:
            raise WorkflowError("Storyboard generation returned no scenes.")
        if len(scenes) < min_scene_count:
            raise WorkflowError(
                f"Storyboard returned {len(scenes)} scenes, but at least {min_scene_count} are required."
            )
        if len(scenes) > max_scene_count:
            add_log(
                job["id"],
                f"Storyboard returned {len(scenes)} scenes; trimming to {max_scene_count}.",
                level="warning",
            )
            scenes = scenes[:max_scene_count]
            storyboard["scenes"] = scenes

        storyboard["visual_theme"] = _normalize_theme(storyboard.get("visual_theme"))
        storyboard["title"] = storyboard.get("title") or job["concept"]
        storyboard["summary"] = storyboard.get("summary") or f"A concise explainer about {job['concept']}."
        storyboard["learning_objective"] = storyboard.get("learning_objective") or f"Understand the core idea behind {job['concept']}."
        storyboard["closing_takeaway"] = storyboard.get("closing_takeaway") or f"Use {job['concept']} by tracking the assumptions, changes, and result."

        for index, scene in enumerate(scenes, start=1):
            headline = (scene.get("headline") or scene.get("title") or f"{job['concept']} part {index}").strip()
            scene["headline"] = _truncate_clean(headline, 60)
            scene["slug"] = _slugify(scene.get("slug") or scene["headline"] or f"scene-{index}")
            scene["class_name"] = _class_name(index, scene["slug"])
            scene["hook"] = _truncate_clean(scene.get("hook") or scene.get("takeaway") or scene["headline"], 70)
            scene["takeaway"] = _truncate_clean(scene.get("takeaway") or scene["hook"], 90)
            scene["narration"] = (
                scene.get("narration")
                or f"This scene introduces {scene['headline']} as part of {job['concept']}. It focuses on the main relationship, a simple example, and why the idea matters for the full explanation."
            ).strip()
            scene["visual_goal"] = (
                scene.get("visual_goal")
                or f"Show {scene['headline']} with simple labels, arrows, and a compact comparison."
            ).strip()
            scene["layout"] = (scene.get("layout") or "auto").strip().lower() or "auto"
            if scene["layout"] == "axes":
                scene["layout"] = "axes_plot"
            if scene["layout"] not in _VALID_LAYOUTS:
                scene["layout"] = "auto"
            scene["scene_variant"] = scene.get("scene_variant") or _default_scene_variant(index, scene["layout"])
            if scene["scene_variant"] != "basic":
                scene["scene_variant"] = "basic"
            scene["highlight_terms"] = _normalize_short_list(
                scene.get("highlight_terms"),
                [scene["headline"]],
                limit=4,
            )
            scene["visual_items"] = _normalize_short_list(
                scene.get("visual_items"),
                [],
                limit=4,
            )
            scene["key_points"] = _normalize_short_list(
                scene.get("key_points"),
                [],
                limit=3,
            )
            scene["equations"] = _normalize_short_list(scene.get("equations"), [], limit=2)

        if len(scenes) != max_scene_count:
            add_log(
                job["id"],
                f"Using {len(scenes)} scenes for this job.",
                level="warning",
            )

        storyboard_path.write_text(json.dumps(storyboard, indent=2), encoding="utf-8")

        update_job(
            job["id"],
            title=storyboard.get("title") or job["concept"],
            storyboard_path=str(storyboard_path),
            token_usage_json=json.dumps(token_usage),
        )
        add_log(job["id"], f"Storyboard created with {len(scenes)} scenes.")
        add_log(job["id"], f"Lesson title: {storyboard.get('title', job['concept'])}")
        add_log(job["id"], f"Visual theme: {storyboard['visual_theme']}")
        add_log(
            job["id"],
            (
                "Claude Code tokens: "
                f"storyboard {token_usage['stage_totals']['storyboard']}, "
                f"scene prep/code {token_usage['stage_totals']['scene_prep_and_code']}, "
                f"other {token_usage['stage_totals']['other']}, "
                f"total {token_usage['total_tokens']}"
            ),
        )
        if token_usage["stage_totals"]["scene_prep_and_code"] == 0:
            add_log(job["id"], "Scene prep and code agent tokens: 0 (deterministic local builder, no agent call).")
        return storyboard

    def _generate_audio(self, job: dict, storyboard: dict, audio_dir: Path) -> dict:
        for index, scene in enumerate(storyboard["scenes"], start=1):
            filename = f"{index:02d}_{scene['slug']}.mp3"
            output_path = audio_dir / filename
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
        self,
        job: dict,
        storyboard: dict,
        module_path: Path,
        render_dir: Path,
        clips_dir: Path,
        final_dir: Path,
    ) -> Path:
        clip_paths = []
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
            clip_paths.append(clip_path)
            add_log(job["id"], f"Scene {index} clip assembled.")

        self._set_state(job["id"], current_step="Finalizing video")
        final_video = final_dir / f"{_slugify(job['concept'])}.mp4"
        concat_clips(clip_paths=clip_paths, output_path=final_video, workdir=final_dir)
        return final_video

    def _now(self) -> str:
        from .repository import utc_now

        return utc_now()
