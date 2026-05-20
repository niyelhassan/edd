from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
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
from .services.google_sheets import sync_csv_to_google_sheet
from .services.media import MediaError, extract_thumbnail, probe_duration
from .services.question_generation import VIDEO_CATEGORIES
from .services.repository import add_log, clone_job, create_job, get_job, get_job_logs, list_jobs, update_job
from .services.workflow import VALID_COLOR_THEMES, VALID_EXPLANATION_LEVELS


RESULTS_CSV_FIELDNAMES = [
    "timestamp",
    "job_id",
    "topic",
    "research_area",
    "category",
    "length",
    "explanation_level",
    "color_theme",
    "video_length_actual",
    "time",
    "storyboard_tokens",
    "storyboard_cost",
    "is_trial",
    "name",
    "grade",
    "enrollment",
    "difficulty_frequency",
    "overall_satisfaction",
    "understanding_improvement",
    "vs_normal_resources",
    "easy_without_guidance",
    "had_difficulties",
    "difficulties_detail",
    "practicality",
    "fair_price",
    "recommend_likelihood",
    "improvement",
    "pre_score",
    "pre_percentage",
    "post_score",
    "post_percentage",
]


def _results_csv_path() -> Path:
    base_dir = Path(current_app.config["BASE_DIR"])
    csv_path = base_dir / "results.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    return csv_path


def _sync_results_csv(csv_path: Path) -> None:
    spreadsheet_id = current_app.config.get("GOOGLE_RESULTS_SPREADSHEET_ID", "")
    if not spreadsheet_id:
        return

    try:
        synced = sync_csv_to_google_sheet(
            csv_path=csv_path,
            spreadsheet_id=spreadsheet_id,
            worksheet_name=current_app.config.get("GOOGLE_RESULTS_WORKSHEET_NAME", "results"),
            config=current_app.config,
        )
    except Exception:
        current_app.logger.exception("Could not sync results.csv to Google Sheets.")
        return

    if synced:
        current_app.logger.info("Synced results.csv to Google Sheets.")


def _quiz_question_count(job: dict) -> int:
    try:
        quiz = json.loads(job.get("quiz_json") or "{}")
    except json.JSONDecodeError:
        return 0
    return len(quiz.get("questions") or []) if isinstance(quiz, dict) else 0


def _score_percentage(score: int | None, question_count: int) -> float | str:
    if score is None or not question_count:
        return ""
    return round((score / question_count) * 100, 1)


def _token_total(usage: dict | None, stage: str | None = None) -> int | str:
    if not usage:
        return ""
    if stage:
        stage_totals = usage.get("stage_totals")
        if isinstance(stage_totals, dict) and stage_totals.get(stage) is not None:
            return int(stage_totals.get(stage) or 0)
    return int(usage.get("total_tokens") or 0)


def _cost_value(usage: dict | None) -> float | str:
    if not usage or usage.get("cost_usd") is None:
        return ""
    try:
        return round(float(usage["cost_usd"]), 6)
    except (TypeError, ValueError):
        return ""


def _job_results_metadata(job: dict) -> dict[str, str | int | float]:
    logs = get_job_logs(job["id"])
    timing = _compute_timing(job, logs)
    video_runtime = {"seconds": None, "label": ""}
    if job.get("video_path"):
        video_runtime = _video_runtime(Path(job["video_path"]), job.get("duration_seconds"))
    token_usage = _parse_token_usage(job.get("token_usage_json"))
    return {
        "topic": job.get("concept", ""),
        "research_area": job.get("research", ""),
        "category": job.get("topic_category", ""),
        "length": job.get("duration_label", ""),
        "explanation_level": job.get("explanation_level", ""),
        "color_theme": job.get("color_theme", ""),
        "video_length_actual": video_runtime["label"],
        "time": timing["total_label"],
        "storyboard_tokens": _token_total(token_usage, "storyboard"),
        "storyboard_cost": _cost_value(token_usage),
    }


def _job_survey_payload(job: dict) -> dict[str, str]:
    if not job.get("survey_json"):
        return {}
    try:
        parsed = json.loads(job["survey_json"])
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {
        key: str(parsed.get(key, ""))
        for key in RESULTS_CSV_FIELDNAMES
        if key in parsed
    }


def _upsert_results_csv_row(row: dict[str, str | int | float | None]) -> None:
    csv_path = _results_csv_path()
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
    _sync_results_csv(csv_path)


