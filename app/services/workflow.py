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


_VALID_THEMES = {"light", "dark", "paper"}
_VALID_LAYOUTS = {
    "auto",
    "title_card",
    "bullets",
    "equation",
    "distribution",
    "axes",
    "comparison",
    "flow",
    "concept_map",
    "timeline",
    "bar_chart",
    "wave",
    "tree",
    "scatter",
    "process",
    "summary",
}


def _default_visual_theme(text: str) -> str:
    return "light"


def _normalize_short_list(values: list[str] | None, fallback: list[str], *, limit: int) -> list[str]:
    cleaned = [str(value).strip() for value in (values or []) if str(value).strip()]
    if not cleaned:
        cleaned = fallback[:]
    return cleaned[:limit]


def _build_storyboard_prompt(job: dict) -> str:
    min_scene_count, max_scene_count = _storyboard_scene_limits()
    target_scene_count = _target_scene_count(job, min_scene_count=min_scene_count, max_scene_count=max_scene_count)
    total_words = int(job["duration_seconds"] * 2.2)
    research = (job.get("research") or "").strip()
    return f"""
You are designing a short explainer video for a high-school student doing research.
The video must build genuine intuition for a complex math or science concept by tying every visual to a vivid, topic-specific picture from the student's research field.

Topic: {job["concept"]}
Research context: {research or "Not provided. Use stable, broadly known background knowledge for this audience."}
Audience: {job["audience"]}
Target runtime: about {job["duration_seconds"]} seconds total
Scene count: between {min_scene_count} and {max_scene_count} (target {target_scene_count})
Style notes: {job["style_notes"] or "Crisp, technical, friendly. Speak to a curious 16-year-old researcher."}

== Renderer ==
Each scene is rendered by an animated Manim template chosen from this fixed library.
Pick the template per scene with the `layout` field. Each template uses the listed fields.

  - title_card        Opening hero. Big animated title, accent underline, subtitle from `hook`.
                      Use ONLY for scene 1.
  - bullets           Numbered, animated 2-3 bullets from `key_points`.
  - equation          Centered LaTeX from `equations[0]`, optional `equations[1]` below,
                      annotation chips from `highlight_terms`. Best for one core formula.
  - distribution      Bell curve with shaded tail. For p-values, sigma, normal/Gaussian.
                      `highlight_terms[0]` = x-axis label, `highlight_terms[1]` = tail label.
  - axes              Plotted curve on Cartesian axes with up to 3 labeled points from
                      `visual_items`. Good for functions, growth, dose-response.
  - comparison        Two side-by-side cards from `visual_items[0..1]` with subtitles
                      from `highlight_terms[0..1]`. Use for contrasts.
  - flow              3-4 step pipeline from `visual_items` connected by arrows.
                      Use for procedures, algorithms, transformations.
  - concept_map       Central node from `highlight_terms[0]` with 3-4 satellites from
                      `visual_items`. Use to relate parts to a whole.
  - timeline          Horizontal milestones from `visual_items`. Use for chronology.
  - bar_chart         Comparative bars from `visual_items` (categorical labels). Heights
                      are auto-generated; only use when relative magnitudes are the point.
  - wave              Two sine waves with labels from `highlight_terms[0..1]`. Use for
                      physics waves, signals, harmonics, interference.
  - tree              Branching tree (root + 2-3 branches) from `highlight_terms[0]`
                      and `visual_items`. Use for Bayes/decision/probability trees.
  - scatter           Scatter plot with linear fit, axes labelled by `highlight_terms`.
                      Use for regression, correlation, lab data.
  - process           Numbered vertical steps from `key_points`. Each item may use
                      "Title: detail" syntax to split a bold title from a body.
  - summary           Closing key takeaway: big `takeaway` text + check-marked bullets
                      from `key_points`. Use ONLY for the final scene.

== Hard rules ==
- Pick the template that best matches the actual content of each scene. Do NOT default everything to `bullets`.
- Use distinct templates across scenes; avoid using the same template twice in a row.
- Scene 1 should be `title_card`. The final scene should be `summary`.
- `highlight_terms` values must literally be the labels you want printed on screen
  (axis labels, chip labels, tail label, root label, etc.). Keep them under 4 words.
- `visual_items` are the specific labels the chosen template draws (bullet labels,
  flow nodes, comparison cards, scatter axes points, etc.). Use the exact labels you
  want shown — short noun phrases, not sentences. Capitalize like normal English (Sentence case, not Title Case).
- `key_points` are full short phrases (5-90 chars) used for `bullets`, `process`, `summary`.
- For `equation`, write the formula as valid LaTeX (no dollar-sign wrappers). Example: `P(A\\mid B)=\\frac{{P(B\\mid A)P(A)}}{{P(B)}}`.
- For `process`, format each `key_points` entry as `Step name: short detail.` so the
  template can split title and body.
- The narration MUST explicitly reference the items shown on screen (using their
  `visual_items` / `highlight_terms` words), so audio and visuals reinforce each other.
- Narration: 2 to 4 natural spoken sentences per scene; total around {total_words} words.
- Do not repeat the headline verbatim in `hook` or `takeaway`. Each adds new information.
- Headlines: max 60 chars, written in Sentence case, no trailing punctuation.
- Hooks: max 90 chars, a one-line subtitle that adds context.
- Takeaways: max 110 chars, a one-line caption shown under the visual.
- No emojis. No markdown. No quotes around plain text.

== Visual theme ==
Pick ONE `visual_theme` from: light, dark, paper.
- `light`  : white background, dark text, blue accent (default).
- `dark`   : near-black background, off-white text, blue accent. For physics, astronomy, signals.
- `paper`  : warm off-white, sepia tone. For history-of-science, biology, classical topics.

== Schema ==
Return only JSON matching the provided schema. No prose, no code fences.
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

        proposed_theme = (storyboard.get("visual_theme") or "").strip()
        storyboard["visual_theme"] = proposed_theme if proposed_theme in _VALID_THEMES else _default_visual_theme(
            storyboard.get("title") or job["concept"]
        )
        storyboard["title"] = storyboard.get("title") or job["concept"]
        storyboard["summary"] = storyboard.get("summary") or f"A concise explainer about {job['concept']}."
        storyboard["learning_objective"] = storyboard.get("learning_objective") or f"Understand the core idea behind {job['concept']}."
        storyboard["closing_takeaway"] = storyboard.get("closing_takeaway") or f"Use {job['concept']} by tracking the assumptions, changes, and result."

        for index, scene in enumerate(scenes, start=1):
            headline = (scene.get("headline") or scene.get("title") or f"{job['concept']} part {index}").strip()
            scene["headline"] = headline[:60]
            scene["slug"] = _slugify(scene.get("slug") or scene["headline"] or f"scene-{index}")
            scene["class_name"] = _class_name(index, scene["slug"])
            scene["hook"] = (scene.get("hook") or scene.get("takeaway") or scene["headline"]).strip()[:70]
            scene["takeaway"] = (scene.get("takeaway") or scene["hook"]).strip()[:90]
            scene["narration"] = (
                scene.get("narration")
                or f"This scene introduces {scene['headline']} as part of {job['concept']}. It focuses on the main relationship, a simple example, and why the idea matters for the full explanation."
            ).strip()
            scene["visual_goal"] = (
                scene.get("visual_goal")
                or f"Show {scene['headline']} with simple labels, arrows, and a compact comparison."
            ).strip()
            scene["layout"] = (scene.get("layout") or "auto").strip() or "auto"
            if scene["layout"] not in _VALID_LAYOUTS:
                scene["layout"] = "auto"
            scene["scene_number"] = index
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
