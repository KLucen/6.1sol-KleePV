"""Focused checks for source-derived dance lyrics, without a source-shoe plate."""

import unittest

import cv2
import numpy as np

from dance_caption_layers import (CANVAS_SHAPE, DONOR, REGION, dance_caption_extent,
                                  dance_caption_layer, extract_dance_caption_layer,
                                  restore_dance_captions, warm_glyph_core)


class DanceCaptionLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = cv2.imread(str(DONOR), cv2.IMREAD_COLOR)

    def test_scope_does_not_leak_outside_registered_phase(self):
        for frame in (None, 830, 911, 920):
            output = np.zeros_like(self.source)
            before = output.copy()
            restored, mask = restore_dance_captions(output, self.source, frame)
            np.testing.assert_array_equal(restored, before)
            self.assertFalse(np.any(mask))
            self.assertFalse(np.any(dance_caption_extent(frame)))

    def test_source_exact_frame_is_not_double_painted(self):
        restored, mask = restore_dance_captions(self.source.copy(), self.source, 831)
        np.testing.assert_array_equal(restored, self.source)
        self.assertFalse(np.any(mask))

    def test_interval_last_frame_still_has_the_registered_layer(self):
        self.assertTrue(np.any(dance_caption_extent(831)))
        self.assertTrue(np.any(dance_caption_extent(862)))
        self.assertTrue(np.any(dance_caption_extent(863)))
        self.assertTrue(np.any(dance_caption_extent(886)))
        self.assertTrue(np.any(dance_caption_extent(896)))

    def test_cream_hue12_is_included_but_pink_star_is_not_a_core(self):
        hsv = np.array([[[12, 35, 240], [170, 20, 228], [125, 110, 242]]], np.uint8)
        core = warm_glyph_core(cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR))
        np.testing.assert_array_equal(core, [[True, False, False]])

    def test_donor_alpha_is_only_near_glyphs_and_contains_both_lines(self):
        layer = dance_caption_layer()
        alpha = layer["alpha"]
        self.assertGreater(np.count_nonzero(layer["source_core"]), 1000)
        self.assertGreater(np.count_nonzero(alpha[:44]), 100)
        self.assertGreater(np.count_nonzero(alpha[44:]), 100)
        self.assertTrue(np.all(alpha[~layer["extent"]] == 0))
        self.assertTrue(np.all((alpha >= 0) & (alpha <= 1)))
        self.assertGreater(layer["foreground_bgr"][1], layer["foreground_bgr"][0])

    def test_generic_graphics_exclusion_encloses_all_alpha_pixels(self):
        x0, y0, x1, y1 = REGION
        extent = dance_caption_extent(843)[y0:y1, x0:x1] != 0
        self.assertTrue(np.all(extent[dance_caption_layer()["alpha"] > 0]))

    def test_registered_reference_cels_have_the_same_caption_phase(self):
        x0, y0, x1, y1 = REGION
        donor = self.source[y0:y1, x0:x1]
        layer = dance_caption_layer()
        stable = layer["source_core"] & (layer["alpha"] >= 0.96)
        names = ("src-0381-f0835.png", "src-0385-f0839.png", "src-0389-f0843.png",
                 "src-0394-f0848.png", "src-0398-f0852.png", "src-0402-f0856.png",
                 "src-0409-f0863.png", "src-0414-f0868.png", "src-0419-f0873.png",
                 "src-0426-f0880.png")
        for name in names:
            with self.subTest(source=name):
                source = cv2.imread(str(DONOR.parent / name), cv2.IMREAD_COLOR)
                crop = source[y0:y1, x0:x1]
                delta = np.max(cv2.absdiff(donor, crop), axis=2)[stable]
                self.assertLessEqual(np.percentile(delta, 95), 30)
                padded = cv2.copyMakeBorder(crop, 2, 2, 2, 2, cv2.BORDER_REFLECT)
                offsets = []
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        shifted = padded[2+dy:2+dy+crop.shape[0], 2+dx:2+dx+crop.shape[1]]
                        error = np.max(cv2.absdiff(donor, shifted), axis=2)[stable].mean()
                        offsets.append((float(error), dx, dy))
                self.assertEqual(min(offsets)[1:], (0, 0))

    def test_gap_between_lines_has_no_star_fragment(self):
        layer = dance_caption_layer()
        self.assertFalse(np.any(layer["alpha"][992-REGION[1]:1003-REGION[1]]))

    def test_transparent_edges_do_not_paste_purple_or_old_shoe(self):
        underlay = self.source.copy()
        x0, y0, x1, y1 = REGION
        boot = np.array([35, 48, 68], np.uint8)
        underlay[y0:y1, x0:x1] = boot
        before = underlay.copy()
        output, mask = restore_dance_captions(underlay, self.source, 843)
        layer = dance_caption_layer()
        alpha = layer["alpha"]
        expected = np.rint(alpha[..., None] * layer["foreground_bgr"]
                           + (1 - alpha[..., None]) * boot).astype(np.uint8)
        original = self.source[y0:y1, x0:x1]
        observed_core = layer["source_core"] & warm_glyph_core(original)
        expected[observed_core] = original[observed_core]
        painted = mask[y0:y1, x0:x1] != 0
        np.testing.assert_array_equal(output[y0:y1, x0:x1][painted], expected[painted])
        np.testing.assert_array_equal(output[mask == 0], before[mask == 0])
        # Reconstructed edges lie on cream-over-boot; observed glyph cores stay exact.
        edge = painted & (alpha > 0.04) & (alpha < 0.85)
        self.assertGreater(np.count_nonzero(edge), 10)
        self.assertTrue(np.all(output[y0:y1, x0:x1][edge, 0]
                               <= output[y0:y1, x0:x1][edge, 1]))

    def test_native_canvas_is_required(self):
        with self.assertRaises(ValueError):
            extract_dance_caption_layer(np.zeros((540, 960, 3), np.uint8))
        with self.assertRaises(ValueError):
            dance_caption_extent(831, (540, 960))


if __name__ == "__main__":
    unittest.main()
