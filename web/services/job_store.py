from __future__ import annotations

import json
import os
import re
import shutil
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTIVE_STATUSES = {"queued", "generating", "exporting", "validating"}
JOB_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class JobNotFoundError(KeyError):
    pass


class JobBusyError(RuntimeError):
    pass


class JobStateError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, root: Path, template_path: Path) -> None:
        self.root = root.resolve()
        self.template_path = template_path.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._recover_interrupted_jobs()

    def create_job(self, prompt: str) -> dict[str, Any]:
        with self._lock:
            job_id = uuid.uuid4().hex
            created_at = utc_now()
            revision_dir = self.revision_dir(job_id, 1, create=True)
            shutil.copy2(self.template_path, revision_dir / "model.py")
            (revision_dir / "request.txt").write_text(prompt, encoding="utf-8")

            job = {
                "id": job_id,
                "created_at": created_at,
                "updated_at": created_at,
                "status": "queued",
                "current_revision": None,
                "pending_revision": 1,
                "messages": [
                    {
                        "role": "user",
                        "kind": "create",
                        "revision": 1,
                        "text": prompt,
                        "created_at": created_at,
                    }
                ],
                "revisions": [self._new_revision(1, prompt, created_at)],
            }
            self._write(job)
            return deepcopy(job)

    def add_revision(self, job_id: str, prompt: str) -> dict[str, Any]:
        with self._lock:
            job = self._read(job_id)
            if job["status"] in ACTIVE_STATUSES:
                raise JobBusyError("当前模型仍在处理中，请等待完成后再提交修改。")
            current = job.get("current_revision")
            if current is None:
                raise JobStateError("首个模型尚未成功生成，请新建一个模型任务。")

            number = max(item["number"] for item in job["revisions"]) + 1
            source = self.revision_dir(job_id, current) / "model.py"
            if not source.exists():
                raise JobStateError("当前版本缺少 model.py，无法继续修改。")

            revision_dir = self.revision_dir(job_id, number, create=True)
            shutil.copy2(source, revision_dir / "model.py")
            (revision_dir / "request.txt").write_text(prompt, encoding="utf-8")
            created_at = utc_now()
            job["revisions"].append(self._new_revision(number, prompt, created_at))
            job["messages"].append(
                {
                    "role": "user",
                    "kind": "modify",
                    "revision": number,
                    "text": prompt,
                    "created_at": created_at,
                }
            )
            job["status"] = "queued"
            job["pending_revision"] = number
            job["updated_at"] = created_at
            self._write(job)
            return deepcopy(job)

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._read(job_id))

    def set_status(self, job_id: str, revision: int, status: str) -> dict[str, Any]:
        with self._lock:
            job = self._read(job_id)
            item = self._find_revision(job, revision)
            timestamp = utc_now()
            item["status"] = status
            item["updated_at"] = timestamp
            job["status"] = status
            job["pending_revision"] = revision
            job["updated_at"] = timestamp
            self._write(job)
            return deepcopy(job)

    def complete_revision(
        self,
        job_id: str,
        revision: int,
        summary: str,
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            job = self._read(job_id)
            item = self._find_revision(job, revision)
            timestamp = utc_now()
            item.update(
                {
                    "status": "ready",
                    "updated_at": timestamp,
                    "summary": summary,
                    "error": None,
                    "validation": validation,
                    "artifacts": {
                        "step": f"/api/jobs/{job_id}/revisions/{revision}/model.step",
                        "stl": f"/api/jobs/{job_id}/revisions/{revision}/model.stl",
                    },
                }
            )
            job["status"] = "ready"
            job["current_revision"] = revision
            job["pending_revision"] = None
            job["updated_at"] = timestamp
            job["messages"].append(
                {
                    "role": "assistant",
                    "kind": "result",
                    "revision": revision,
                    "text": summary or f"模型 V{revision} 已生成并通过校验。",
                    "created_at": timestamp,
                }
            )
            self._write(job)
            return deepcopy(job)

    def fail_revision(self, job_id: str, revision: int, error: str) -> dict[str, Any]:
        with self._lock:
            job = self._read(job_id)
            item = self._find_revision(job, revision)
            timestamp = utc_now()
            clean_error = error.strip()[-4000:] or "模型生成失败。"
            item.update({"status": "failed", "updated_at": timestamp, "error": clean_error})
            job["status"] = "failed"
            job["pending_revision"] = None
            job["updated_at"] = timestamp
            job["messages"].append(
                {
                    "role": "assistant",
                    "kind": "error",
                    "revision": revision,
                    "text": f"V{revision} 生成失败：{clean_error}",
                    "created_at": timestamp,
                }
            )
            self._write(job)
            return deepcopy(job)

    def revision_dir(self, job_id: str, revision: int, create: bool = False) -> Path:
        self._validate_job_id(job_id)
        if revision < 1:
            raise ValueError("revision must be positive")
        path = self.root / job_id / "revisions" / f"{revision:03d}"
        if create:
            path.mkdir(parents=True, exist_ok=False)
        return path

    def artifact_path(self, job_id: str, revision: int, filename: str) -> Path:
        if filename not in {"model.step", "model.stl"}:
            raise ValueError("unsupported artifact")
        self.get_job(job_id)
        return self.revision_dir(job_id, revision) / "output" / filename

    @staticmethod
    def _new_revision(number: int, prompt: str, created_at: str) -> dict[str, Any]:
        return {
            "number": number,
            "request": prompt,
            "status": "queued",
            "created_at": created_at,
            "updated_at": created_at,
            "summary": None,
            "error": None,
            "artifacts": {},
            "validation": None,
        }

    def _manifest_path(self, job_id: str) -> Path:
        self._validate_job_id(job_id)
        return self.root / job_id / "manifest.json"

    def _read(self, job_id: str) -> dict[str, Any]:
        path = self._manifest_path(job_id)
        if not path.exists():
            raise JobNotFoundError(job_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, job: dict[str, Any]) -> None:
        path = self._manifest_path(job["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(job, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)

    @staticmethod
    def _find_revision(job: dict[str, Any], revision: int) -> dict[str, Any]:
        for item in job["revisions"]:
            if item["number"] == revision:
                return item
        raise JobStateError(f"版本 V{revision} 不存在。")

    @staticmethod
    def _validate_job_id(job_id: str) -> None:
        if not JOB_ID_PATTERN.fullmatch(job_id):
            raise JobNotFoundError(job_id)

    def _recover_interrupted_jobs(self) -> None:
        with self._lock:
            for path in self.root.glob("*/manifest.json"):
                try:
                    job = json.loads(path.read_text(encoding="utf-8"))
                    if job.get("status") not in ACTIVE_STATUSES:
                        continue
                    revision = job.get("pending_revision")
                    if revision is None:
                        continue
                    item = self._find_revision(job, revision)
                    timestamp = utc_now()
                    message = "本地服务在任务完成前停止，请重新提交这次需求。"
                    item.update({"status": "failed", "updated_at": timestamp, "error": message})
                    job.update(
                        {
                            "status": "failed",
                            "pending_revision": None,
                            "updated_at": timestamp,
                        }
                    )
                    self._write(job)
                except (OSError, ValueError, KeyError, TypeError):
                    continue
