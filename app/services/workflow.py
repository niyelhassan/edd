from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from flask import current_app

from .codex_cli import CodexCliError, run_codex_json
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


def _default_visual_theme(text: str) -> str:
    themes = ["blueprint", "chalk", "lab", "signal", "midnight", "sunset"]
    return themes[sum(ord(ch) for ch in text) % len(themes)]


def _default_scene_variant(index: int, layout: str) -> str:
    if index == 1:
        return "hero"
    if layout == "comparison":
        return "compare"
    if layout == "axes":
        return "spotlight"
    if layout == "orbit":
        return "orbit"
    if layout == "timeline":
        return "magazine"
    if index == 3:
        return "grid"
    return "stage" if index % 2 == 0 else "split"


def _normalize_short_list(values: list[str] | None, fallback: list[str], *, limit: int) -> list[str]:
    cleaned = [str(value).strip() for value in (values or []) if str(value).strip()]
    if not cleaned:
        cleaned = fallback[:]
    return cleaned[:limit]


def _build_storyboard_prompt(job: dict) -> str:
    _, scene_count = _storyboard_scene_limits()
    total_words = int(job["duration_seconds"] * 2.0)
    return f"""
Create a concise but high-quality explainer-video plan for a high school student.

Topic: {job["concept"]}
Audience: {job["audience"]}
Target runtime: about {job["duration_seconds"]} seconds
Scene count: exactly {scene_count}
Style notes: {job["style_notes"] or "Use a calm, clear academic tone with strong visual intuition."}

Requirements:
- Explain the idea accurately, but with the pacing of a strong teacher.
- Use exactly {scene_count} scenes.
- Keep total narration near {total_words} words.
- Each scene narration should be natural for voiceover and 2 to 4 sentences long.
- Headlines and on-screen items must be short enough to fit cleanly on screen.
- Visual goals must be specific enough for deterministic Manim layouts.
- Pick one overall `visual_theme` from: blueprint, chalk, lab, signal, midnight, sunset.
- Use a mix of layout types from: concept_map, equation, comparison, axes, timeline, flow, orbit.
- Vary `scene_variant` across scenes using: hero, split, spotlight, compare, grid, stage, orbit, magazine.
- Prefer intuition first, then formalism, then a compact takeaway.
- Include at most 2 equations per scene and keep them short.
- `visual_items`, `highlight_terms`, and `key_points` must be compact phrases, not long sentences.
- `hook` must be a short on-screen prompt or framing line and must not repeat the narration sentence-for-sentence.
- `takeaway` must be one short sentence that works as an on-screen summary.
- On-screen text should complement the voiceover, not duplicate it verbatim.
- Put strong emphasis on visuals, spatial relationships, and animation beats. The graphics should explain the concept even with muted audio.
- Avoid overusing cards, panels, boxed labels, or dense bullet stacks.
- Use open compositions that leave room for motion and concept-specific diagrams.

Return only JSON matching the provided schema.
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
        codex_dir = job_root / "codex"
        audio_dir = job_root / "audio"
        render_dir = job_root / "renders"
        clips_dir = job_root / "clips"
        final_dir = job_root / "final"
        for directory in (codex_dir, audio_dir, render_dir, clips_dir, final_dir):
            directory.mkdir(parents=True, exist_ok=True)

        try:
            self._require_tools()

            update_job(job_id, status="running", current_step="Starting job", error_message=None)
            add_log(job_id, "Worker started.")

            self._set_state(job_id, status="running", current_step="Generating storyboard")
            storyboard = self._generate_storyboard(job, codex_dir)

            self._set_state(job_id, current_step="Synthesizing narration")
            storyboard = self._generate_audio(job, storyboard, audio_dir)

            self._set_state(job_id, current_step="Preparing scenes")
            code_path = self._build_scene_module(job, storyboard, codex_dir)

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
        except (CodexCliError, DeepgramError, MediaError, WorkflowError) as exc:
            update_job(job_id, status="failed", current_step="Failed", error_message=str(exc))
            add_log(job_id, f"Job failed: {exc}", level="error")
        except Exception as exc:
            update_job(job_id, status="failed", current_step="Failed", error_message=str(exc))
            add_log(job_id, f"Unexpected failure: {exc}", level="error")

    def _require_tools(self) -> None:
        missing = []
        for tool in ("codex", "ffmpeg", "ffprobe"):
            if shutil.which(tool) is None:
                missing.append(tool)
        if missing:
            raise WorkflowError(f"Missing required tools: {', '.join(missing)}")

    def _set_state(self, job_id: str, **fields) -> None:
        update_job(job_id, **fields)
        if "current_step" in fields:
            add_log(job_id, fields["current_step"])

    def _generate_storyboard(self, job: dict, codex_dir: Path) -> dict:
        storyboard_path = codex_dir / "storyboard.json"
        min_scene_count, max_scene_count = _storyboard_scene_limits()
        storyboard = run_codex_json(
            prompt=_build_storyboard_prompt(job),
            workdir=codex_dir,
            output_path=storyboard_path,
            model=self.app.config["CODEX_MODEL"],
            reasoning_effort=self.app.config["CODEX_REASONING_EFFORT"],
            schema_path=_storyboard_schema_path(),
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

        storyboard["visual_theme"] = storyboard.get("visual_theme") or _default_visual_theme(
            storyboard.get("title") or job["concept"]
        )

        for index, scene in enumerate(scenes, start=1):
            scene["slug"] = _slugify(scene.get("slug") or scene.get("headline") or f"scene-{index}")
            scene["class_name"] = _class_name(index, scene["slug"])
            scene["hook"] = (scene.get("hook") or scene.get("takeaway") or scene["headline"]).strip()
            scene["scene_variant"] = scene.get("scene_variant") or _default_scene_variant(index, scene.get("layout", "concept_map"))
            scene["highlight_terms"] = _normalize_short_list(
                scene.get("highlight_terms"),
                [scene["headline"], scene["hook"]],
                limit=4,
            )
            scene["visual_items"] = _normalize_short_list(
                scene.get("visual_items"),
                scene["highlight_terms"],
                limit=4,
            )
            scene["key_points"] = _normalize_short_list(
                scene.get("key_points"),
                [scene.get("takeaway", "Key idea"), scene.get("visual_goal", "See the pattern")],
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
        )
        add_log(job["id"], f"Storyboard created with {len(scenes)} scenes.")
        add_log(job["id"], f"Lesson title: {storyboard.get('title', job['concept'])}")
        add_log(job["id"], f"Visual theme: {storyboard['visual_theme']}")
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

        storyboard_file = Path(job.get("storyboard_path") or audio_dir.parent / "codex" / "storyboard.json")
        storyboard_file.write_text(json.dumps(storyboard, indent=2), encoding="utf-8")
        return storyboard

    def _build_scene_module(self, job: dict, storyboard: dict, codex_dir: Path) -> Path:
        module_path = codex_dir / "generated_scenes.py"
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
                quality=job["render_quality"],
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
