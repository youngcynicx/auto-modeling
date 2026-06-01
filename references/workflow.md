# Workflow

## 1. Parse the Request

Extract:

- object type and purpose
- units and scale
- fixed dimensions
- adjustable dimensions
- interfaces such as holes, threads, sockets, nozzles, tubes, bottle necks, or mounting points
- manufacturing constraints such as wall thickness, minimum radius, material, printability, or machining
- requested outputs: STEP, STL, cutaway, assembly, SVG dimensions

If the request is underspecified, make conservative assumptions and state them before or in the model docstring.

## 2. Choose a Modeling Pattern

- Block/bracket/enclosure: base solid plus cuts, fillets, chamfers.
- Tube: cylinder/frustum plus bore cutter.
- Nozzle or manifold: external body, internal channel cutters, optional cutaway.
- Threaded connector: cylinder plus helical swept ridge or valley.
- Assembly: import/build separate parts, translate/rotate to interface coordinates, save `cq.Assembly()`.
- Review drawing: generate an SVG schematic from the same parameters used by the model.

## 3. Generate the Script

Structure non-trivial scripts like this:

```python
"""
Parametric CadQuery model for ...

Coordinate convention:
- X ...
- Y ...
- Z ...
"""

from pathlib import Path
import cadquery as cq

# Parameters in millimeters

output_dir = Path(__file__).resolve().parent / "output"
step_path = output_dir / "part.step"
stl_path = output_dir / "part.stl"

def validate_parameters():
    ...

def build_model():
    validate_parameters()
    ...
    return model.clean()

def export_model(model):
    output_dir.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(model, str(step_path))
    cq.exporters.export(model, str(stl_path), tolerance=0.05, angularTolerance=0.1)

if __name__ == "__main__":
    model = build_model()
    export_model(model)
```

## 4. Validate

Run the script and verify:

- no exceptions
- output directory exists
- STEP file was written
- STL was written when requested
- parameters do not violate basic geometry constraints
- internal channels open to intended faces
- fit-check assemblies align at interfaces

For high-risk shapes, create at least one of:

- cutaway model
- dimensioned SVG section
- assembly with mating part

## 5. Iterate

When the user asks for modifications:

- identify whether it is a parameter change, feature addition, or topology change
- adjust top-level parameters first
- preserve coordinate convention and export names unless requested
- rerun script and report changed output files
