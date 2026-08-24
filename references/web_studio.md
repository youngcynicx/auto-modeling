# Local Web Studio

The Local Web Studio is a small browser interface around the Auto Modeling
workflow. It accepts a mechanical design request, asks Codex to create or update
a parameterized CadQuery script, validates the exported geometry, and displays
the resulting STL in a Three.js viewport.

The first version is intentionally local and single-user. It does not include
accounts, remote deployment, a database, shared projects, or production job
orchestration.

## User Workflow

1. Enter a natural-language description of a mechanical part.
2. The page creates a job and displays its current processing state.
3. Codex adapts a parameterized CadQuery template inside an isolated revision
   directory.
4. CadQuery exports `model.step` and `model.stl`.
5. The service reimports the STEP file and checks its solids, shape validity,
   volume, and bounding box.
6. The page loads the STL into an interactive preview.
7. Enter a follow-up change. The service copies the last valid `model.py` into
   a new revision and asks Codex to make a localized edit.
8. The preview switches only after the new revision passes validation. A failed
   edit leaves the previous valid revision available.

## Architecture

```text
Browser
  ├─ natural-language request and revision history
  └─ Three.js STL preview
          │
          ▼
FastAPI local service
  ├─ JSON job store
  ├─ single-worker revision queue
  ├─ Codex non-interactive runner
  └─ CadQuery export and STEP validation
          │
          ▼
output/web-jobs/<job-id>/revisions/<revision>/
  ├─ model.py
  ├─ request.txt
  ├─ validation.json
  └─ output/
      ├─ model.step
      └─ model.stl
```

The relevant source directories are:

- `web/static/`: the single-page interface and Three.js viewer
- `web/server.py`: the FastAPI routes and static file server
- `web/services/job_store.py`: JSON manifests and revision state
- `web/services/codex_runner.py`: restricted Codex CLI invocation
- `web/services/model_runner.py`: CadQuery execution and geometry validation
- `web/services/modeling_service.py`: background job orchestration
- `tests/`: job versioning and geometry validation tests

## Requirements

- Python 3.11
- the repository CadQuery virtual environment
- Codex CLI installed and authenticated
- network access for Codex and the pinned Three.js modules used by the page

Install the web packages into the existing virtual environment:

```bash
.venv/bin/python -m pip install -r requirements-web.txt
```

Run the service:

```bash
.venv/bin/python scripts/run_web.py
```

Open `http://127.0.0.1:8000`.

The service binds to `127.0.0.1` by default. A different host or port can be
selected explicitly:

```bash
.venv/bin/python scripts/run_web.py --host 127.0.0.1 --port 8765
```

## Job and Revision State

A job moves through the following states:

```text
queued -> generating -> exporting -> validating -> ready
                                               \-> failed
```

Only one Codex job runs at a time. This keeps local CPU and agent usage
predictable while still allowing the HTTP service to respond to status polls.

Each requested change receives its own numbered directory. The current revision
pointer changes only after validation succeeds, so an invalid or interrupted
edit cannot overwrite the last known-good model.

Job manifests and CAD artifacts are stored under `output/web-jobs/`. The entire
`output/` tree is ignored by Git.

## HTTP API

### Create a model

```http
POST /api/jobs
Content-Type: application/json

{"prompt": "Create a 60 x 36 x 6 mm mounting plate with four holes."}
```

### Read job state

```http
GET /api/jobs/{job_id}
```

### Submit a modification

```http
POST /api/jobs/{job_id}/revisions
Content-Type: application/json

{"prompt": "Increase the plate thickness to 8 mm."}
```

### Download artifacts

```http
GET /api/jobs/{job_id}/revisions/{revision}/model.step
GET /api/jobs/{job_id}/revisions/{revision}/model.stl
```

## Runtime Configuration

The service accepts these optional environment variables:

- `AUTO_MODELING_CODEX`: absolute path to the Codex executable
- `AUTO_MODELING_PYTHON`: Python executable containing CadQuery
- `AUTO_MODELING_JOBS_ROOT`: alternate directory for generated jobs

Defaults are selected for the repository layout and the Codex binary bundled
with the ChatGPT desktop application on macOS.

## Safety Boundaries

The service invokes Codex with workspace-scoped write access and makes each
revision directory the working root. The prompt restricts edits to `model.py`
and CAD output to the revision's `output/` directory. After Codex exits, the
service independently reruns the script and validates the exported STEP.

The generated `model.py` is still agent-authored Python code. Keep the server
bound to localhost, use it only with trusted users, and do not expose this first
version directly to a network. A hosted or multi-user version should run model
generation inside an additional container or operating-system sandbox with
explicit resource limits and no access to personal files.

## Tests

Run the automated tests with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The tests cover preservation of the last valid revision after a failed edit and
CadQuery STEP/STL generation with solid, volume, and bounding-box validation.
