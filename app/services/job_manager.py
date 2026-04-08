from __future__ import annotations

from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from .repository import add_log, get_job, list_pending_jobs, update_job
from .workflow import VideoWorkflow


class JobManager:
    def __init__(self, app):
        self.app = app
        self.executor = ThreadPoolExecutor(max_workers=app.config["MAX_WORKERS"])
        self._lock = Lock()
        self._active_job_ids: set[str] = set()
        with app.app_context():
            self.resume_pending_jobs()

    def enqueue(self, job_id: str, *, resume: bool = False) -> None:
        with self._lock:
            if job_id in self._active_job_ids:
                return
            self._active_job_ids.add(job_id)

        job = get_job(job_id)
        if job is None:
            with self._lock:
                self._active_job_ids.discard(job_id)
            return

        if resume:
            if job["status"] == "queued":
                update_job(job_id, status="queued", current_step="Queued for worker")
            add_log(job_id, "Worker resumed job.")
        else:
            update_job(job_id, status="queued", current_step="Queued for worker")
            add_log(job_id, "Worker accepted job.")
        future = self.executor.submit(self._run_job, job_id)
        future.add_done_callback(lambda done: self._handle_done(job_id, done))

    def resume_pending_jobs(self) -> None:
        for job in list_pending_jobs():
            self.enqueue(job["id"], resume=True)

    def _run_job(self, job_id: str) -> None:
        with self.app.app_context():
            workflow = VideoWorkflow()
            workflow.run(job_id)

    def _handle_done(self, job_id: str, future: Future) -> None:
        with self.app.app_context():
            with self._lock:
                self._active_job_ids.discard(job_id)

            try:
                future.result()
            except Exception as exc:
                job = get_job(job_id)
                if job and job["status"] not in {"completed", "failed"}:
                    update_job(job_id, status="failed", current_step="Failed", error_message=str(exc))
                    add_log(job_id, f"Worker crashed: {exc}", level="error")
