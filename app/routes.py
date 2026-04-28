from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime, timezone
from threading import Thread
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from .services.captions import write_captions
from .services.claude_code import extract_json_text
from .services.media import MediaError, extract_thumbnail, probe_duration
from .services.question_generation import generate_quiz
from .services.repository import add_log, clone_job, create_job, get_job, get_job_logs, list_jobs, update_job


RESULTS_CSV_FIELDNAMES = [
    "timestamp",
    "job_id",
    "name",
    "grade",
    "enrollment",
    "difficulty_frequency",
    "first_resource",
    "resource_satisfaction",
    "first_video_time",
    "understanding_change",
    "video_quality",
    "appropriate_length",
    "easy_without_guidance",
    "use_again",
    "improvement",
    "pre_score",
    "pre_percentage",
    "post_score",
    "post_percentage",
]


def _survey_csv_path() -> Path:
    base_dir = Path(current_app.config["BASE_DIR"])
    csv_path = base_dir / "survey_results.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    return csv_path


def _quiz_question_count(job: dict) -> int:
    try:
        quiz = json.loads(job.get("quiz_json") or "{}")
    except json.JSONDecodeError:
        return 0
    if isinstance(quiz, dict):
        return len(quiz.get("questions") or [])
    if isinstance(quiz, list):
        return len(quiz)
    return 0


def _score_percentage(score: int | None, question_count: int) -> float | str:
    if score is None or not question_count:
        return ""
    return round((score / question_count) * 100, 1)


def _upsert_results_csv_row(row: dict[str, str | int | float | None]) -> None:
    csv_path = _survey_csv_path()
    rows: list[dict[str, str]] = []
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as csvfile:
            rows = list(csv.DictReader(csvfile))

    normalized = {key: row.get(key, "") for key in RESULTS_CSV_FIELDNAMES}
    job_id = str(normalized.get("job_id", ""))
    for index, existing in enumerate(rows):
        if existing.get("job_id") == job_id:
            merged = {key: existing.get(key, "") for key in RESULTS_CSV_FIELDNAMES}
            merged.update({key: value for key, value in normalized.items() if value not in ("", None)})
            rows[index] = merged
            break
    else:
        rows.append(normalized)

    with csv_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=RESULTS_CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in RESULTS_CSV_FIELDNAMES} for row in rows)


def _save_quiz_results_to_csv(job_id: str, job: dict) -> None:
    question_count = _quiz_question_count(job)
    pre_score = job.get("pre_score")
    post_score = job.get("post_score")
    _upsert_results_csv_row(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "job_id": job_id,
            "pre_score": pre_score if pre_score is not None else "",
            "pre_percentage": _score_percentage(pre_score, question_count),
            "post_score": post_score if post_score is not None else "",
            "post_percentage": _score_percentage(post_score, question_count),
        }
    )


bp = Blueprint("main", __name__)


PIPELINE = [
    "Queued",
    "Planning storyboard",
    "Synthesizing narration",
    "Preparing scenes",
    "Rendering scenes",
    "Finalizing video",
]

_AUDIO_DONE_RE = re.compile(r"Scene (\d+)/(\d+) narration synthesized")
_RENDER_DONE_RE = re.compile(r"Scene (\d+) clip assembled")


def _quiz_state(job: dict) -> dict:
    raw = job.get("quiz_json")
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"status": "error", "questions": None, "error": "Saved quiz JSON could not be parsed."}
        if isinstance(parsed, dict):
            if parsed.get("status") == "error":
                return {"status": "error", "questions": None, "error": parsed.get("error") or "Question generation failed."}
            if isinstance(parsed.get("questions"), list):
                return {"status": "ready", "questions": parsed["questions"], "error": None}
            if parsed.get("status") == "pending":
                return {"status": "pending", "questions": None, "error": None}
        elif isinstance(parsed, list):
            return {"status": "ready", "questions": parsed, "error": None}
    return {"status": "pending", "questions": None, "error": None}


def _quiz_from_job(job: dict) -> list[dict]:
    state = _quiz_state(job)
    return state["questions"] or []


