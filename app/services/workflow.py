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


LAYOUT_OPTIONS = {
    "auto",
    "concept_map",
    "equation",
    "comparison",
    "axes",
    "timeline",
    "flow",
    "orbit",
    "matrix",
    "distribution",
    "geometry",
    "vector",
    "bridge",
    "feedback",
    "lab",
}

SCENE_TEMPLATES = [
    "hero_reveal",
    "concept_network",
    "equation_build",
    "graph_discovery",
    "before_after",
    "process_flow",
    "timeline_story",
    "orbit_system",
    "lab_experiment",
    "probability_grid",
    "distribution_curve",
    "geometry_proof",
    "vector_field",
    "feedback_loop",
    "research_bridge",
]

SCENE_TEMPLATE_BY_LAYOUT = {
    "concept_map": "concept_network",
    "equation": "equation_build",
    "comparison": "before_after",
    "axes": "graph_discovery",
    "timeline": "timeline_story",
    "flow": "process_flow",
    "orbit": "orbit_system",
    "matrix": "probability_grid",
    "distribution": "distribution_curve",
    "geometry": "geometry_proof",
    "vector": "vector_field",
    "bridge": "research_bridge",
    "feedback": "feedback_loop",
    "lab": "lab_experiment",
}

SCENE_TEMPLATE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("probability_grid", ("probability", "bayes", "chance", "odds", "sample", "combinator")),
    ("distribution_curve", ("distribution", "variance", "normal", "gaussian", "histogram", "standard deviation")),
    ("vector_field", ("vector", "gradient", "field", "flux", "direction", "phase")),
    ("geometry_proof", ("geometry", "triangle", "angle", "proof", "theorem", "circle")),
    ("lab_experiment", ("experiment", "reaction", "molecule", "chemical", "cell", "enzyme", "lab")),
    ("orbit_system", ("orbit", "planet", "electron", "nucleus", "gravity", "rotation")),
    ("feedback_loop", ("feedback", "loop", "cycle", "control", "homeostasis", "regulation")),
    ("research_bridge", ("research", "question", "hypothesis", "evidence", "result", "study")),
    ("graph_discovery", ("graph", "plot", "trend", "slope", "regression", "correlation")),
    ("process_flow", ("process", "algorithm", "pipeline", "method", "steps")),
]

STOPWORDS = {
    "about",
    "across",
    "after",
    "also",
    "and",
    "are",
    "around",
    "because",
    "been",
    "being",
    "between",
    "both",
    "could",
    "does",
    "each",
    "from",
    "have",
    "into",
    "just",
    "more",
    "most",
    "much",
    "over",
    "part",
    "same",
    "should",
    "than",
    "that",
    "their",
    "them",
    "there",
    "these",
    "this",
    "those",
    "through",
    "using",
    "very",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "your",
}


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


def _normalize_spacing(value: str | None) -> str:
    text = str(value or "")
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2022", " ")
    return re.sub(r"\s+", " ", text).strip()


def _truncate_to_boundary(text: str, *, max_len: int) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    clipped = text[:max_len].rsplit(" ", 1)[0].strip()
    return (clipped or text[:max_len]).strip(" ,;:-")


def _normalize_caption(value: str | None, *, max_len: int) -> str:
    caption = _normalize_spacing(value)
    caption = _truncate_to_boundary(caption, max_len=max_len)
    caption = caption.strip(" ,;:-")
    if caption and caption[0].isalpha() and caption[0].islower():
        caption = caption[0].upper() + caption[1:]
    return caption


def _normalize_sentence(value: str | None, *, max_len: int, ensure_terminal: bool = True) -> str:
    sentence = _normalize_spacing(value)
    sentence = re.sub(r"\s+([,.;:!?])", r"\1", sentence)
    sentence = _truncate_to_boundary(sentence, max_len=max_len)
    if sentence and sentence[0].isalpha() and sentence[0].islower():
        sentence = sentence[0].upper() + sentence[1:]
    if ensure_terminal and sentence and sentence[-1] not in ".!?":
        sentence += "."
    return sentence


