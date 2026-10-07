"""Actual 900/901 ROI tests and frozen 902..910 pixel-hash regression."""

import hashlib
import json
from pathlib import Path
import unittest

import cv2
import numpy as np

from compose import compose, read_image, subject_mask
from night_transition_layers import BACKVIEW_ASSET, BACKVIEW_ROI, is_registered, night_subject_mask, restore_night_transition

ROOT = Path(__file__).resolve().parent
QA = ROOT / "qa" / "fast-fullpv-dance-backview-fragment-2026-10-04" / "fixed-v2"
NIGHT_QA = ROOT / "qa" / "fast-fullpv-dance-night-matte-2026-10-04"


class BackviewTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(2)
        cls.generated = read_image(ROOT / "generated" / BACKVIEW_ASSET)
        cls.generic_new = subject_mask(cls.generated)
        cls.area = np.zeros((1080, 1920), bool)
        x0, y0, x1, y1 = BACKVIEW_ROI
        cls.area[y0:y1, x0:x1] = True
        cls.frames = {}
        for frame in (900, 901):
            source = cv2.imread(str(QA / f"f{frame:04d}-source-native.png"))
            before = cv2.imread(str(QA / f"f{frame:04d}-composite-native.png"))
            old = subject_mask(source)
            new = night_subject_mask(cls.generated, frame, BACKVIEW_ASSET, cls.generic_new)
            merged_old = night_subject_mask(source, frame, BACKVIEW_ASSET, old)
            fixed, repair = restore_night_transition(
                before, source, cls.generated, merged_old, new, frame, BACKVIEW_ASSET)
            cls.frames[frame] = (source, before, old, merged_old, new, fixed, repair)
            cv2.imwrite(str(QA / f"f{frame:04d}-scoped-layer-before-captions-native.png"), fixed)
            cv2.imwrite(str(QA / f"f{frame:04d}-scoped-layer-repair-mask.png"), repair)

    def test_registration_is_only_new_asset_two_frames(self):
        for frame in (900, 901):
            self.assertTrue(is_registered(frame, BACKVIEW_ASSET))
        for frame in (899, 902):
            self.assertFalse(is_registered(frame, BACKVIEW_ASSET))
        self.assertFalse(is_registered(900, "candidate-028-clean.png"))

    def test_both_mattes_preserve_generic_outside_checked_roi(self):
        for source, before, old, merged_old, new, fixed, repair in self.frames.values():
            self.assertTrue(np.array_equal(merged_old[~self.area], old[~self.area]))
            self.assertTrue(np.array_equal(new[~self.area], self.generic_new[~self.area]))
            self.assertTrue(np.array_equal(fixed[~self.area], before[~self.area]))
            self.assertEqual(np.count_nonzero(repair[~self.area]), 0)

    def test_actual_new_cool_beret_arc_and_front_red_beret_are_exact(self):
        h, s, v = cv2.split(cv2.cvtColor(self.generated, cv2.COLOR_BGR2HSV))
        cool = self.area & (h >= 135) & (s > 50) & (v < 215)
        front = self.area & (h < 20) & (s > 120) & (v > 80)
        self.assertGreater(np.count_nonzero(cool), 1000)
        self.assertGreater(np.count_nonzero(front), 10000)
        for source, before, old, merged_old, new, fixed, repair in self.frames.values():
            self.assertTrue(np.all(new[cool | front] == 255))
            self.assertTrue(np.array_equal(fixed[cool | front], self.generated[cool | front]))

    def test_measured_green_fringe_pixels_no_longer_equal_old_source(self):
        for source, before, old, merged_old, new, fixed, repair in self.frames.values():
            for x, y in ((1226, 4), (1275, 19), (1305, 45), (1350, 80), (1414, 168), (1467, 252)):
                self.assertFalse(np.array_equal(fixed[y, x], source[y, x]), (x, y))

    def test_vacated_ear_background_not_generated_patch_or_flat_fill(self):
        for source, before, old, merged_old, new, fixed, repair in self.frames.values():
            target = self.area & (repair != 0) & (new == 0)
            self.assertGreater(np.count_nonzero(target), 4000)
            self.assertGreater(np.count_nonzero(np.any(fixed[target] != self.generated[target], axis=1)), 4000)
            self.assertGreater(np.max(np.std(fixed[target].astype(float), axis=0)), 2)
            self.assertTrue(np.array_equal(fixed[100:160, 1750:1810], source[100:160, 1750:1810]))

    def test_prior_nine_actual_composites_are_byte_identical(self):
        evidence = json.loads((NIGHT_QA / "actual-native-evidence-902-903-904-905-906-907-908-909-910.json").read_text())
        timeline = json.loads((ROOT / "timeline-dance-812-911-fast-draft-v11.json").read_text())
        for record in evidence["records"]:
            frame = record["frame"]
            source = cv2.imread(str(NIGHT_QA / f"f{frame:04d}-source-native.png"))
            exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
            asset = timeline["assets"][exposure["cel"]]
            generated = read_image(ROOT / asset["path"])
            output, _, _ = compose(source, source, generated, exposure.get("source_matrix"),
                                   asset["source_frame"], Path(asset["path"]).name, frame)
            self.assertEqual(hashlib.sha256(output.tobytes()).hexdigest(), record["fixed_bgr_sha256"], frame)


if __name__ == "__main__":
    unittest.main()