def _score_quiz(form, quiz: list[dict]) -> int:
    score = 0
    for index, question in enumerate(quiz):
        if form.get(f"q{index}") == str(question.get("answer")):
            score += 1
    return score


def _generate_quiz_for_job(app, job_id: str, concept: str, research: str) -> None:
    with app.app_context():
        quiz_dir = Path(app.config["JOBS_DIR"]) / job_id / "quiz"
        try:
            quiz = generate_quiz(
                concept=concept,
                research=research,
                workdir=quiz_dir,
                output_path=quiz_dir / "questions.json",
                model=app.config["CLAUDE_QUESTION_MODEL"],
            )
        except Exception as exc:
            update_job(job_id, quiz_json=json.dumps({"status": "error", "error": str(exc)}))
            add_log(job_id, f"Question generation failed: {exc}", level="error")
            return

        update_job(job_id, quiz_json=json.dumps({"status": "ready", "questions": quiz}))
        add_log(job_id, f"Question quiz generated with {app.config['CLAUDE_QUESTION_MODEL']}.")


def _start_quiz_generation(app, job_id: str, concept: str, research: str) -> None:
    update_job(job_id, quiz_json=json.dumps({"status": "pending"}))
    Thread(
        target=_generate_quiz_for_job,
        args=(app, job_id, concept, research),
        daemon=True,
    ).start()


def _parse_token_usage(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    if "stage_totals" not in parsed:
        input_tokens = int(parsed.get("input_tokens") or 0)
        output_tokens = int(parsed.get("output_tokens") or 0)
        cache_read_tokens = int(parsed.get("cache_read_input_tokens") or 0)
        cache_creation_tokens = int(parsed.get("cache_creation_input_tokens") or 0)
        storyboard_total = input_tokens + output_tokens + cache_read_tokens + cache_creation_tokens
        parsed["stage_totals"] = {
            "storyboard": storyboard_total,
            "scene_prep_and_code": 0,
            "other": 0,
        }
        parsed["total_tokens"] = int(parsed.get("total_tokens") or storyboard_total)
    return parsed


def _progress_metrics(job: dict, logs: list[dict], scene_count: int) -> tuple[int, str, str]:
    messages = [entry["message"] for entry in logs]
    worker_started = any("Worker started." in message or "Worker accepted job." in message for message in messages)
    storyboard_done = any("Storyboard created with" in message for message in messages)
    prepared = any("Scene module prepared." in message for message in messages)
    finalizing = any("Finalizing video" == message for message in messages) or job.get("current_step") == "Finalizing video"
    final_ready = any(message.startswith("Final video ready:") for message in messages) or job.get("status") == "completed"
    render_started = any(message.startswith("Rendering scene ") for message in messages) or job.get("current_step", "").startswith("Rendering scene")

    audio_done = 0
    audio_total = scene_count
    render_done = 0
    for message in messages:
        audio_match = _AUDIO_DONE_RE.search(message)
        if audio_match:
            audio_done = max(audio_done, int(audio_match.group(1)))
            audio_total = max(audio_total, int(audio_match.group(2)))
        render_match = _RENDER_DONE_RE.search(message)
        if render_match:
            render_done = max(render_done, int(render_match.group(1)))

    total_scenes = max(scene_count, audio_total, 1)
    progress = 0
    detail = "Queued"
    active_label = "Queued"

    if worker_started or job.get("status") in {"running", "completed", "failed"}:
        progress = max(progress, 5)
        detail = "Worker started"
        active_label = "Planning storyboard"
    if storyboard_done:
        progress = max(progress, 20)
        detail = f"Storyboard ready, {total_scenes} scenes"
        active_label = "Synthesizing narration"
    if audio_done:
        progress = max(progress, 20 + int((audio_done / total_scenes) * 30))
        detail = f"Narration {audio_done}/{total_scenes}"
        active_label = "Synthesizing narration" if audio_done < total_scenes else "Preparing scenes"
    if prepared:
        progress = max(progress, 55)
        detail = "Scene module ready"
        active_label = "Preparing scenes"
    if render_started:
        active_label = "Rendering scenes"
    if render_done:
        progress = max(progress, 55 + int((render_done / total_scenes) * 40))
        detail = f"Rendered {render_done}/{total_scenes}"
        active_label = "Rendering scenes"
    if finalizing:
        progress = max(progress, 97)
        detail = "Finalizing video"
        active_label = "Finalizing video"
    if final_ready:
        return 100, "Completed", "Completed"

    if job.get("status") == "failed":
        return min(progress, 99), detail, active_label
    if job.get("status") == "queued" and progress == 0:
        return 1, "Queued", "Queued"
    return min(progress, 99), detail, active_label


def _progress_from_job(job: dict, logs: list[dict], scene_count: int) -> tuple[int, list[dict], str]:
    status = job.get("status", "queued")
    labels = PIPELINE[:]
    progress, detail, current_label = _progress_metrics(job, logs, scene_count)

    current_index = labels.index(current_label) if current_label in labels else 0
    pipeline = []
    for index, label in enumerate(labels):
        state = "pending"
        if status == "completed" or index < current_index:
            state = "done"
        elif label == current_label or (status == "queued" and label == "Queued"):
            state = "current"
        pipeline.append({"label": label, "state": state})

    if status == "failed" and current_label in labels:
        for item in pipeline:
            if item["label"] == current_label:
                item["state"] = "current"
                break
    return progress, pipeline, detail


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m"


def _video_runtime(video_path: Path, fallback_seconds: float | None = None) -> dict:
    try:
        seconds = probe_duration(video_path) if video_path.exists() else fallback_seconds
    except (MediaError, OSError, ValueError):
        seconds = fallback_seconds
    return {"seconds": seconds, "label": _format_duration(seconds)}


def _title_card_duration(payload: dict) -> float | None:
    scenes = (payload.get("storyboard") or {}).get("scenes") or []
    if not scenes:
        return None
    try:
        return float(scenes[0].get("target_duration_seconds") or 0) or None
    except (TypeError, ValueError):
        return None


def _format_relative(target: datetime | None, now: datetime | None = None) -> str:
    if target is None:
        return "—"
    now = now or datetime.now(timezone.utc)
    delta = (now - target).total_seconds()
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)} min ago"
    if delta < 86400:
        return f"{int(delta // 3600)} hr ago"
    return f"{int(delta // 86400)} d ago"


