"""The safe lyric rectangle is tied to the six inspected draft assets."""

import unittest

import numpy as np

from compose import ROOT, compose, read_image
from dance_caption_layers import CLEAR_ASSETS, CLEAR_REGION, restore_clear_dance_captions


class ClearDanceCaptionTests(unittest.TestCase):
    def setUp(self):
        self.source = np.full((1080, 1920, 3), [209, 226, 237], np.uint8)
        self.output = np.full_like(self.source, [30, 40, 70])

    def test_all_registered_exposures_copy_exactly_the_safe_rectangle(self):
        x0, y0, x1, y1 = CLEAR_REGION
        for name, (start, end) in CLEAR_ASSETS.items():
            for frame in range(start, end):
                with self.subTest(asset=name, frame=frame):
                    output, mask = restore_clear_dance_captions(self.output.copy(), self.source, frame, name)
                    np.testing.assert_array_equal(output[y0:y1, x0:x1], self.source[y0:y1, x0:x1])
                    np.testing.assert_array_equal(output[mask == 0], self.output[mask == 0])
                    self.assertEqual(np.count_nonzero(mask), (x1-x0)*(y1-y0))

    def test_unknown_new_draft_does_not_paste_the_source_rectangle(self):
        for name in (None, "root-continuation-f0827-v2.png"):
            output, mask = restore_clear_dance_captions(self.output.copy(), self.source, 827, name)
            np.testing.assert_array_equal(output, self.output)
            self.assertFalse(np.any(mask))

    def test_macro_and_wrong_asset_exposures_are_noops(self):
        for frame in (810, 811, 812, 826, 831):
            output, mask = restore_clear_dance_captions(self.output.copy(), self.source, frame,
                                                       "root-continuation-f0827-v1.png")
            np.testing.assert_array_equal(output, self.output)
            self.assertFalse(np.any(mask))

    def test_actual_back_view_lyrics_remain_source_exact(self):
        source = read_image(ROOT/"source_refs/src-0373-f0827.png")
        generated = read_image(ROOT/"generated/root-continuation-f0827-v1.png")
        output, _, masks = compose(source, source, generated, asset_source_frame=827,
                                   current_frame=827, asset_name="root-continuation-f0827-v1.png")
        x0, y0, x1, y1 = CLEAR_REGION
        np.testing.assert_array_equal(output[y0:y1, x0:x1], source[y0:y1, x0:x1])
        self.assertEqual(np.count_nonzero(np.any(output != source, axis=2) & np.all(masks == 0, axis=2)), 0)


if __name__ == "__main__":
    unittest.main()