def _split_sentences(text: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", text) if segment.strip()]


def _normalize_short_list(
    values: list[str] | None,
    fallback: list[str],
    *,
    limit: int,
    max_len: int,
    capitalize: bool = True,
) -> list[str]:
    candidates = [*list(values or []), *list(fallback or [])]
    cleaned: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        item = _normalize_spacing(candidate)
        if not item:
            continue
        item = _truncate_to_boundary(item, max_len=max_len)
        if capitalize and item and item[0].isalpha() and item[0].islower():
            item = item[0].upper() + item[1:]
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
        if len(cleaned) >= limit:
            break
    return cleaned[:limit]


def _extract_keywords(text: str, *, limit: int) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+\-]{2,}", text.lower())
    keywords: list[str] = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        if token in keywords:
            continue
        keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def _keyword_to_term(word: str) -> str:
    if "-" in word:
        return "-".join(part.capitalize() if len(part) > 3 else part.upper() for part in word.split("-"))
    if len(word) <= 3:
        return word.upper()
    return word.capitalize()


def _target_scene_count(job: dict, *, min_scene_count: int, max_scene_count: int) -> int:
    duration_seconds = int(job["duration_seconds"])
    concept = f"{job.get('concept', '')} {job.get('research', '')}".lower()
    if duration_seconds <= 75:
        base = 3
    elif duration_seconds <= 210:
        base = 5
    else:
        base = 7
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
        "genetics",
        "regression",
    )
    if any(term in concept for term in complexity_terms):
        base += 1
    return max(min_scene_count, min(max_scene_count, base))


def _default_visual_theme(text: str) -> str:
    themes = ["blueprint", "chalk", "lab", "signal", "midnight", "sunset"]
    return themes[sum(ord(ch) for ch in text) % len(themes)]


def _default_scene_variant(index: int, layout: str, scene_context: str) -> str:
    if layout in SCENE_TEMPLATE_BY_LAYOUT:
        return SCENE_TEMPLATE_BY_LAYOUT[layout]
    lowered = scene_context.lower()
    for template, keywords in SCENE_TEMPLATE_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return template
    return SCENE_TEMPLATES[(index - 1) % len(SCENE_TEMPLATES)]