def _compute_timing(job: dict, logs: list[dict]) -> dict:
    now = datetime.now(timezone.utc)
    created = _parse_iso(job.get("created_at"))
    completed = _parse_iso(job.get("completed_at"))
    updated = _parse_iso(job.get("updated_at"))

    end_time = completed or (updated if job.get("status") in {"completed", "failed"} else now)
    total_seconds = (end_time - created).total_seconds() if created else None

    worker_started_ts = None
    worker_finished_ts = None
    for entry in logs:
        message = entry.get("message", "")
        if worker_started_ts is None and ("Worker started." in message or "Worker accepted job." in message):
            worker_started_ts = _parse_iso(entry.get("timestamp"))
        if message.startswith("Final video ready:"):
            worker_finished_ts = _parse_iso(entry.get("timestamp"))

    if worker_started_ts is not None:
        agent_end = worker_finished_ts or completed or now
        agent_seconds = (agent_end - worker_started_ts).total_seconds()
    else:
        agent_seconds = None

    status_anchor = updated or created
    status_seconds = (now - status_anchor).total_seconds() if status_anchor and job.get("status") in {"queued", "running"} else None

    return {
        "total_seconds": total_seconds,
        "total_label": _format_duration(total_seconds),
        "agent_seconds": agent_seconds,
        "agent_label": _format_duration(agent_seconds),
        "status_seconds": status_seconds,
        "status_label": _format_duration(status_seconds) if status_seconds is not None else _format_duration(total_seconds),
        "input_relative": _format_relative(created, now),
        "input_absolute": created.astimezone().strftime("%b %d, %I:%M %p") if created else "—",
        "completed_relative": _format_relative(completed, now) if completed else None,
    }


def _ensure_artifact(job_id: str, video_path: Path, name: str, builder) -> Path | None:
    """Return path to the named artifact next to the video, building it on demand."""
    artifact_path = video_path.parent / name
    if artifact_path.exists():
        return artifact_path
    if not video_path.exists():
        return None
    try:
        builder(artifact_path)
    except Exception:
        return None
    return artifact_path if artifact_path.exists() else None


