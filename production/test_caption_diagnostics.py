"""Ensure subtitle QA detects both lost source ink and added bubble glyphs."""

import unittest

import numpy as np

from compose import ROOT, compose, read_image
from review_interval import caption_diagnostics


class CaptionDiagnosticsTests(unittest.TestCase):
    def test_empty_render_detects_lost_source_ink(self):
        source = read_image(ROOT / "source_refs/src-0082-f0290.png")
        rows = caption_diagnostics(source, np.zeros_like(source), 290)
        self.assertGreater(rows[0]["source_bright_core_pixels"], 0)
        self.assertGreater(rows[0]["core_mismatch_gt30_pixels"], 0)

    def test_extra_bubble_text_detected_then_cleared(self):
        source = read_image(ROOT / "source_refs/src-0082-f0290.png")
        generated = read_image(ROOT / "generated/candidate-005.png")
        before, _, _ = compose(source, source, generated)
        after, _, _ = compose(source, source, generated, asset_source_frame=287,
                               asset_name="candidate-005.png", current_frame=290)
        self.assertGreater(caption_diagnostics(source, before, 290)[-1]["whole_region_mismatch_pixels"], 0)
        self.assertEqual(caption_diagnostics(source, after, 290)[-1]["whole_region_mismatch_pixels"], 0)

    def test_corrected_prone_lyric_has_no_missing_bright_core(self):
        source = read_image(ROOT / "source_refs/src-0281-f0661.png")
        generated = read_image(ROOT / "generated/fine-f0661-source-extent-v2.png")
        output, _, _ = compose(source, source, generated, asset_source_frame=661,
                               asset_name="fine-f0661-source-extent-v2.png", current_frame=665)
        rows = caption_diagnostics(source, output, 665)
        self.assertGreater(rows[0]["source_bright_core_pixels"], 0)
        self.assertEqual(rows[0]["core_mismatch_gt30_pixels"], 0)

    def test_unregistered_later_shot_not_claimed_checked(self):
        source = read_image(ROOT / "source_refs/src-0281-f0661.png")
        self.assertEqual(caption_diagnostics(source, source, 700), [])


if __name__ == "__main__":
    unittest.main()
