from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from web.services.model_runner import run_model, validate_outputs


MODEL_SCRIPT = """
from pathlib import Path
import cadquery as cq

output_dir = Path(__file__).resolve().parent / "output"

def build_model():
    return cq.Workplane("XY").box(20, 12, 5)

def export_model(model):
    output_dir.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(model, str(output_dir / "model.step"))
    cq.exporters.export(model, str(output_dir / "model.stl"))

if __name__ == "__main__":
    export_model(build_model())
"""


class ModelRunnerTests(unittest.TestCase):
    def test_runs_and_validates_step_and_stl(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            revision_dir = Path(temporary)
            (revision_dir / "model.py").write_text(
                textwrap.dedent(MODEL_SCRIPT), encoding="utf-8"
            )
            run_model(revision_dir, Path(sys.executable))
            result = validate_outputs(revision_dir)

            self.assertTrue(result["shape_valid"])
            self.assertEqual(result["solid_count"], 1)
            self.assertEqual(result["bounding_box_mm"], {"x": 20.0, "y": 12.0, "z": 5.0})
            self.assertAlmostEqual(result["volume_mm3"], 1200.0, places=2)


if __name__ == "__main__":
    unittest.main()
