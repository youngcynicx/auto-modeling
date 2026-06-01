# Auto Modeling

Auto Modeling is a Codex skill for turning natural-language mechanical design requests into parameterized CadQuery 3D models. It guides an agent from a plain text idea to editable CAD outputs such as STEP and STL, then supports follow-up edits like changing dimensions, adding connectors, generating cutaways, or checking assemblies.

## What It Does

- Parse natural-language product or mechanical design requirements.
- Extract dimensions, units, interfaces, tolerances, and manufacturing constraints.
- Generate CadQuery Python models with clear parameter blocks.
- Export STEP for CAD exchange and STL for mesh workflows.
- Create review artifacts such as cutaway models, fit-check assemblies, and SVG dimension sketches.
- Iterate on existing models through localized parameter or geometry changes.

## Typical Workflow

1. Describe the object in natural language.
2. The agent identifies assumptions, key dimensions, and required outputs.
3. A parameterized CadQuery script is created or updated.
4. The script is run in a CadQuery environment.
5. STEP/STL files are exported under `output/`.
6. Optional review artifacts are generated for internal channels, threads, sockets, or mating parts.
7. The user asks for refinements, and the model is updated without starting from scratch.

Example request:

```text
Create a compact nozzle body with a 3 mm gas inlet, a 2.5 mm powder channel,
a threaded bottle socket on the bottom, and export STEP/STL files.
```

## Included Resources

- `SKILL.md`: core instructions loaded by Codex when the skill is used.
- `references/environment.md`: Python, CadQuery, FreeCAD, and CAD Assistant setup notes.
- `references/workflow.md`: natural-language-to-CAD workflow and validation checklist.
- `references/cadquery_patterns.md`: reusable CadQuery modeling patterns for tubes, threads, cutaways, and assemblies.
- `references/prompt_templates.md`: prompts for new models, edits, fit checks, and inspection drawings.
- `scripts/`: helper scripts for environment setup, CadQuery verification, model runs, and preview export.
- `assets/templates/`: starter CadQuery templates for parts, fit-check assemblies, and SVG section drawings.

## Quick Start

Clone the repository and verify the skill structure:

```bash
git clone https://github.com/youngcynicx/auto-modeling.git
cd auto-modeling
```

Set up CadQuery if needed:

```bash
scripts/setup_cadquery_env.sh .venv
. .venv/bin/activate
```

Verify CadQuery:

```bash
python scripts/verify_cadquery.py
```

Generate a preview model:

```bash
python scripts/export_preview.py
```

## Design Principles

- Keep models parameterized and editable.
- Use millimeters unless the user specifies otherwise.
- Prefer STEP as the primary CAD exchange format.
- Add validation checks before export.
- Generate review artifacts for complex geometry before treating the design as complete.
- Modify existing scripts incrementally during iteration instead of rewriting working geometry.
