"""Read-only regression tests for the private generation archive."""

import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SPEC = importlib.util.spec_from_file_location("private_archive", OUT / "archive_root_promptset.py")
ARCHIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARCHIVE)


class PrivateArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "jobs/star-f1091-underarm-hair-repair-2026-10-05-v2.json"
        cls.raw = cls.path.read_bytes()
        cls.job = json.loads(cls.raw)
        manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
        cls.cels = {row["canonical_source_frame"]: row for row in manifest["cels"]}
        cls.selected = json.loads((ROOT / "asset_selections.json").read_text(encoding="utf-8"))["selections"]

    def inspect(self, job=None):
        return ARCHIVE.inspect_job(self.path, self.raw, job or self.job, self.cels, self.selected, None, False)

    def test_failed_variant_retains_full_prompt_and_pending_disposition(self):
        record = self.inspect()
        self.assertEqual(record["full_prompt_original"], self.job["prompt"])
        self.assertEqual(record["job_original_complete"], self.job)
        self.assertTrue(record["job_reports_failed_or_blocking_unselected"])
        self.assertEqual(record["final_disposition"], "pending_root_batch_completion_and_final_adoption")
        self.assertFalse(record["accepted"])
        self.assertFalse(record["original_speed_review_performed_by_archivist"])

    def test_actual_file_dimensions_and_hash_cover_missing_job_fields(self):
        record = self.inspect()
        self.assertTrue(record["completed_builtin_output_call_evidence"])
        self.assertEqual(record["workspace_output"]["sha256"], record["builtin_tool_origin"]["sha256"])
        self.assertEqual(record["workspace_output"]["dimensions"], record["builtin_tool_origin"]["dimensions"])
        self.assertIn("job_omits_output_dimensions_archive_measured_real_png", record["metadata_warnings"])
        self.assertIn("job_omits_output_sha256_archive_hashed_real_png", record["metadata_warnings"])
        self.assertEqual(record["issues"], [])

    def test_recorded_bad_dimensions_and_hash_are_detected(self):
        job = copy.deepcopy(self.job)
        job["output_dimensions"] = [1, 1]
        job["output_sha256"] = "incorrect"
        record = self.inspect(job)
        self.assertIn("recorded_output_dimensions_mismatch", record["issues"])
        self.assertIn("recorded_output_sha256_mismatch", record["issues"])

    def test_exposure_change_is_detected_without_modifying_original_job(self):
        job = copy.deepcopy(self.job)
        job["source_exposures"][0]["end"] += 1
        record = self.inspect(job)
        self.assertIn("original_source_exposure_mismatch", record["issues"])
        self.assertEqual(self.path.read_bytes(), self.raw)

    def test_seal_requires_real_completion_notice(self):
        with patch.object(sys, "argv", ["archive_root_promptset.py", "--seal"]):
            with self.assertRaisesRegex(ValueError, "root completion notice"):
                ARCHIVE.main()

    def test_caption_authorization_keeps_exact_human_reply_and_limits(self):
        authorization = json.loads((OUT / "caption-authorization.json").read_text(encoding="utf-8"))
        self.assertEqual(authorization["human_answer_original"], "允许先重建清晰字幕，看片后再指定返工。")
        self.assertTrue(authorization["scope"]["real_clear_glyphs_from_the_same_original_lyric_only"])
        self.assertFalse(authorization["scope"]["ai_generated_caption_allowed"])
        self.assertFalse(authorization["scope"]["artistic_acceptance_granted"])


if __name__ == "__main__":
    unittest.main()
