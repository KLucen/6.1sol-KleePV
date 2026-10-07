"""Tests of the private proposal only; no production helper is patched."""

import unittest

import numpy as np

from restoration_plan import PROPOSED_RECT, apply_proposed_source_restore


class Pre831CaptionPlanTests(unittest.TestCase):
    def setUp(self):
        self.source = np.full((1080, 1920, 3), [242, 136, 154], np.uint8)
        self.output = np.full_like(self.source, [30, 40, 70])

    def test_proposal_is_exact_source_inside_only_the_small_rect(self):
        output, mask = apply_proposed_source_restore(self.output.copy(), self.source, 827)
        x0, y0, x1, y1 = PROPOSED_RECT
        np.testing.assert_array_equal(output[y0:y1,x0:x1], self.source[y0:y1,x0:x1])
        np.testing.assert_array_equal(output[mask == 0], self.output[mask == 0])

    def test_all_four_827_to_830_frames_use_the_same_proposal_scope(self):
        for frame in range(827, 831):
            _, mask = apply_proposed_source_restore(self.output.copy(), self.source, frame)
            self.assertEqual(np.count_nonzero(mask), (1022-870)*(1044-954))

    def test_start_is_safe_shot_not_prior_macro_lyric(self):
        for frame in (810, 811, 831):
            output, mask = apply_proposed_source_restore(self.output.copy(), self.source, frame)
            np.testing.assert_array_equal(output, self.output)
            self.assertFalse(np.any(mask))

    def test_modified_pixels_are_all_declared(self):
        output, mask = apply_proposed_source_restore(self.output.copy(), self.source, 812)
        self.assertEqual(np.count_nonzero(np.any(output != self.output, axis=2) & (mask == 0)), 0)


if __name__ == "__main__":
    unittest.main()
