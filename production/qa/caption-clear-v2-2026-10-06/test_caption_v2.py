import unittest
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import star_extended_captions as captions


class CaptionV2Tests(unittest.TestCase):
    def test_reconstruction_changes_only_cn_rows(self):
        with np.load(HERE / "long-combined-before-v2.npz") as prior:
            current = captions._clear_long_layer()
            for key in ("alpha", "core", "extent", "ink_rgb"):
                self.assertTrue(np.array_equal(current[key][:48], prior[key][:48]), key)

    def test_chinese_donor_is_not_a_current_pixel_oracle(self):
        self.assertFalse(captions._clear_long_layer()["core"][48:].any())

    def test_boundary_dispatch_is_exact(self):
        class Checkpoint:
            def caption_layer(self, frame):
                return ("checkpoint", frame)

        checkpoint = Checkpoint()
        with patch.object(captions, "_clear_long_layer", return_value="long"), patch.object(
                captions, "_clear_short_layer", return_value="short"):
            self.assertEqual(captions.caption_layer(checkpoint, 1042), ("checkpoint", 1042))
            self.assertEqual(captions.caption_layer(checkpoint, 1043), "long")
            self.assertEqual(captions.caption_layer(checkpoint, 1143), "long")
            self.assertEqual(captions.caption_layer(checkpoint, 1144), "short")
            self.assertEqual(captions.caption_layer(checkpoint, 1161), "short")
            self.assertEqual(captions.caption_layer(checkpoint, 1162), ("checkpoint", 1162))

    def test_clear_cn_ink_is_not_overwritten_by_original_cuff(self):
        shape = (10, 12)
        source = np.full((*shape, 3), 245, np.uint8)
        generated = np.full((*shape, 3), 50, np.uint8)
        layer = {"region": np.array([0, 0, 12, 10]), "alpha": np.ones(shape, np.float32),
                 "core": np.zeros(shape, bool), "ink_rgb": np.full((*shape, 3), 200, np.float32)}

        class Checkpoint:
            def _matte_and_sky(self, image, frame, source=False):
                return np.full(shape, 255, np.uint8), np.zeros(shape, bool)

            def _warm_support(self, image):
                return np.zeros(shape, bool)

        with patch.object(captions, "_clear_long_layer", return_value=layer), patch.object(
                captions, "_source_gradient", return_value=generated):
            output, masks = captions.compose_with_clear_captions(Checkpoint(), source, generated, 1043)
        self.assertTrue(np.all(output == 200))
        self.assertTrue(masks["caption"].all())


if __name__ == "__main__":
    unittest.main()
