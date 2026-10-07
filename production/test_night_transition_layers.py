"""Narrow scope and actual-cel tests for the registered night matte repair."""

from pathlib import Path
import unittest

import cv2
import numpy as np

from compose import read_image, subject_mask
from night_transition_layers import REGISTERED, is_registered, night_subject_mask, restore_night_transition

ROOT = Path(__file__).resolve().parent
QA = ROOT / "qa" / "fast-fullpv-dance-night-matte-2026-10-04"


class NightTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(2)
        cls.source = cv2.imread(str(QA / "f0907-source-native.png"))
        cls.generated = read_image(ROOT / "generated" / "fast-fullpv-dance-f0907-source-v2.png")
        if cls.source is None:
            raise RuntimeError("Run qa/check_night_transition.py to save actual source evidence")
        cls.name = "fast-fullpv-dance-f0907-source-v2.png"
        cls.old = subject_mask(cls.source)
        cls.generic_new = subject_mask(cls.generated)
        cls.new = night_subject_mask(cls.generated, 907, cls.name)
        cls.before = cls.source.copy()
        union = (cls.old != 0) | (cls.generic_new != 0)
        cls.before[union] = cls.generated[union]
        cls.fixed, cls.repair = restore_night_transition(
            cls.before, cls.source, cls.generated, cls.old, cls.generic_new, 907, cls.name)

    def test_exact_registration_and_exposure_scope(self):
        for name, (start, end) in REGISTERED.items():
            self.assertTrue(is_registered(start, name))
            self.assertTrue(is_registered(end - 1, name))
            self.assertFalse(is_registered(start - 1, name))
            self.assertFalse(is_registered(end, name))
        self.assertFalse(is_registered(907, "fast-fullpv-dance-f0907-v1.png"))
        self.assertFalse(is_registered(911, "candidate-030-clean.png"))

    def test_unregistered_pipeline_is_exact_noop(self):
        for frame, name in ((901, "candidate-029-clean.png"),
                            (911, "fast-fullpv-dance-f0909-v1.png"),
                            (907, "unknown.png"), (None, self.name)):
            output, mask = restore_night_transition(
                self.before, self.source, self.generated, self.old, self.generic_new, frame, name)
            self.assertIs(output, self.before)
            self.assertEqual(np.count_nonzero(mask), 0)
            self.assertIsNone(night_subject_mask(self.generated, frame, name))

    def test_actual_cyan_profile_and_hat_are_included(self):
        # Native coordinates cover the new feather, forehead, face and coat.
        for x, y in ((1330, 90), (1210, 370), (1290, 580), (1340, 630), (1230, 990)):
            self.assertEqual(self.new[y, x], 255, (x, y))
        self.assertEqual(self.new[300, 1600], 0)
        self.assertEqual(self.new[130, 1780], 0)

    def test_actual_old_candidate_blue_feather_is_not_sky(self):
        generated = read_image(ROOT / "generated" / "candidate-029-clean.png")
        matte = night_subject_mask(generated, 902, "candidate-029-clean.png")
        for x, y in ((1290, 45), (1370, 170), (1310, 530)):
            self.assertEqual(matte[y, x], 255, (x, y))

    def test_new_pixels_and_unedited_source_stars_are_exact(self):
        self.assertTrue(np.array_equal(self.fixed[self.new != 0], self.generated[self.new != 0]))
        self.assertTrue(np.array_equal(self.fixed[self.repair == 0], self.before[self.repair == 0]))
        self.assertTrue(np.array_equal(self.fixed[100:160, 1750:1810], self.source[100:160, 1750:1810]))
        self.assertTrue(np.array_equal(self.fixed[:, 1550:], self.source[:, 1550:]))

    def test_vacated_source_gradient_is_local_and_not_flat(self):
        old = night_subject_mask(self.source, 907, self.name)
        vacated = (cv2.dilate(old, np.ones((17, 17), np.uint8)) != 0) & (self.new == 0)
        self.assertGreater(np.count_nonzero(vacated), 10000)
        self.assertGreater(float(np.max(np.std(self.fixed[vacated].astype(float), axis=0))), 8)
        self.assertGreater(np.count_nonzero(np.any(self.fixed[vacated] != self.generated[vacated], axis=1)), 10000)


if __name__ == "__main__":
    unittest.main()