def _artifact_url(job_id: str, file_path: Path) -> str | None:
    try:
        relative = file_path.relative_to(Path(current_app.config["JOBS_DIR"]) / job_id)
    except ValueError:
        return None
    return url_for("main.job_artifact", job_id=job_id, subpath=str(relative))


def _build_job_payload(job: dict, include_logs: bool = False) -> dict:
    payload = dict(job)
    payload["video_url"] = None
    payload["thumbnail_url"] = None
    payload["captions_url"] = None
    payload["storyboard"] = None
    payload["raw_storyboard"] = None
    payload["claude_available"] = True
    payload["deepgram_ready"] = bool(current_app.config["DEEPGRAM_API_KEY"])
    payload["token_usage"] = _parse_token_usage(payload.get("token_usage_json"))
    payload["token_usage_message"] = None
    payload["video_runtime"] = {
        "seconds": payload.get("duration_seconds"),
        "label": _format_duration(payload.get("duration_seconds")),
    }

    storyboard_path = payload.get("storyboard_path")
    if storyboard_path:
        story_file = Path(storyboard_path)
        if story_file.exists():
            payload["raw_storyboard"] = story_file.read_text(encoding="utf-8")
            payload["storyboard"] = json.loads(extract_json_text(payload["raw_storyboard"]))
        if not payload["token_usage"] and "/codex/" in storyboard_path:
            payload["token_usage_message"] = "This is an older job from the pre-SDK path, so no Claude usage was saved."
        elif not payload["token_usage"] and payload.get("status") == "completed":
            payload["token_usage_message"] = "This job completed without saved SDK usage data."

    if payload.get("video_path"):
        video_path = Path(payload["video_path"])
        try:
            relative = video_path.relative_to(Path(current_app.config["JOBS_DIR"]) / payload["id"])
            payload["video_url"] = url_for("main.job_artifact", job_id=payload["id"], subpath=str(relative))
        except ValueError:
            payload["video_url"] = None

        thumbnail_path = _ensure_artifact(
            payload["id"],
            video_path,
            "thumbnail.jpg",
            lambda dest: extract_thumbnail(
                video_path=video_path,
                output_path=dest,
                title_duration=_title_card_duration(payload),
            ),
        )
        if thumbnail_path:
            payload["thumbnail_url"] = _artifact_url(payload["id"], thumbnail_path)
        payload["video_runtime"] = _video_runtime(video_path, payload.get("duration_seconds"))

    if payload.get("video_path") and payload.get("storyboard"):
        video_path = Path(payload["video_path"])

        def _build_captions(dest: Path) -> None:
            scenes = payload["storyboard"].get("scenes") or []
            scene_durations = [
                float(scene.get("target_duration_seconds") or 0) or None
                for scene in scenes
            ]
            write_captions(
                scenes=scenes,
                output_path=dest,
                scene_durations=[d if d is not None else 6.0 for d in scene_durations],
            )

        captions_path = _ensure_artifact(
            payload["id"], video_path, "captions.vtt", _build_captions,
        )
        if captions_path:
            payload["captions_url"] = _artifact_url(payload["id"], captions_path)

    payload["scene_count"] = len(payload["storyboard"]["scenes"]) if payload["storyboard"] else 0
    payload["question_count"] = _quiz_question_count(payload)
    logs = get_job_logs(payload["id"])
    payload["progress_percent"], payload["pipeline"], payload["progress_detail"] = _progress_from_job(
        payload,
        logs,
        payload["scene_count"],
    )
    payload["is_active"] = payload["status"] in {"queued", "running"}
    payload["timing"] = _compute_timing(payload, logs)

    if include_logs:
        payload["logs"] = logs
    return payload


@bp.get("/")
def index():
    if request.cookies.get("onboarded") != "1":
        return redirect(url_for("main.onboarding"))
    return redirect(url_for("main.home"))


