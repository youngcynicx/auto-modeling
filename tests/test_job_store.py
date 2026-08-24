from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from web.services.job_store import JobStore


class JobStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.template = root / "template.py"
        self.template.write_text("# starter\n", encoding="utf-8")
        self.store = JobStore(root / "jobs", self.template)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_failed_edit_keeps_last_ready_revision(self) -> None:
        job = self.store.create_job("Create a 20 mm cube")
        job_id = job["id"]
        validation = {
            "shape_valid": True,
            "solid_count": 1,
            "volume_mm3": 8000.0,
            "bounding_box_mm": {"x": 20.0, "y": 20.0, "z": 20.0},
        }
        self.store.complete_revision(job_id, 1, "Cube ready", validation)

        edited = self.store.add_revision(job_id, "Make it 25 mm high")
        self.assertEqual(edited["current_revision"], 1)
        self.assertEqual(edited["pending_revision"], 2)

        failed = self.store.fail_revision(job_id, 2, "test failure")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["current_revision"], 1)
        self.assertEqual(failed["revisions"][0]["status"], "ready")
        self.assertEqual(failed["revisions"][1]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
