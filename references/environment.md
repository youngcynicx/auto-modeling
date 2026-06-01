# Environment Setup

Use this reference when a machine has not been prepared for natural-language-to-CAD modeling.

## Required

- Python 3.11
- CadQuery 2.7.0 or newer compatible 2.x release
- A shell that can run Python scripts

Recommended local setup:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install cadquery==2.7.0
python - <<'PY'
import cadquery as cq
print("CadQuery", cq.__version__)
PY
```

This workspace was verified with:

- Python `3.11.15`
- CadQuery `2.7.0`

## Optional Review Tools

Use FreeCAD for opening, inspecting, and manually editing STEP/STL outputs. On macOS arm64, the local workspace used `FreeCAD_1.1.1-macOS-arm64-py311.dmg`.

Known local SHA256 for that DMG:

```text
fbcab489c3d37057c2283e298ef2d50c4930cc988fb331ea7df3ad75879e3949
```

Do not commit `.venv/`, `FreeCAD.app/`, `.dmg`, generated STEP/STL files, or output folders to the skill repository unless the user explicitly wants binary artifacts.

CAD Assistant is a lightweight viewer option for STEP, IGES, STL, OBJ, and related exchange files.

## Suggested `.gitignore`

```gitignore
.venv/
FreeCAD.app/
*.dmg
output/
*.step
*.stl
*.FCStd
__pycache__/
.DS_Store
```
