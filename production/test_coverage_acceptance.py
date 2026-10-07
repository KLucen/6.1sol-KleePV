"""Acceptance counts require explicit review records for selected artwork."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import audit_full_pv_coverage as audit


class CoverageAcceptanceTests(unittest.TestCase):
    def test_only_real_booleans_record_acceptance(self):
        for record in ({}, {"accepted": "true"}, {"accepted": 1},
                       {"status": "generated", "technical_accepted": True,
                        "review": "manual_full_resolution_source_approved"}):
            with self.subTest(record=record):
                result = audit.recorded_acceptance([("job.json", record)])
                self.assertIsNone(result["artistic_accepted"])
                self.assertEqual(result["artistic_acceptance_status"], "not_recorded")
                self.assertEqual(result["artistic_acceptance_records"], [])

    def test_artistic_field_precedes_legacy_accepted(self):
        result = audit.recorded_acceptance([
            ("job.json", {"accepted": True, "artistic_accepted": False})])
        self.assertIs(result["artistic_accepted"], False)
        self.assertEqual(result["artistic_acceptance_status"], "explicit_not_accepted")
        self.assertEqual(result["artistic_acceptance_records"], [
            {"source": "job.json", "field": "artistic_accepted", "value": False}])

    def test_conflicting_records_remain_unknown(self):
        result = audit.recorded_acceptance([
            ("selection", {"accepted": True}), ("job.json", {"accepted": False})])
        self.assertIsNone(result["artistic_accepted"])
        self.assertEqual(result["artistic_acceptance_status"], "conflicting")
        self.assertEqual(len(result["artistic_acceptance_records"]), 2)

    def test_main_counts_selected_flags_without_changing_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("generated", "jobs", "qa", "source_refs"):
                (root / directory).mkdir()

            def write_json(name, value):
                (root / name).write_text(json.dumps(value), encoding="utf-8")

            for name in ("make_timeline.py", "compose.py"):
                (root / name).write_text("# fixture\n", encoding="utf-8")
            for name in ("fine-f0000.png", "fine-f0001.png", "fine-f0002.png",
                         "fine-f0003.png", "selected-003.png", "selected-004.png"):
                Image.new("RGB", (16, 9)).save(root / "generated" / name)
            Image.new("RGB", (16, 9)).save(root / "source_refs/blank.png")

            cels = [f"cel-{index:04d}" for index in range(7)] + ["cel-0064"]
            candidates = [{"id": f"src-{index:04d}", "frame": index,
                           "start": index, "end": index + 1, "cel": cel,
                           "reference": f"source_refs/{cel}.png", "family": "test",
                           "review": "independent_candidate"}
                          for index, cel in enumerate(cels)]
            exposures = [{"start": index, "end": index + 1, "pts": index,
                          "end_pts": index + 1, "cel": cel, "family": "test",
                          "source_transform": {"kind": "identity"}}
                         for index, cel in enumerate(cels)]
            write_json("source_map.json", {"source": "fixture.mp4", "frames": 8,
                       "candidates": candidates, "cels": candidates,
                       "frame_to_cel": cels, "source_exposures": exposures,
                       "families": ["test"], "deduplication": {
                           "camera_similarity_evidence": [],
                           "uncertain_pairs_kept_separate": []}})
            write_json("source_meta.json", {})
            write_json("source_aliases.json", {"aliases": [{
                "source_cel": cels[5], "verified_target_cel": cels[0],
                "review": "manual_full_resolution_source_approved", "accepted": True}]})
            write_json("generation_jobs.json", {"old_anchor_to_cel": []})
            write_json("qa/late-title-copy-candidates.json", [])
            write_json("asset_selections.json", {"accepted": False, "selections": [
                {"source_frame": 3, "path": "generated/selected-003.png",
                 "review": "draft", "accepted": True},
                {"source_frame": 4, "path": "generated/selected-004.png",
                 "review": "draft", "accepted": True},
                {"source_frame": 7, "path": "source_refs/blank.png",
                 "review": "source reuse", "artistic_accepted": True}]})
            job_records = [
                ("technical", {"output": "generated/fine-f0000.png", "status": "generated",
                               "technical_accepted": True}),
                ("accepted", {"output": "generated/fine-f0001.png", "accepted": True}),
                ("pending", {"output": "generated/fine-f0002.png", "accepted": True,
                             "artistic_accepted": False}),
                ("unselected", {"output": "generated/fine-f0003.png", "accepted": False}),
                ("conflicting", {"output": "generated/selected-004.png", "accepted": False})]
            for name, record in job_records:
                write_json(f"jobs/{name}.json", record)

            with patch.object(audit, "ROOT", root), redirect_stdout(io.StringIO()):
                audit.main()
            manifest = audit.read(root / "full-pv-progress-manifest.json")
            report = audit.read(root / "full-pv-coverage-report.json")
            records = {record["cel"]: record for record in manifest["cels"]}
            summary = manifest["summary"]
            self.assertEqual(summary["mapped_cels_including_source_reuse"], 7)
            self.assertEqual(summary["direct_selected_asset_cels"], 6)
            self.assertEqual(summary["verified_alias_expansion_cels"], 1)
            self.assertEqual(summary["missing_selected_cels"], 1)
            self.assertEqual(summary["covered_frames_draft_plus_source_reuse"], 7)
            self.assertEqual(summary["accepted_character_cels"], 2)
            self.assertEqual(report["families"][0]["accepted_cels"], 3)
            self.assertEqual(summary["artistic_acceptance_status_counts"], {
                "not_recorded": 3, "accepted": 3,
                "explicit_not_accepted": 1, "conflicting": 1})
            self.assertEqual(summary["mapped_artistic_acceptance_status_counts"]["not_recorded"], 2)
            self.assertIs(records[cels[3]]["artistic_accepted"], True)
            self.assertIs(records[cels[2]]["artistic_accepted"], False)
            for index in (0, 4, 5, 6):
                self.assertIsNone(records[cels[index]]["artistic_accepted"])
            self.assertIs(manifest["accepted"], False)


if __name__ == "__main__":
    unittest.main()