def _build_storyboard_prompt(job: dict) -> str:
    min_scene_count, max_scene_count = _storyboard_scene_limits()
    target_scene_count = _target_scene_count(job, min_scene_count=min_scene_count, max_scene_count=max_scene_count)
    total_words = int(job["duration_seconds"] * 2.3)
    research = (job.get("research") or "").strip()
    layout_list = ", ".join(sorted(LAYOUT_OPTIONS))
    template_list = ", ".join(SCENE_TEMPLATES)
    return f"""
Create a storyboard for a visual-first explainer video for high-school students doing research.

Topic: {job["concept"]}
Research context: {research or "None provided. Use broad, stable background knowledge only."}
Audience: {job["audience"]}
Target runtime: about {job["duration_seconds"]} seconds
Scene count: choose between {min_scene_count} and {max_scene_count}, with a target of {target_scene_count}
Style notes: {job["style_notes"] or "Clear, encouraging, visual-first, and technically correct."}

Requirements:
- Explain the concept in language a motivated high-school student can follow.
- Choose varied scene structures so the video does not feel static.
- Keep total narration near {total_words} words.
- Each scene narration should be 2 to 4 short sentences and must describe what changes on screen.
- Ensure narration and visual action directly match (what is spoken should be what is shown).
- Use concise on-screen text; avoid paragraph blocks.
- Keep capitalization and spacing clean for all text fields.
- Use one `layout` from: {layout_list}. Use `auto` when unsure.
- Use one `scene_variant` from: {template_list}. Reuse only when it clearly helps continuity.
- Include at most 2 short equations per scene.
- Keep visual_items and highlight_terms compact and concrete.
- Prefer concrete examples, then formal statement, then takeaway.
- Keep the output compact and return only valid JSON that matches the schema.

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

        storyboard["visual_theme"] = storyboard.get("visual_theme") or _default_visual_theme(
            storyboard.get("title") or job["concept"]
        )
        storyboard["title"] = _normalize_caption(storyboard.get("title") or job["concept"], max_len=80)
        storyboard["summary"] = _normalize_sentence(
            storyboard.get("summary") or f"A visual explanation of {job['concept']} for student researchers.",
            max_len=220,
        )
        storyboard["learning_objective"] = _normalize_sentence(
            storyboard.get("learning_objective") or f"Understand the key mechanism behind {job['concept']} and when to use it.",
            max_len=180,
        )
        storyboard["closing_takeaway"] = _normalize_sentence(
            storyboard.get("closing_takeaway") or f"Apply {job['concept']} by checking assumptions, evidence, and interpretation.",
            max_len=180,
        )

        concept_context = " ".join(
            [
                _normalize_spacing(job.get("concept")),
                _normalize_spacing(job.get("research")),
                _normalize_spacing(storyboard.get("summary")),
                _normalize_spacing(storyboard.get("learning_objective")),
            ]
        )

        for index, scene in enumerate(scenes, start=1):
            fallback_title = f"{_normalize_caption(job['concept'], max_len=42) or 'Concept'} Part {index}"
            headline = _normalize_caption(scene.get("headline") or scene.get("title") or fallback_title, max_len=60)
            scene["headline"] = headline or fallback_title
            scene["slug"] = _slugify(scene.get("slug") or scene["headline"] or f"scene-{index}")
            scene["class_name"] = _class_name(index, scene["slug"])

            scene["hook"] = _normalize_caption(
                scene.get("hook") or scene.get("takeaway") or scene["headline"],
                max_len=70,
            )

            fallback_takeaway = f"{scene['headline']} gives a usable interpretation for your research question."
            scene["takeaway"] = _normalize_sentence(
                scene.get("takeaway") or fallback_takeaway,
                max_len=90,
                ensure_terminal=False,
            )

            fallback_narration = (
                f"We start with {scene['headline']} in the context of {job['concept']}. "
                "Watch the visual as the relationship builds step by step, then connect that pattern to a practical research decision."
            )
            narration = _normalize_sentence(scene.get("narration") or fallback_narration, max_len=420)
            if len(narration) < 45:
                narration = _normalize_sentence(
                    f"{narration} This visual shows how the parts change and why that change matters.",
                    max_len=420,
                )
            scene["narration"] = narration

            fallback_visual_goal = (
                f"Animate {scene['headline']} with changing shapes, labels, and one clear comparison that matches the narration."
            )
            scene["visual_goal"] = _normalize_sentence(
                scene.get("visual_goal") or fallback_visual_goal,
                max_len=220,
            )

            layout = _normalize_spacing(scene.get("layout") or "auto").lower()
            if layout not in LAYOUT_OPTIONS:
                layout = "auto"
            scene["layout"] = layout

            scene_context = " ".join(
                [
                    concept_context,
                    scene["headline"],
                    scene["narration"],
                    scene["visual_goal"],
                    " ".join(scene.get("visual_items") or []),
                    " ".join(scene.get("highlight_terms") or []),
                    " ".join(scene.get("equations") or []),
                ]
            )

            raw_variant = _normalize_spacing(scene.get("scene_variant") or "").lower().replace("-", "_").replace(" ", "_")
            if raw_variant not in SCENE_TEMPLATES:
                raw_variant = _default_scene_variant(index, scene["layout"], scene_context)
            scene["scene_variant"] = raw_variant

            keywords = _extract_keywords(scene_context, limit=10)
            keyword_terms = [_keyword_to_term(word) for word in keywords]

            narration_points = [
                _normalize_caption(sentence.rstrip(".!?"), max_len=90)
                for sentence in _split_sentences(scene["narration"])[:3]
            ]
            narration_points = [point for point in narration_points if point]

            scene["key_points"] = _normalize_short_list(
                scene.get("key_points"),
                narration_points,
                limit=3,
                max_len=90,
            )

            visual_fallback = scene["key_points"] or keyword_terms[:5]
            scene["visual_items"] = _normalize_short_list(
                scene.get("visual_items"),
                visual_fallback,
                limit=5,
                max_len=48,
            )

            highlight_fallback = [*keyword_terms, *scene["visual_items"], scene["headline"]]
            scene["highlight_terms"] = _normalize_short_list(
                scene.get("highlight_terms"),
                highlight_fallback,
                limit=5,
                max_len=28,
            )

            scene["equations"] = _normalize_short_list(
                scene.get("equations"),
                [],
                limit=2,
                max_len=60,
                capitalize=False,
            )

        add_log(job["id"], f"Using {len(scenes)} scenes for this lesson.")

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
                render_quality=str(job.get("render_quality") or "1080p"),
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
