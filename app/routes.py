from __future__ import annotations

import json
import re
import shutil
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

from .services.claude_code import extract_json_text
from .services.question_generation import fallback_quiz, generate_quiz
from .services.repository import add_log, clone_job, create_job, get_job, get_job_logs, list_jobs, update_job
from .services.claude_cli import resolve_claude_cli_path


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
                cli_path=app.config.get("CLAUDE_CODE_CLI_PATH") or None,
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


def _build_job_payload(job: dict, include_logs: bool = False) -> dict:
    payload = dict(job)
    payload["video_url"] = None
    payload["storyboard"] = None
    payload["raw_storyboard"] = None
    payload["claude_available"] = bool(resolve_claude_cli_path())
    payload["deepgram_ready"] = bool(current_app.config["DEEPGRAM_API_KEY"])
    payload["token_usage"] = _parse_token_usage(payload.get("token_usage_json"))
    payload["token_usage_message"] = None

    if payload.get("video_path"):
        video_path = Path(payload["video_path"])
        try:
            relative = video_path.relative_to(Path(current_app.config["JOBS_DIR"]) / payload["id"])
            payload["video_url"] = url_for("main.job_artifact", job_id=payload["id"], subpath=str(relative))
        except ValueError:
            payload["video_url"] = None

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

    payload["scene_count"] = len(payload["storyboard"]["scenes"]) if payload["storyboard"] else 0
    logs = get_job_logs(payload["id"])
    payload["progress_percent"], payload["pipeline"], payload["progress_detail"] = _progress_from_job(
        payload,
        logs,
        payload["scene_count"],
    )
    payload["is_active"] = payload["status"] in {"queued", "running"}

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
        "claude": bool(resolve_claude_cli_path()),
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
    update_job(job_id, pre_score=_score_quiz(request.form, quiz))
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
    update_job(job_id, post_score=_score_quiz(request.form, quiz))
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
    if get_job(job_id) is None:
        abort(404)
    survey = request.form.to_dict(flat=False)
    survey["improvement"] = [request.form.get("improvement", "").strip()]
    update_job(job_id, survey_json=json.dumps(survey))
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