def _save_quiz_results_to_csv(job_id: str, job: dict) -> None:
    question_count = _quiz_question_count(job)
    pre_score = job.get("pre_score")
    post_score = job.get("post_score")
    _upsert_results_csv_row(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            **_job_results_metadata(job),
            **_job_survey_payload(job),
            "pre_score": pre_score if pre_score is not None else "",
            "pre_percentage": _score_percentage(pre_score, question_count),
            "post_score": post_score if post_score is not None else "",
            "post_percentage": _score_percentage(post_score, question_count),
        }
    )


bp = Blueprint("main", __name__)


TOPIC_HUE_PALETTE = (210, 158, 34, 348, 265, 188, 15, 300)
TOPIC_HUES = {
    category: TOPIC_HUE_PALETTE[index % len(TOPIC_HUE_PALETTE)]
    for index, category in enumerate(VIDEO_CATEGORIES)
}


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
            if isinstance(parsed.get("questions"), list):
                return {"status": "ready", "questions": parsed["questions"], "error": None}
        return {"status": "error", "questions": None, "error": "Saved quiz JSON is missing questions."}
    if job.get("status") == "failed":
        return {
            "status": "error",
            "questions": None,
            "error": job.get("error_message") or "Question generation failed.",
        }
    if job.get("status") in {"completed", "canceled"}:
        return {
            "status": "error",
            "questions": None,
            "error": "Questions were not generated for this video.",
        }
    return {"status": "pending", "questions": None, "error": None}


def _quiz_from_job(job: dict) -> list[dict]:
    return _quiz_state(job)["questions"] or []


def _score_quiz(form, quiz: list[dict]) -> int:
    return sum(1 for i, q in enumerate(quiz) if form.get(f"q{i}") == str(q.get("answer")))


