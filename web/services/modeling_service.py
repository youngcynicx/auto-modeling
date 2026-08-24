from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .codex_runner import CodexRunner
from .job_store import JobStore
from .model_runner import run_model, validate_outputs


class ModelingService:
    def __init__(self, store: JobStore, python_path: Path) -> None:
        self.store = store
        self.python_path = python_path.expanduser().absolute()
        self.codex = CodexRunner(self.python_path)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cad-model")

    def submit_new(self, prompt: str) -> dict:
        job = self.store.create_job(prompt)
        self.executor.submit(self._process_revision, job["id"], 1, prompt, False)
        return job

    def submit_edit(self, job_id: str, prompt: str) -> dict:
        job = self.store.add_revision(job_id, prompt)
        revision = job["pending_revision"]
        self.executor.submit(self._process_revision, job_id, revision, prompt, True)
        return job

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)

    def _process_revision(self, job_id: str, revision: int, prompt: str, is_edit: bool) -> None:
        try:
            revision_dir = self.store.revision_dir(job_id, revision)
            self.store.set_status(job_id, revision, "generating")
            summary = self.codex.run(revision_dir, prompt, is_edit)
            self.store.set_status(job_id, revision, "exporting")
            run_model(revision_dir, self.python_path)
            self.store.set_status(job_id, revision, "validating")
            validation = validate_outputs(revision_dir)
            self.store.complete_revision(job_id, revision, summary, validation)
        except Exception as exc:
            self.store.fail_revision(job_id, revision, str(exc))
