from __future__ import annotations

from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor

from .repository import add_log, get_job, list_pending_jobs, update_job
from .workflow import VideoWorkflow


class JobManager:
    def __init__(self, app):
        self.app = app
        self.executor = ThreadPoolExecutor(max_workers=1)
        with app.app_context():
            self.resume_pending_jobs()

    def enqueue(self, job_id: str, *, resume: bool = False) -> None:
        job = get_job(job_id)
        if job is None:
            return

        if resume:
            update_job(job_id, status="queued", current_step="Queued")
            add_log(job_id, "Renderer resumed job.")
        else:
            update_job(job_id, status="queued", current_step="Queued")
            add_log(job_id, "Renderer accepted job.")
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
            try:
                future.result()
            except Exception as exc:
                job = get_job(job_id)
                if job and job["status"] not in {"completed", "failed"}:
                    update_job(job_id, status="failed", current_step="Failed", error_message=str(exc))
                    add_log(job_id, f"Renderer crashed: {exc}", level="error")
