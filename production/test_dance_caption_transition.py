"""Bounded source-registered tests across f897's actual lyric change."""

from pathlib import Path
from functools import lru_cache
import hashlib
import json
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import compose as compositor
from dance_caption_layers import (DONOR, NIGHT_DONOR, NIGHT_INTERVAL, NIGHT_REGION,
                                  REGION, SOURCE_INTERVAL, dance_caption_extent,
                                  dance_caption_layer, night_caption_layer,
                                  registered_caption, restore_dance_captions,
                                  warm_glyph_core)

ROOT = Path(__file__).resolve().parent


class DanceCaptionTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(2)
        cls.donor = cv2.imread(str(NIGHT_DONOR))

    def test_exact_lyric_change_boundary_has_different_registered_layers(self):
        self.assertEqual(SOURCE_INTERVAL, (831, 897))
        self.assertEqual(NIGHT_INTERVAL, (897, 911))
        self.assertIs(registered_caption(896)[1], dance_caption_layer())
        self.assertIs(registered_caption(897)[1], night_caption_layer())
        self.assertIs(registered_caption(910)[1], night_caption_layer())
        self.assertIsNone(registered_caption(911))
        self.assertFalse(np.any(dance_caption_extent(911)))

    def test_new_layer_has_both_lines_but_no_between_line_plate(self):
        layer = night_caption_layer()
        self.assertGreater(np.count_nonzero(layer["source_core"]), 1000)
        self.assertGreater(np.count_nonzero(layer["alpha"][:44]), 100)
        self.assertGreater(np.count_nonzero(layer["alpha"][44:]), 100)
        self.assertFalse(np.any(layer["alpha"][992-NIGHT_REGION[1]:1003-NIGHT_REGION[1]]))
        self.assertTrue(np.all(layer["alpha"][~layer["extent"]] == 0))

    def test_new_observed_glyph_cores_are_source_exact_without_support_expansion(self):
        x0, y0, x1, y1 = NIGHT_REGION
        layer = night_caption_layer()
        for frame, name in ((897, "src-0443-f0897.png"), (900, "src-0446-f0900.png"),
                            (902, "src-0448-f0902.png"), (903, "src-0449-f0903.png"),
                            (905, "src-0451-f0905.png"), (907, "src-0452-f0907.png"),
                            (908, "src-0453-f0908.png"), (909, "src-0454-f0909.png"),
                            (910, "src-0455-f0910.png")):
            with self.subTest(frame=frame):
                source = cv2.imread(str(ROOT / "source_refs" / name))
                underlay = source.copy()
                underlay[y0:y1, x0:x1] = (35, 48, 68)
                before = underlay.copy()
                output, mask = restore_dance_captions(underlay, source, frame)
                crop = source[y0:y1, x0:x1]
                observed = (layer["source_core"] & warm_glyph_core(crop)
                            & (np.max(np.abs(crop.astype(float) - layer["foreground_bgr"]), axis=2) <= 25))
                self.assertGreater(np.count_nonzero(observed), 1000)
                np.testing.assert_array_equal(output[y0:y1, x0:x1][observed], crop[observed])
                np.testing.assert_array_equal(output[mask == 0], before[mask == 0])
                permitted = (layer["alpha"] > 0) | layer["contrast_edge_support"]
                self.assertFalse(np.any((mask[y0:y1, x0:x1] != 0) & ~permitted))

    def test_contrast_edge_is_bounded_and_never_changes_unedited_source(self):
        layer = night_caption_layer()
        x0, y0, x1, y1 = NIGHT_REGION
        for frame in (897, 900, 903, 910):
            output, mask = restore_dance_captions(self.donor.copy(), self.donor, frame)
            np.testing.assert_array_equal(output, self.donor)
            self.assertFalse(np.any(mask))
        underlay = self.donor.copy()
        underlay[y0:y1, x0:x1] = (207, 223, 237)
        before = underlay.copy()
        character_mask = np.ones(self.donor.shape[:2], np.uint8) * 255
        character_mask[:, :900] = 0
        output, mask = restore_dance_captions(underlay, self.donor, 900, character_mask)
        changed = np.any(output[y0:y1, x0:x1] != before[y0:y1, x0:x1], axis=2)
        edge = changed & (layer["alpha"] == 0)
        self.assertGreater(np.count_nonzero(edge), 100)
        self.assertFalse(np.any(edge & ~layer["contrast_edge_support"]))
        self.assertFalse(np.any(edge & (character_mask[y0:y1, x0:x1] == 0)))
        np.testing.assert_array_equal(output[mask == 0], before[mask == 0])
        support = layer["alpha"] >= .1
        dilated = cv2.dilate(support.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0
        self.assertFalse(np.any(layer["contrast_edge_support"] & ~dilated))

    def test_no_contrast_edge_is_added_without_explicit_new_character_coverage(self):
        x0, y0, x1, y1 = NIGHT_REGION
        underlay = self.donor.copy()
        underlay[y0:y1, x0:x1] = (207, 223, 237)
        before = underlay.copy()
        output, mask = restore_dance_captions(underlay, self.donor, 900)
        layer = night_caption_layer()
        self.assertFalse(np.any((mask[y0:y1, x0:x1] != 0) & (layer["alpha"] == 0)))
        np.testing.assert_array_equal(output[mask == 0], before[mask == 0])

    def test_all_existing_v8_56_native_caption_outputs_are_unchanged(self):
        timeline = json.loads((ROOT / "timeline-opening-36s958-draft-v8.json").read_text(encoding="utf-8"))
        evidence = json.loads((ROOT / "qa/dance-caption-v8/evidence.json").read_text(encoding="utf-8"))
        rows = {row["frame"]: row for row in evidence["frames"]}
        exposures = timeline["output_exposures"]

        @lru_cache(maxsize=8)
        def load(cel):
            asset = timeline["assets"][cel]
            return compositor.read_image(ROOT / asset["source_reference"]), compositor.read_image(ROOT / asset["path"])

        cap = cv2.VideoCapture(timeline["source"])
        try:
            for _ in range(831):
                self.assertTrue(cap.grab())
            x0, y0, x1, y1 = REGION
            for frame in range(831, 887):
                with self.subTest(frame=frame):
                    ok, source = cap.read()
                    self.assertTrue(ok)
                    self.assertEqual(hashlib.sha256(source.tobytes()).hexdigest(), rows[frame]["decoded_source_sha256"])
                    exposure = next(e for e in exposures if e["start"] <= frame < e["end"])
                    asset = timeline["assets"][exposure["cel"]]
                    reference, generated = load(exposure["cel"])
                    output, _, _ = compositor.compose(source, reference, generated, exposure["source_matrix"],
                        asset["source_frame"], Path(asset["path"]).name, frame)
                    native_pair = cv2.imread(rows[frame]["native_caption_pair"])
                    expected = native_pair[:, x1-x0:]
                    np.testing.assert_array_equal(output[y0:y1, x0:x1], expected)
        finally:
            cap.release()

    def test_warm_foreground_skin_is_not_promoted_to_observed_glyphs(self):
        x0, y0, x1, y1 = NIGHT_REGION
        source = self.donor.copy()
        skin = np.array((180, 207, 230), np.uint8)
        source[y0:y1, x0:x1] = skin
        self.assertTrue(warm_glyph_core(skin.reshape(1, 1, 3))[0, 0])
        underlay = self.donor.copy()
        underlay[y0:y1, x0:x1] = (35, 48, 68)
        output, _ = restore_dance_captions(underlay, source, 903)
        layer = night_caption_layer()
        opaque = layer["alpha"] >= .96
        self.assertGreater(np.count_nonzero(opaque), 1000)
        self.assertFalse(np.any(np.all(output[y0:y1, x0:x1][opaque] == skin, axis=1)))

    def test_actual_existing_assets_cannot_restore_generic_old_face_or_boot(self):
        cases = ((891, "src-0437-f0891.png", "candidate-025-clean.png"),
                 (894, "src-0440-f0894.png", "candidate-026-clean.png"),
                 (897, "src-0443-f0897.png", "candidate-027-clean.png"),
                 (900, "src-0446-f0900.png", "candidate-028-clean.png"),
                 (902, "src-0448-f0902.png", "candidate-029-clean.png"),
                 (905, "src-0451-f0905.png", "candidate-030-clean.png"))
        for frame, source_name, asset_name in cases:
            with self.subTest(frame=frame):
                source = cv2.imread(str(ROOT / "source_refs" / source_name))
                generated = compositor.read_image(ROOT / "generated" / asset_name)
                arguments = dict(asset_source_frame=frame, asset_name=asset_name, current_frame=frame)
                forced = np.ones(source.shape[:2], np.uint8) * 255
                with patch.object(compositor, "graphics_mask", return_value=forced):
                    output, _, masks = compositor.compose(source, source, generated, **arguments)
                with patch.object(compositor, "graphics_mask", return_value=np.zeros_like(forced)):
                    expected, _, expected_masks = compositor.compose(source, source, generated, **arguments)
                np.testing.assert_array_equal(output, expected)
                np.testing.assert_array_equal(masks, expected_masks)

    def test_existing_v8_four_new_cel_composites_do_not_change(self):
        cases = ((863, "src-0409-f0863.png", "root-continuation-f0863-hair-v2.png"),
                 (868, "src-0414-f0868.png", "root-continuation-f0868-v1.png"),
                 (873, "src-0419-f0873.png", "root-continuation-f0873-v1.png"),
                 (880, "src-0426-f0880.png", "root-continuation-f0880-v1.png"))
        for frame, source_name, asset_name in cases:
            with self.subTest(frame=frame):
                source = cv2.imread(str(ROOT / "source_refs" / source_name))
                generated = compositor.read_image(ROOT / "generated" / asset_name)
                output, _, _ = compositor.compose(source, source, generated,
                    asset_source_frame=frame, asset_name=asset_name, current_frame=frame)
                baseline = cv2.imread(str(ROOT / "qa/dance-caption-v8" / f"f{frame:04d}-full-composite.png"))
                np.testing.assert_array_equal(output, baseline)


if __name__ == "__main__":
    unittest.main()
