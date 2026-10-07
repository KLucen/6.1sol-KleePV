"""Bounded tests of the actual dance-lyric integration in compose."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import compose as compositor
from dance_caption_layers import REGION, dance_caption_layer

ROOT = Path(__file__).resolve().parent
REFERENCES = {843: "src-0389-f0843.png", 848: "src-0394-f0848.png",
              856: "src-0402-f0856.png", 863: "src-0409-f0863.png",
              868: "src-0414-f0868.png", 873: "src-0419-f0873.png",
              880: "src-0426-f0880.png"}


def selected_cases():
    selections = json.loads((ROOT/"asset_selections.json").read_text(encoding="utf-8"))
    rows = {row["source_frame"]: row for row in selections["selections"]}
    cases = []
    for frame, reference in REFERENCES.items():
        row = rows[frame]
        cases.append((frame, compositor.read_image(ROOT/"source_refs"/reference),
                      compositor.read_image(ROOT/row["path"]), Path(row["path"]).name))
    return cases


def disabled_dance(output, source, frame):
    return output, np.zeros(source.shape[:2], np.uint8)


class DanceCaptionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(2)
        cls.cases = selected_cases()

    def call_compose(self, case, frame=None):
        source_frame, source, generated, name = case
        return compositor.compose(source, source, generated, asset_source_frame=source_frame,
                                  asset_name=name, current_frame=source_frame if frame is None else frame)

    def test_actual_shared_compositor_exposes_integrated_layer(self):
        self.assertTrue(callable(compositor.restore_dance_captions))

    def test_outside_phase_equals_compositor_with_layer_disabled(self):
        case = self.cases[0]
        for frame in (830, 911, 920):
            with self.subTest(frame=frame):
                actual, _, actual_masks = self.call_compose(case, frame)
                with patch.object(compositor, "restore_dance_captions", side_effect=disabled_dance):
                    baseline, _, baseline_masks = self.call_compose(case, frame)
                np.testing.assert_array_equal(actual, baseline)
                np.testing.assert_array_equal(actual_masks, baseline_masks)

    def test_no_current_source_graphics_can_reintroduce_old_boot_in_bottom_band(self):
        for case in self.cases:
            with self.subTest(frame=case[0]):
                forced = np.zeros(case[1].shape[:2], np.uint8)
                forced[910:] = 255
                with patch.object(compositor, "graphics_mask", return_value=forced):
                    actual, _, masks = self.call_compose(case)
                with patch.object(compositor, "graphics_mask", return_value=np.zeros_like(forced)):
                    baseline, _, baseline_masks = self.call_compose(case)
                np.testing.assert_array_equal(actual, baseline)
                np.testing.assert_array_equal(masks, baseline_masks)

    def test_every_actual_changed_pixel_has_a_declared_mask(self):
        for case in self.cases:
            with self.subTest(frame=case[0]):
                output, _, masks = self.call_compose(case)
                changed = np.any(output != case[1], axis=2)
                undeclared = changed & np.all(masks == 0, axis=2)
                self.assertEqual(np.count_nonzero(undeclared), 0)

    def test_false_left_caption_candidates_cannot_restore_old_coat(self):
        for case in self.cases:
            with self.subTest(frame=case[0]):
                forced = np.zeros(case[1].shape[:2], np.uint8)
                forced[350:840, :860] = 255
                with patch.object(compositor, "graphics_mask", return_value=forced):
                    actual, _, actual_masks = self.call_compose(case)
                with patch.object(compositor, "graphics_mask", return_value=np.zeros_like(forced)):
                    expected, _, expected_masks = self.call_compose(case)
                np.testing.assert_array_equal(actual, expected)
                np.testing.assert_array_equal(actual_masks, expected_masks)

    def test_dance_layer_changes_only_alpha_support_and_declares_its_changes(self):
        x0, y0, x1, y1 = REGION
        support = np.zeros(self.cases[0][1].shape[:2], bool)
        support[y0:y1, x0:x1] = dance_caption_layer()["alpha"] > 0
        for case in self.cases:
            with self.subTest(frame=case[0]):
                actual, _, masks = self.call_compose(case)
                with patch.object(compositor, "restore_dance_captions", side_effect=disabled_dance):
                    before, _, _ = self.call_compose(case)
                changed = np.any(actual != before, axis=2)
                self.assertGreater(np.count_nonzero(changed), 100)
                self.assertEqual(np.count_nonzero(changed & ~support), 0)
                self.assertEqual(np.count_nonzero(changed & np.all(masks == 0, axis=2)), 0)


if __name__ == "__main__":
    unittest.main()