@bp.get("/home")
def home():
    jobs = [_build_job_payload(job) for job in list_jobs()]
    environment = {
        "claude": True,
        "deepgram": bool(current_app.config["DEEPGRAM_API_KEY"]),
        "ffmpeg": bool(shutil.which("ffmpeg")),
    }
    models = {
        "questions": current_app.config["CLAUDE_QUESTION_MODEL"],
        "video": current_app.config["CLAUDE_CODE_MODEL"],
    }
    return render_template("index.html", jobs=jobs, environment=environment, models=models)


@bp.get("/onboarding")
def onboarding():
    return render_template("onboarding.html")


@bp.post("/onboarding/done")
def onboarding_done():
    response = make_response(redirect(url_for("main.home")))
    response.set_cookie("onboarded", "1", max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response


@bp.get("/library")
def library():
    return redirect(url_for("main.home"))


@bp.post("/jobs")
def create_job_view():
    concept = request.form.get("concept", "").strip()
    if not concept:
        flash("A concept is required.")
        return redirect(url_for("main.index"))
    research = request.form.get("research", "").strip()

    duration_label = request.form.get("duration_label", "medium").strip().lower()
    style_notes = " ".join(
        [
            "Keep the plan compact but technically useful for developers.",
            "Use simple diagrams, equations, arrows, and transformations that basic Manim can render well.",
            "Prefer precise explanations, clean structure, and high-signal visuals over marketing language.",
        ]
    )

    job_id = create_job(
        concept=concept,
        research=research,
        audience="Developer",
        provider="claude-agent-sdk",
        model=current_app.config["CLAUDE_CODE_MODEL"],
        duration_label=duration_label,
        voice_model=current_app.config["DEEPGRAM_VOICE_MODEL"],
        render_quality="720p",
        style_notes=style_notes,
    )
    current_app.extensions["job_manager"].enqueue(job_id)
    _start_quiz_generation(current_app._get_current_object(), job_id, concept, research)
    return redirect(url_for("main.pre_quiz", job_id=job_id))


@bp.post("/jobs/<job_id>/rerun")
def rerun_job(job_id: str):
    source = get_job(job_id)
    if source is None:
        abort(404)
    new_job_id = clone_job(source)
    if source.get("quiz_json"):
        update_job(new_job_id, quiz_json=source.get("quiz_json"))
    else:
        _start_quiz_generation(
            current_app._get_current_object(),
            new_job_id,
            source["concept"],
            source.get("research", ""),
        )
    current_app.extensions["job_manager"].enqueue(new_job_id)
    return redirect(url_for("main.pre_quiz", job_id=new_job_id))


@bp.get("/jobs/<job_id>")
def job_detail(job_id: str):
    return redirect(url_for("main.video_page", job_id=job_id))


@bp.get("/jobs/<job_id>/debug")
def debug_job(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    return render_template("job_detail.html", job=_build_job_payload(job, include_logs=True))


@bp.get("/jobs/<job_id>/pre")
def pre_quiz(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    if not job.get("quiz_json"):
        _start_quiz_generation(
            current_app._get_current_object(),
            job_id,
            job["concept"],
            job.get("research", ""),
        )
        job = get_job(job_id)
    return render_template(
        "quiz.html",
        job=_build_job_payload(job),
        quiz_state=_quiz_state(job),
        models={"questions": current_app.config["CLAUDE_QUESTION_MODEL"]},
        phase="pre",
    )


@bp.post("/jobs/<job_id>/pre")
def submit_pre_quiz(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    quiz = _quiz_from_job(job)
    if not quiz:
        flash("Question generation is not ready yet.")
        return redirect(url_for("main.pre_quiz", job_id=job_id))
    pre_score = _score_quiz(request.form, quiz)
    update_job(job_id, pre_score=pre_score)
    return redirect(url_for("main.video_page", job_id=job_id))


@bp.get("/jobs/<job_id>/watch")
def video_page(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    if job.get("pre_score") is None:
        return redirect(url_for("main.pre_quiz", job_id=job_id))
    return render_template("video.html", job=_build_job_payload(job, include_logs=True))


@bp.get("/jobs/<job_id>/post")
def post_quiz(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    if job.get("pre_score") is None:
        return redirect(url_for("main.pre_quiz", job_id=job_id))
    state = _quiz_state(job)
    if state["status"] != "ready":
        return redirect(url_for("main.pre_quiz", job_id=job_id))
    return render_template(
        "quiz.html",
        job=_build_job_payload(job),
        quiz_state=state,
        models={"questions": current_app.config["CLAUDE_QUESTION_MODEL"]},
        phase="post",
    )


@bp.post("/jobs/<job_id>/post")
def submit_post_quiz(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    quiz = _quiz_from_job(job)
    if not quiz:
        flash("Question generation is not ready yet.")
        return redirect(url_for("main.post_quiz", job_id=job_id))
    post_score = _score_quiz(request.form, quiz)
    update_job(job_id, post_score=post_score)
    updated_job = get_job(job_id) or {**job, "post_score": post_score}
    _save_quiz_results_to_csv(job_id, updated_job)
    return redirect(url_for("main.results", job_id=job_id))


@bp.get("/jobs/<job_id>/results")
def results(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    if job.get("post_score") is None:
        return redirect(url_for("main.post_quiz", job_id=job_id))
    return render_template("results.html", job=_build_job_payload(job))


@bp.get("/jobs/<job_id>/survey")
def survey(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    if job.get("post_score") is None:
        return redirect(url_for("main.results", job_id=job_id))
    return render_template("survey.html", job=_build_job_payload(job))


@bp.post("/jobs/<job_id>/survey")
def submit_survey(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)

    name = request.form.get("name", "").strip()
    grade = request.form.get("grade", "").strip()
    enrollment = "; ".join(request.form.getlist("enrollment"))
    difficulty_frequency = request.form.get("difficulty_frequency", "").strip()
    first_resource = request.form.get("first_resource", "").strip()
    first_resource_other = request.form.get("first_resource_other", "").strip()
    if first_resource == "Other" and first_resource_other:
        first_resource = f"Other: {first_resource_other}"
    resource_satisfaction = request.form.get("resource_satisfaction", "").strip()
    first_video_time = request.form.get("first_video_time", "").strip()
    understanding_change = request.form.get("understanding_change", "").strip()
    video_quality = request.form.get("video_quality", "").strip()
    appropriate_length = request.form.get("appropriate_length", "").strip()
    easy_without_guidance = request.form.get("easy_without_guidance", "").strip()
    use_again = request.form.get("use_again", "").strip()
    improvement = request.form.get("improvement", "").strip()

    question_count = _quiz_question_count(job)
    pre_score = job.get("pre_score")
    post_score = job.get("post_score")
    survey_payload = {
        "name": name,
        "grade": grade,
        "enrollment": enrollment,
        "difficulty_frequency": difficulty_frequency,
        "first_resource": first_resource,
        "resource_satisfaction": resource_satisfaction,
        "first_video_time": first_video_time,
        "understanding_change": understanding_change,
        "video_quality": video_quality,
        "appropriate_length": appropriate_length,
        "easy_without_guidance": easy_without_guidance,
        "use_again": use_again,
        "improvement": improvement,
    }

    update_job(job_id, survey_json=json.dumps(survey_payload))
    _upsert_results_csv_row(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "job_id": job_id,
            **survey_payload,
            "pre_score": pre_score if pre_score is not None else "",
            "pre_percentage": _score_percentage(pre_score, question_count),
            "post_score": post_score if post_score is not None else "",
            "post_percentage": _score_percentage(post_score, question_count),
        }
    )

    return render_template("thanks.html")


@bp.get("/api/jobs/<job_id>")
def job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    response = jsonify(_build_job_payload(job, include_logs=True))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@bp.get("/api/jobs/<job_id>/quiz")
def quiz_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    response = jsonify(_quiz_state(job))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@bp.get("/jobs/<job_id>/artifacts/<path:subpath>")
def job_artifact(job_id: str, subpath: str):
    job_root = Path(current_app.config["JOBS_DIR"]) / job_id
    artifact_path = (job_root / subpath).resolve()
    if not artifact_path.exists():
        abort(404)
    if job_root.resolve() not in artifact_path.parents and artifact_path != job_root.resolve():
        abort(403)
    return send_from_directory(job_root, subpath)
