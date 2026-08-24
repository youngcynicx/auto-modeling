from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .services.job_store import JobBusyError, JobNotFoundError, JobStateError, JobStore
from .services.modeling_service import ModelingService


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = PROJECT_ROOT / "web" / "static"
JOBS_ROOT = Path(
    os.environ.get("AUTO_MODELING_JOBS_ROOT", PROJECT_ROOT / "output" / "web-jobs")
)
PYTHON_PATH = Path(
    os.environ.get("AUTO_MODELING_PYTHON", PROJECT_ROOT / ".venv" / "bin" / "python")
)

store = JobStore(JOBS_ROOT, PROJECT_ROOT / "assets" / "templates" / "parametric_part.py")
service = ModelingService(store, PYTHON_PATH)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    service.shutdown()


app = FastAPI(title="Auto Modeling Studio", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=12000)

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("请输入更完整的建模需求。")
        return cleaned


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_ROOT / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/jobs", status_code=status.HTTP_202_ACCEPTED)
def create_job(request: PromptRequest) -> dict:
    return service.submit_new(request.prompt.strip())


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    try:
        return store.get_job(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="任务不存在。") from exc


@app.post("/api/jobs/{job_id}/revisions", status_code=status.HTTP_202_ACCEPTED)
def create_revision(job_id: str, request: PromptRequest) -> dict:
    try:
        return service.submit_edit(job_id, request.prompt.strip())
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="任务不存在。") from exc
    except JobBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except JobStateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/jobs/{job_id}/revisions/{revision}/{filename}")
def get_artifact(job_id: str, revision: int, filename: str) -> FileResponse:
    try:
        path = store.artifact_path(job_id, revision, filename)
    except (JobNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="模型文件不存在。") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="模型文件尚未生成。")
    media_type = "model/stl" if filename.endswith(".stl") else "model/step"
    return FileResponse(path, media_type=media_type, filename=filename)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
