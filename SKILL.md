---
name: auto-modeling
description: Convert natural-language mechanical design requests into parameterized CadQuery 3D models. Use when Codex needs to create, modify, validate, export, or iterate CAD models from text requirements, especially STEP/STL deliverables, FreeCAD/CAD Assistant review workflows, threaded connectors, tubes, nozzles, fit-check assemblies, cutaways, or dimensioned inspection sketches.
---

# Auto Modeling

## Core Workflow

Use this skill to turn a user's natural language request into a repeatable CAD workflow:

1. Capture requirements: object purpose, units, key dimensions, tolerances, interfaces, material/manufacturing constraints, output formats, and whether the user wants a new model or an edit.
2. State assumptions briefly when dimensions or interfaces are missing. Use millimeters unless the user specifies otherwise.
3. Create or edit a parameterized CadQuery Python script. Keep dimensions in a named parameter block near the top.
4. Include `validate_parameters()`, `build_model()`, and `export_model()` functions for non-trivial models.
5. Export STEP first and STL when mesh output is useful. Put generated files under an `output/` directory.
6. Run the script with the CadQuery environment and fix runtime or boolean errors.
7. For complex internal geometry, add one review artifact: cutaway STEP/STL, fit-check assembly STEP, or SVG dimension sketch.
8. When the user asks for modifications, prefer parameter or localized geometry changes over rewriting the whole model.

## Environment

Before modeling, verify CadQuery is available:

```bash
python scripts/verify_cadquery.py
```

If CadQuery is missing, read `references/environment.md` and run:

```bash
scripts/setup_cadquery_env.sh .venv
```

Use FreeCAD or CAD Assistant only for inspection and optional manual review; do not require a GUI for batch model generation.

## Modeling Rules

- Use a clear coordinate convention in the model docstring.
- Keep all major dimensions in millimeters and in one parameter section.
- Use robust booleans: create external solids first, then subtract channel/socket cutters, then add threaded ridges or external features.
- Use `clean()` after fragile boolean or thread operations.
- Prefer STEP for editable CAD exchange; use STL for slicing or quick mesh preview.
- For threads, use `cq.Wire.makeHelix()` plus a swept profile; use simplified threads only when the user says visual/non-functional thread is acceptable.
- For assemblies, use `cq.Assembly()` and place components by explicit interface coordinates.
- For fit checks, preserve separate part names in the assembly.

## Resources

- `references/environment.md`: Python, CadQuery, FreeCAD, CAD Assistant setup.
- `references/workflow.md`: Natural-language-to-CAD workflow and validation checklist.
- `references/cadquery_patterns.md`: Reusable CadQuery construction patterns from this workspace.
- `references/prompt_templates.md`: Prompts for new models, edits, fit checks, and review artifacts.
- `references/troubleshooting.md`: Common CadQuery and export failures.
- `assets/templates/parametric_part.py`: Starter script for a single parameterized part.
- `assets/templates/assembly_fit_check.py`: Starter script for STEP fit-check assemblies.
- `assets/templates/dimensioned_section_svg.py`: Starter SVG inspection drawing pattern.
- `scripts/run_model.py`: Run a CadQuery model script and report generated STEP/STL/SVG files.
- `scripts/export_preview.py`: Create a simple CadQuery preview model for environment smoke tests.
