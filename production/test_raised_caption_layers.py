"""Focused scope, glyph registration and bright-subject contrast regressions."""

from pathlib import Path
import json
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import compose as compositor
from raised_caption_layers import (DONOR, REGION, SOURCE_INTERVAL, raised_caption_layer,
                                   raised_caption_extent, restore_raised_captions,
                                   cream_glyph_candidate)

ROOT = Path(__file__).resolve().parent


class RaisedCaptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(2)
        cls.source = cv2.imread(str(DONOR))
        cls.layer = raised_caption_layer()

    def test_exact_scope_and_unedited_source_is_untouched(self):
        self.assertEqual(SOURCE_INTERVAL, (1225, 1285))
        for frame in (None, 812, 831, 886, 897, 910, 1224, 1285):
            output, mask = restore_raised_captions(self.source.copy(), self.source, frame)
            np.testing.assert_array_equal(output, self.source)
            self.assertFalse(np.any(mask))
            self.assertFalse(np.any(raised_caption_extent(frame)))
        for frame in (1225, 1261, 1284):
            output, mask = restore_raised_captions(self.source.copy(), self.source, frame,
                                                   np.ones(self.source.shape[:2], np.uint8)*255)
            np.testing.assert_array_equal(output, self.source)
            self.assertFalse(np.any(mask))

    def test_registered_strokes_exclude_old_button_and_between_lines(self):
        layer = self.layer
        self.assertGreater(np.count_nonzero(layer["source_core"]), 7000)
        self.assertTrue(np.all(layer["core_votes"][layer["source_core"]] >= 5))
        self.assertTrue(np.all(layer["alpha"][~layer["extent"]] == 0))
        x0, y0, _, _ = REGION
        # Button center moves between the two lines in the primary native donor.
        self.assertFalse(layer["extent"][990-y0, 927-x0])
        self.assertFalse(np.any(layer["alpha"][994-y0:1002-y0]))
        # The genuine horizontal stroke of Japanese "ni" is not lost to B >= G.
        self.assertGreater(np.count_nonzero(layer["source_core"][963-y0:970-y0, 899-x0:914-x0]), 30)

    def test_source_core_rgb_and_outside_declared_support_are_preserved(self):
        x0, y0, x1, y1 = REGION
        for frame in (1225, 1229, 1241, 1256, 1261, 1282, 1284):
            with self.subTest(frame=frame):
                file = next((ROOT / "source_refs").glob(f"*-f{frame:04d}.png"))
                source = cv2.imread(str(file))
                underlay = source.copy()
                underlay[y0:y1, x0:x1] = (35, 48, 68)
                before = underlay.copy()
                output, mask = restore_raised_captions(underlay, source, frame)
                crop = source[y0:y1, x0:x1]
                observed = self.layer["source_core"] & cream_glyph_candidate(crop)
                self.assertGreater(np.count_nonzero(observed), 7000)
                np.testing.assert_array_equal(output[y0:y1, x0:x1][observed], crop[observed])
                np.testing.assert_array_equal(output[mask == 0], before[mask == 0])
                self.assertFalse(np.any((mask[y0:y1, x0:x1] != 0) & (self.layer["alpha"] == 0)))

    def test_fixed_one_pixel_edge_requires_edited_actual_bright_subject(self):
        x0, y0, x1, y1 = REGION
        underlay = self.source.copy()
        underlay[y0:y1, x0:x1] = self.layer["foreground_bgr"]
        before = underlay.copy()
        subject = np.ones(self.source.shape[:2], np.uint8)*255
        subject[:, :940] = 0
        output, mask = restore_raised_captions(underlay, self.source, 1261, subject)
        changed = np.any(output[y0:y1, x0:x1] != before[y0:y1, x0:x1], axis=2)
        edge = changed & (self.layer["alpha"] == 0)
        self.assertGreater(np.count_nonzero(edge), 100)
        self.assertFalse(np.any(edge & ~self.layer["contrast_edge_support"]))
        self.assertFalse(np.any(edge & (subject[y0:y1, x0:x1] == 0)))
        np.testing.assert_array_equal(output[mask == 0], before[mask == 0])
        for color, explicit in (((35, 48, 68), subject), ((211, 223, 237), None)):
            underlay = self.source.copy()
            underlay[y0:y1, x0:x1] = color
            _, mask = restore_raised_captions(underlay, self.source, 1261, explicit)
            self.assertFalse(np.any((mask[y0:y1, x0:x1] != 0) & (self.layer["alpha"] == 0)))

    def test_actual_raised_cels_never_restore_generic_pale_old_collar(self):
        timeline = json.loads((ROOT / "timeline-raised-1225-1285-fast-draft-v1.json").read_text(encoding="utf-8"))
        for frame in (1225, 1261):
            with self.subTest(frame=frame):
                source = cv2.imread(str(next((ROOT / "source_refs").glob(f"*-f{frame:04d}.png"))))
                exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
                generated = compositor.read_image(ROOT / timeline["assets"][exposure["cel"]]["path"])
                forced = np.ones(source.shape[:2], np.uint8)*255
                with patch.object(compositor, "graphics_mask", return_value=forced):
                    output, _, masks = compositor.compose(source, source, generated, current_frame=frame)
                with patch.object(compositor, "graphics_mask", return_value=np.zeros_like(forced)):
                    expected, _, expected_masks = compositor.compose(source, source, generated, current_frame=frame)
                np.testing.assert_array_equal(output, expected)
                np.testing.assert_array_equal(masks, expected_masks)


if __name__ == "__main__":
    unittest.main()
