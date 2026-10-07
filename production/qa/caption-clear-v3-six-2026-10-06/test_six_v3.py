import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import star_gestures_layers as current


class SixV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("_test_old_star_before_six", HERE / "star_gestures_layers-before-six-v3.py")
        cls.before = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.before)
        cls.before.ROOT = ROOT

    def test_earlier_phases_are_exact(self):
        for phase in (0, 1):
            before, after = self.before.caption_layer(phase), current.caption_layer(phase)
            self.assertEqual(before["region"], after["region"])
            for key in ("core", "extent", "alpha", "foreground", "contrast_ring"):
                self.assertTrue(np.array_equal(before[key], after[key]), (phase, key))

    def test_old_phase2_japanese_is_exact(self):
        with np.load(HERE / "old-phase2-layer-before-six-v3.npz") as before:
            after = current.caption_layer(2)
            for key in ("core", "extent", "alpha", "contrast_ring", "ink_rgb"):
                self.assertTrue(np.array_equal(before[key][:48], after[key][:48]), key)

    def test_cn_is_the_registered_complete_original_donor(self):
        after = current.caption_layer(2)
        with np.load(ROOT / "qa/caption-clear-v2-2026-10-06/long-f3402-cn-clear-real-caption-v2.npz") as donor:
            self.assertTrue(np.array_equal(after["region"], donor["region"]))
            for key in ("core", "extent", "alpha", "contrast_ring", "ink_rgb"):
                self.assertTrue(np.array_equal(after[key][48:], donor[key][48:]), key)
        self.assertFalse(after["core"][48:].any())

    def test_registered_phase_exposure_boundaries_are_unchanged(self):
        self.assertEqual(current.REGISTERED, self.before.REGISTERED)
        self.assertEqual(current.CAPTION_PHASES, self.before.CAPTION_PHASES)
        self.assertEqual([current._phase(frame) for frame in range(1037, 1043)], [2] * 6)
        self.assertEqual(current._phase(1036), 1)
        self.assertIsNone(current._phase(1043))


if __name__ == "__main__":
    unittest.main()