def _parse_token_usage(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _progress_metrics(job: dict, logs: list[dict], scene_count: int) -> tuple[int, str, str]:
    messages = [entry["message"] for entry in logs]
    renderer_started = any(
        "Renderer started." in m or "Renderer accepted job." in m
        for m in messages
    )
    storyboard_done = any("Storyboard ready" in m or "Storyboard created with" in m for m in messages)
    prepared = any("Scene module prepared." in m for m in messages)
    finalizing = any("Finalizing video" == m for m in messages) or job.get("current_step") == "Finalizing video"
    final_ready = any(m.startswith("Final video ready:") for m in messages) or job.get("status") == "completed"
    render_started = any(m.startswith("Rendering scene ") for m in messages) or job.get("current_step", "").startswith("Rendering scene")

    audio_done, audio_total, render_done = 0, scene_count, 0
    for m in messages:
        a = _AUDIO_DONE_RE.search(m)
        if a:
            audio_done = max(audio_done, int(a.group(1)))
            audio_total = max(audio_total, int(a.group(2)))
        r = _RENDER_DONE_RE.search(m)
        if r:
            render_done = max(render_done, int(r.group(1)))

    total_scenes = max(scene_count, audio_total, 1)
    progress, detail, active_label = 0, "Queued", "Queued"

    if renderer_started or job.get("status") in {"running", "completed", "failed"}:
        progress, detail, active_label = max(progress, 5), "Renderer started", "Planning storyboard"
    if storyboard_done:
        progress, detail, active_label = max(progress, 20), f"Storyboard ready, {total_scenes} scenes", "Synthesizing narration"
    if audio_done:
        progress = max(progress, 20 + int((audio_done / total_scenes) * 30))
        detail = f"Narration {audio_done}/{total_scenes}"
        active_label = "Synthesizing narration" if audio_done < total_scenes else "Preparing scenes"
    if prepared:
        progress, detail, active_label = max(progress, 55), "Scene module ready", "Preparing scenes"
    if render_started:
        active_label = "Rendering scenes"
    if render_done:
        progress = max(progress, 55 + int((render_done / total_scenes) * 40))
        detail = f"Rendered {render_done}/{total_scenes}"
        active_label = "Rendering scenes"
    if finalizing:
        progress, detail, active_label = max(progress, 97), "Finalizing video", "Finalizing video"
    if final_ready:
        return 100, "Completed", "Completed"

    if job.get("status") == "failed":
        return min(progress, 99), detail, active_label
    if job.get("status") == "queued" and progress == 0:
        return 1, "Queued", "Queued"
    return min(progress, 99), detail, active_label


def _progress_from_job(job: dict, logs: list[dict], scene_count: int) -> tuple[int, list[dict], str]:
    status = job.get("status", "queued")
    progress, detail, current_label = _progress_metrics(job, logs, scene_count)
    current_index = PIPELINE.index(current_label) if current_label in PIPELINE else 0
    pipeline = []
    for i, label in enumerate(PIPELINE):
        state = "pending"
        if status == "completed" or i < current_index:
            state = "done"
        elif label == current_label or (status == "queued" and label == "Queued"):
            state = "current"
        pipeline.append({"label": label, "state": state})
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
        return "-"
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m"


def _format_timestamp(seconds: float | None) -> str:
    seconds = int(max(seconds or 0, 0))
    minutes, secs = divmod(seconds, 60)
    hours, mins = divmod(minutes, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def _build_chapters(storyboard: dict | None) -> list[dict]:
    scenes = (storyboard or {}).get("scenes") or []
    chapters = []
    cursor = 0.0
    for scene in scenes:
        duration = float(scene.get("target_duration_seconds") or 0) or 6.0
        layout = str(scene.get("layout") or "").strip().lower()
        title = str(scene.get("headline") or scene.get("title") or "Chapter").strip()
        if layout != "thanks" and title:
            chapters.append(
                {
                    "index": len(chapters) + 1,
                    "title": title,
                    "start": round(cursor, 2),
                    "end": round(cursor + duration, 2),
                    "duration": round(duration, 2),
                    "time": _format_timestamp(cursor),
                }
            )
        cursor += duration
    return chapters


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
        return "-"
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

    renderer_started_ts, renderer_finished_ts = None, None
    for entry in logs:
        message = entry.get("message", "")
        if renderer_started_ts is None and (
            "Renderer started." in message or "Renderer accepted job." in message
        ):
            renderer_started_ts = _parse_iso(entry.get("timestamp"))
        if message.startswith("Final video ready:"):
            renderer_finished_ts = _parse_iso(entry.get("timestamp"))

    if renderer_started_ts is not None:
        agent_end = renderer_finished_ts or completed or now
        agent_seconds = (agent_end - renderer_started_ts).total_seconds()
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
        "input_absolute": created.astimezone().strftime("%b %d, %I:%M %p") if created else "-",
        "completed_relative": _format_relative(completed, now) if completed else None,
    }


def _ensure_artifact(job_id: str, video_path: Path, name: str, builder) -> Path | None:
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
    payload["topic_hue"] = TOPIC_HUES.get(payload.get("topic_category") or "Other", TOPIC_HUES["Other"])
    payload["video_url"] = None
    payload["thumbnail_url"] = None
    payload["captions_url"] = None
    payload["storyboard"] = None
    payload["raw_storyboard"] = None
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
        if not payload["token_usage"] and payload.get("status") == "completed":
            payload["token_usage_message"] = "This job completed without saved usage data."

    if payload.get("video_path"):
        video_path = Path(payload["video_path"])
        try:
            relative = video_path.relative_to(Path(current_app.config["JOBS_DIR"]) / payload["id"])
            payload["video_url"] = url_for("main.job_artifact", job_id=payload["id"], subpath=str(relative))
        except ValueError:
            payload["video_url"] = None

        thumbnail_path = _ensure_artifact(
            payload["id"], video_path, "thumbnail.jpg",
            lambda dest: extract_thumbnail(
                video_path=video_path, output_path=dest,
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

        captions_path = _ensure_artifact(payload["id"], video_path, "captions.vtt", _build_captions)
        if captions_path:
            payload["captions_url"] = _artifact_url(payload["id"], captions_path)

    payload["scene_count"] = len(payload["storyboard"]["scenes"]) if payload["storyboard"] else 0
    payload["chapters"] = _build_chapters(payload["storyboard"])
    payload["question_count"] = _quiz_question_count(payload)
    logs = get_job_logs(payload["id"])
    payload["progress_percent"], payload["pipeline"], payload["progress_detail"] = _progress_from_job(
        payload, logs, payload["scene_count"],
    )
    payload["is_active"] = payload["status"] in {"queued", "running"}
    payload["timing"] = _compute_timing(payload, logs)

    if include_logs:
        payload["logs"] = logs
    return payload


@bp.get("/")
def index():
    if request.cookies.get("onboarded") != "1":
        return redirect(url_for("main.hello"))
    return redirect(url_for("main.home"))


@bp.get("/home")
def home():
    jobs = [_build_job_payload(job) for job in list_jobs()]
    jobs = [
        job for job in jobs
        if job.get("status") == "completed"
        or job.get("is_active")
        or job.get("status") in {"failed", "canceled"}
    ]
    return render_template(
        "index.html",
        jobs=jobs,
        topic_hues=TOPIC_HUES,
    )


@bp.get("/hello")
def hello():
    return render_template("onboarding.html")


@bp.post("/hello/done")
def hello_done():
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
        flash("A topic is required.")
        return redirect(url_for("main.index"))
    research = request.form.get("research", "").strip()
    if not research:
        flash("A research area is required.")
        return redirect(url_for("main.index"))
    duration_label = request.form.get("duration_label", "short").strip().lower()
    color_theme = request.form.get("color_theme", "blue").strip().lower()
    if color_theme not in VALID_COLOR_THEMES:
        color_theme = "blue"
    explanation_level = request.form.get("explanation_level", "high_school").strip().lower()
    if explanation_level not in VALID_EXPLANATION_LEVELS:
        explanation_level = "high_school"

    job_id = create_job(
        concept=concept,
        research=research,
        model=current_app.config["CLAUDE_CODE_MODEL"],
        duration_label=duration_label,
        voice_model=current_app.config["DEEPGRAM_VOICE_MODEL"],
        color_theme=color_theme,
        explanation_level=explanation_level,
    )
    current_app.extensions["job_manager"].enqueue(job_id)
    return redirect(url_for("main.pre_quiz", job_id=job_id))


@bp.post("/jobs/<job_id>/rerun")
def rerun_job(job_id: str):
    source = get_job(job_id)
    if source is None:
        abort(404)
    new_job_id = clone_job(source)
    current_app.extensions["job_manager"].enqueue(new_job_id)
    return redirect(url_for("main.pre_quiz", job_id=new_job_id))


@bp.post("/jobs/<job_id>/cancel")
def cancel_job(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    if job.get("status") in {"queued", "running"}:
        update_job(
            job_id,
            status="canceled",
            current_step="Canceled",
            error_message="Stopped by user.",
        )
        add_log(job_id, "Job stopped by user.", level="warning")
    return redirect(url_for("main.debug_job", job_id=job_id))


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
    return render_template(
        "quiz.html",
        job=_build_job_payload(job),
        quiz_state=_quiz_state(job),
        phase="pre",
    )


@bp.post("/jobs/<job_id>/pre")
def submit_pre_quiz(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    quiz = _quiz_from_job(job)
    if not quiz:
        flash("Questions are not ready yet.")
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
        phase="post",
    )


@bp.post("/jobs/<job_id>/post")
def submit_post_quiz(job_id: str):
    job = get_job(job_id)
    if job is None:
        abort(404)
    quiz = _quiz_from_job(job)
    if not quiz:
        flash("Questions are not ready yet.")
        return redirect(url_for("main.post_quiz", job_id=job_id))
    post_score = _score_quiz(request.form, quiz)
    update_job(job_id, post_score=post_score)
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

    is_trial = request.form.get("is_trial", "yes").strip()
    name = request.form.get("name", "").strip()
    grade = request.form.get("grade", "").strip()
    enrollment = request.form.get("enrollment", "").strip()
    difficulty_frequency = request.form.get("difficulty_frequency", "").strip()
    overall_satisfaction = request.form.get("overall_satisfaction", "").strip()
    understanding_improvement = request.form.get("understanding_improvement", "").strip()
    vs_normal_resources = request.form.get("vs_normal_resources", "").strip()
    easy_without_guidance = request.form.get("easy_without_guidance", "").strip()
    had_difficulties = request.form.get("had_difficulties", "").strip()
    difficulties_detail = request.form.get("difficulties_detail", "").strip()
    practicality = request.form.get("practicality", "").strip()
    fair_price = request.form.get("fair_price", "").strip()
    recommend_likelihood = request.form.get("recommend_likelihood", "").strip()
    improvement = request.form.get("improvement", "").strip()

    question_count = _quiz_question_count(job)
    pre_score = job.get("pre_score")
    post_score = job.get("post_score")
    survey_payload = {
        "is_trial": is_trial,
        "name": name,
        "grade": grade,
        "enrollment": enrollment,
        "difficulty_frequency": difficulty_frequency,
        "overall_satisfaction": overall_satisfaction,
        "understanding_improvement": understanding_improvement,
        "vs_normal_resources": vs_normal_resources,
        "easy_without_guidance": easy_without_guidance,
        "had_difficulties": had_difficulties,
        "difficulties_detail": difficulties_detail,
        "practicality": practicality,
        "fair_price": fair_price,
        "recommend_likelihood": recommend_likelihood,
        "improvement": improvement,
    }

    update_job(job_id, survey_json=json.dumps(survey_payload))
    _upsert_results_csv_row(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            **_job_results_metadata(job),
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
