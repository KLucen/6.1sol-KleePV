"""Ownership regressions observed in the f1008..1042 native audit."""

from pathlib import Path
import sys
import unittest

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import star_gestures_layers as layers


class StarGesturesLayersTests(unittest.TestCase):
    def test_exact_exposures_and_repaired_backview_only(self):
        spans = sorted(layers.REGISTERED.values())
        self.assertEqual(spans[0][0], 1008)
        self.assertEqual(spans[-1][1], 1043)
        self.assertTrue(all(a[1] == b[0] for a, b in zip(spans, spans[1:])))
        self.assertFalse(layers.is_registered(1017, "candidate-035.png"))
        self.assertTrue(layers.is_registered(1018, "star-gestures-f1017-rear-hair-v2.png"))
        self.assertFalse(layers.is_registered(1019, "star-gestures-f1017-rear-hair-v2.png"))
        self.assertFalse(layers.is_registered(1043, "star-gestures-f1038-fast-v1.png"))
        self.assertFalse(layers.is_registered(1009, "candidate-033-clean.png"))

    def test_out_of_scope_is_no_op(self):
        output = np.full((1080, 1920, 3), 17, np.uint8)
        source = np.full_like(output, 63)
        result, mask = layers.restore_star_captions(output, source, 1043, "star-gestures-f1038-fast-v1.png")
        self.assertIs(result, output)
        self.assertFalse(np.any(mask))
        self.assertTrue(np.all(result == 17))

    def test_old_blue_hair_is_not_a_sky_donor(self):
        source = cv2.imread(str(ROOT / "source_refs/src-0541-f1008.png"))
        matte, sky = layers._matte_and_sky(source, 1008, source=True)
        for x, y in ((600, 500), (700, 900), (650, 500), (450, 850), (800, 50)):
            with self.subTest(point=(x, y)):
                self.assertEqual(matte[y, x], 255)
                self.assertFalse(sky[y, x])

    def test_rear_klee_hat_and_blue_face_are_not_cropped(self):
        generated = cv2.imread(str(ROOT / "generated/candidate-033-clean.png"))
        generated = cv2.resize(generated, (1920, 1080), interpolation=cv2.INTER_LANCZOS4)
        matte = layers.star_subject_mask(generated, 1008, "candidate-033-clean.png")
        for x, y in ((575, 350), (850, 450), (850, 600)):
            with self.subTest(point=(x, y)):
                self.assertEqual(matte[y, x], 255)

    def test_phase_masks_do_not_expand_with_warm_skin(self):
        self.assertEqual([layers._phase(f) for f in (1008, 1011, 1012, 1036, 1037, 1042)], [0, 0, 1, 1, 2, 2])
        self.assertIsNone(layers._phase(1043))
        source = cv2.imread(str(ROOT / "source_refs/src-0569-f1037.png"))
        output = np.full_like(source, (166, 182, 228))
        before = output.copy()
        result, mask = layers.restore_star_captions(output, source, 1037, "star-gestures-f1037-fast-v1.png", np.full(source.shape[:2], 255, np.uint8))
        declared = layers.star_caption_extent(1037) != 0
        self.assertFalse(np.any(mask[~declared]))
        np.testing.assert_array_equal(result[~declared], before[~declared])
        layer = layers.caption_layer(2)
        x0, y0, x1, y1 = layer["region"]
        np.testing.assert_array_equal(result[y0:y1, x0:x1][layer["core"]], source[y0:y1, x0:x1][layer["core"]])
        # The observed pre-word cuff pixel is not a Japanese glyph or a core.
        self.assertFalse(layer["core"][965-y0, 857-x0])

    def test_adjacent_star_is_not_a_feather_or_character(self):
        for frame in (1033, 1037, 1038):
            name = f"star-gestures-f{frame}-fast-v1.png"
            source = cv2.imread(str(next((ROOT / "source_refs").glob(f"*-f{frame}.png"))))
            generated = cv2.imread(str(ROOT / "generated" / name))
            generated = cv2.resize(generated, (1920, 1080), interpolation=cv2.INTER_LANCZOS4)
            old = layers.star_subject_mask(source, frame, name, source=True)
            new = layers.star_subject_mask(generated, frame, name)
            output, _ = layers.restore_star_gestures(source.copy(), source, generated, old, new, frame, name)
            for x, y in ((1150, 220), (1120, 200)):
                with self.subTest(frame=frame, point=(x, y)):
                    self.assertEqual(old[y, x], 0)
                    self.assertEqual(new[y, x], 0)
                    np.testing.assert_array_equal(output[y, x], source[y, x])
            if frame in (1033, 1037):
                self.assertEqual(new[160, 1030], 255)


if __name__ == "__main__":
    unittest.main()
