# Prompt Templates

## New Model

```text
Convert this natural-language mechanical design into a parameterized CadQuery model.
Use millimeters. First identify dimensions, assumptions, interfaces, and output files.
Then create a Python script with validate_parameters(), build_model(), and export_model().
Export STEP and STL to output/.
Request: ...
```

## Edit Existing Model

```text
Modify the existing CadQuery model for this change.
Prefer adjusting top-level parameters; only edit geometry functions when needed.
Preserve coordinate convention, output paths, and unrelated features.
Run the model script and confirm regenerated files.
Change request: ...
```

## Fit Check

```text
Create a fit-check assembly for these CadQuery parts.
Align mating interfaces using explicit coordinates, preserve separate part names in cq.Assembly(),
and export a STEP assembly to output/.
Parts/interfaces: ...
```

## Cutaway or Inspection Drawing

```text
Generate a review artifact for this model: either a cutaway STEP/STL or an SVG X-Z section.
Use the same parameters as the CAD model. Show internal channels, sockets, threads, and key dimensions.
This is for inspection, not a manufacturing drawing.
```

## Iteration Loop

```text
The user has reviewed the output and requested changes.
Map each requested change to parameters or local geometry edits, update the script, rerun export,
and summarize the exact regenerated output files.
Review notes: ...
```
