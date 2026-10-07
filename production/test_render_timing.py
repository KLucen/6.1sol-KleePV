"""Focused regression checks for the PV's exact source exposure boundaries."""

import copy
import json
from pathlib import Path
import unittest

from compose import validate_render_timing

ROOT = Path(__file__).resolve().parent


class RenderTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))

    def timeline(self, frames):
        return {"source": self.metadata["source"], "frames": frames, "fps": 24,
                "source_frames": len(self.metadata["pts"]), "source_pts": self.metadata["pts"][:frames]}

    def test_117_frame_tail(self):
        timing = validate_render_timing(self.timeline(117), self.metadata)
        self.assertEqual((timing["boundary_seconds"], timing["last_pts_ticks"], timing["last_duration_ticks"]),
                         (4.875, 77328, 672))
        self.assertIn("eq(PTS\\,77328)", timing["packet_duration_bsf"])

    def test_210_frame_tail(self):
        timing = validate_render_timing(self.timeline(210), self.metadata)
        self.assertEqual((timing["boundary_seconds"], timing["last_pts_ticks"], timing["last_duration_ticks"]),
                         (8.75, 139328, 672))

    def test_full_source_tail_uses_stream_duration(self):
        timing = validate_render_timing(self.timeline(len(self.metadata["pts"])), self.metadata)
        self.assertEqual((timing["boundary_seconds"], timing["last_pts_ticks"], timing["last_duration_ticks"]),
                         (152.416625, 2438000, 666))

    def test_invalid_quantization_rejected_even_when_timeline_matches(self):
        metadata = copy.deepcopy(self.metadata)
        metadata["pts"][1] = 1 / 24
        timeline = self.timeline(117)
        timeline["source_pts"] = metadata["pts"][:117]
        with self.assertRaisesRegex(ValueError, "quantized"):
            validate_render_timing(timeline, metadata)

    def test_timeline_metadata_mismatch_rejected(self):
        timeline = self.timeline(117)
        timeline["source_pts"] = list(timeline["source_pts"])
        timeline["source_pts"][1] = 0.041
        with self.assertRaisesRegex(ValueError, "exactly match"):
            validate_render_timing(timeline, self.metadata)

    def test_missing_pts_rejected(self):
        timeline = self.timeline(117)
        timeline.pop("source_pts")
        with self.assertRaisesRegex(ValueError, "exactly match"):
            validate_render_timing(timeline, self.metadata)

    def interval(self, start, end):
        timeline = self.timeline(end-start)
        timeline["source_start"] = start
        timeline["source_pts"] = self.metadata["pts"][start:end]
        return timeline

    def test_title_interval_exact_source_phase(self):
        timing = validate_render_timing(self.interval(1296, 1502), self.metadata)
        self.assertEqual(timing["source_start_seconds"], 54.0)
        self.assertEqual(timing["boundary_seconds"], 8.583)
        self.assertEqual(timing["last_pts_ticks"], 136672)
        self.assertEqual(timing["last_duration_ticks"], 656)

    def test_nonzero_quantization_phase_kept(self):
        timeline = self.interval(1297, 1301)
        timing = validate_render_timing(timeline, self.metadata)
        self.assertEqual(timing["source_start_ticks"], 864672)
        self.assertEqual(timing["boundary_seconds"], 0.166)
        self.assertEqual(timing["last_pts_ticks"], 2000)

    def test_interval_cannot_use_prefix_pts(self):
        timeline = self.interval(1296, 1502)
        timeline["source_pts"] = self.metadata["pts"][:206]
        with self.assertRaisesRegex(ValueError, "exactly match"):
            validate_render_timing(timeline, self.metadata)

    def test_negative_and_overrun_intervals_rejected(self):
        for start, frames in [(-1, 1), (3657, 2), (100, 0)]:
            timeline = self.timeline(1)
            timeline.update(source_start=start, frames=frames)
            with self.assertRaisesRegex(ValueError, "valid source range"):
                validate_render_timing(timeline, self.metadata)


if __name__ == "__main__":
    unittest.main()
