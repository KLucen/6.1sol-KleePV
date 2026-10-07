"""Regression checks for source captions and scoped opening restoration."""

import unittest

import cv2
import numpy as np

from compose import ROOT, compose, graphics_mask, pale_graphics, read_image, subject_mask, yellow_graphics


class CaptionCompositeTests(unittest.TestCase):
    def test_opening_left_caption_region_is_exact_source(self):
        source = read_image(ROOT / "source_refs/src-0059-f0190.png")
        generated = read_image(ROOT / "generated/fine-f0190.png")
        output, _, _ = compose(source, source, generated, asset_source_frame=190,
                               asset_name="fine-f0190.png", current_frame=190)
        self.assertTrue(np.array_equal(output[350:840, :800], source[350:840, :800]))

    def test_caption_rules_stop_at_audited_opening_end(self):
        source = read_image(ROOT / "source_refs/src-0059-f0190.png")
        generated = read_image(ROOT / "generated/fine-f0190.png")
        baseline, _, _ = compose(source, source, generated)
        later, _, _ = compose(source, source, generated, asset_source_frame=190,
                             asset_name="fine-f0190.png", current_frame=666)
        self.assertTrue(np.array_equal(baseline, later))

    def test_later_left_caption_is_source_exact(self):
        source = read_image(ROOT / "source_refs/src-0074-f0250.png")
        generated = read_image(ROOT / "generated/fine-f0250.png")
        output, _, _ = compose(source, source, generated, asset_source_frame=250,
                               asset_name="fine-f0250.png", current_frame=250)
        pale = pale_graphics(source)[495:635, 180:780] != 0
        self.assertTrue(np.array_equal(output[495:635, 180:780][pale],
                                       source[495:635, 180:780][pale]))
        baseline, _, _ = compose(source, source, generated)
        self.assertTrue(np.array_equal(output[700:840, 650:800],
                                       baseline[700:840, 650:800]))

    def test_face_caption_repairs_only_damaged_chinese_line(self):
        source = read_image(ROOT / "source_refs/src-0084-f0294.png")
        generated = read_image(ROOT / "generated/fine-f0294.png")
        output, _, _ = compose(source, source, generated, asset_source_frame=294,
                               asset_name="fine-f0294.png", current_frame=300)
        pale = pale_graphics(source)[290:540, 180:590] != 0
        self.assertTrue(np.array_equal(output[290:540, 180:590][pale],
                                       source[290:540, 180:590][pale]))
        baseline, _, _ = compose(source, source, generated)
        self.assertTrue(np.array_equal(output[637:760, 424:660],
                                       baseline[637:760, 424:660]))

    def test_undamaged_later_face_caption_does_not_restore_old_hair(self):
        source = read_image(ROOT / "source_refs/src-0084-f0294.png")
        generated = read_image(ROOT / "generated/fine-f0294.png")
        baseline, _, _ = compose(source, source, generated)
        later, _, _ = compose(source, source, generated, asset_source_frame=294,
                              asset_name="fine-f0294.png", current_frame=394)
        self.assertTrue(np.array_equal(baseline, later))

    def test_zoomed_chinese_line_keeps_warm_cream_strokes(self):
        source = read_image(ROOT / "source_refs/src-0082-f0290.png")
        generated = read_image(ROOT / "generated/candidate-005.png")
        output, _, _ = compose(source, source, generated, asset_source_frame=287,
                               asset_name="candidate-005.png", current_frame=290)
        patch = source[234:243, 488:509]
        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        warm_cream = (hsv[:, :, 0] >= 10) & (hsv[:, :, 0] < 17) & (hsv[:, :, 1] < 43)
        self.assertGreater(np.count_nonzero(warm_cream), 0)
        self.assertTrue(np.array_equal(output[234:243, 488:509][warm_cream], patch[warm_cream]))

    def test_bottom_lyric_is_source_exact_after_wide_shot_begins(self):
        source = read_image(ROOT / "source_refs/src-0168-f0499.png")
        generated = read_image(ROOT / "generated/fine-f0499.png")
        output, _, _ = compose(source, source, generated, asset_source_frame=499,
                               asset_name="fine-f0499.png", current_frame=500)
        self.assertTrue(np.array_equal(output[925:1060, 700:1230],
                                       source[925:1060, 700:1230]))

    def test_zoomed_bubble_erases_added_chinese_glyphs(self):
        source = read_image(ROOT / "source_refs/src-0082-f0290.png")
        generated = read_image(ROOT / "generated/candidate-005.png")
        output, _, _ = compose(source, source, generated, asset_source_frame=287,
                               asset_name="candidate-005.png", current_frame=290)
        self.assertTrue(np.array_equal(output[390:550, 220:560],
                                       source[390:550, 220:560]))
        baseline, _, _ = compose(source, source, generated)
        self.assertGreater(np.count_nonzero(np.any(baseline[475:530, 350:510] !=
                                                   source[475:530, 350:510], axis=2)), 0)
        self.assertTrue(np.array_equal(output[637:760, 610:810],
                                       baseline[637:760, 610:810]))

    def test_right_lyric_stays_in_front_of_new_legs(self):
        source = read_image(ROOT / "source_refs/src-0281-f0661.png")
        generated = read_image(ROOT / "generated/fine-f0661.png")
        output, _, _ = compose(source, source, generated, asset_source_frame=661,
                               asset_name="fine-f0661.png", current_frame=665)
        baseline, _, _ = compose(source, source, generated)
        self.assertTrue(np.array_equal(output[514:538, 1214:1229],
                                       baseline[514:538, 1214:1229]))
        source_crop = source[495:670, 1210:1830]
        background_color = np.median(source_crop.reshape(-1, 3), axis=0)
        background = np.linalg.norm(source_crop.astype(float)-background_color, axis=2) < 3
        self.assertTrue(np.array_equal(output[495:670, 1210:1830][background],
                                       baseline[495:670, 1210:1830][background]))
        self.assertGreater(np.count_nonzero(np.any(output[495:670, 1210:1830] !=
                                                   source[495:670, 1210:1830], axis=2)), 0)

    def test_compact_prone_repair_keeps_lyric_clear_and_removes_old_hat_highlights(self):
        source = read_image(ROOT / "source_refs/src-0281-f0661.png")
        generated = read_image(ROOT / "generated/fine-f0661-source-extent-v2.png")
        output, _, _ = compose(source, source, generated, asset_source_frame=661,
                               asset_name="fine-f0661-source-extent-v2.png", current_frame=661)
        old_highlights = (graphics_mask(source) != 0) & (subject_mask(generated) != 0)
        self.assertGreater(np.count_nonzero(old_highlights), 0)
        self.assertTrue(np.array_equal(output[old_highlights], generated[old_highlights]))
        source_field = source[495:670, 1255:1830]
        generated_field = generated[495:670, 1255:1830]
        hsv = cv2.cvtColor(generated_field, cv2.COLOR_BGR2HSV)
        # The generated caption itself is warm cream; only dark warm subject
        # colors here would indicate a boot/coat crossing this source text field.
        blocked = (hsv[:, :, 0] < 80) & (hsv[:, :, 1] > 60) & (hsv[:, :, 2] < 205)
        self.assertEqual(np.count_nonzero(blocked), 0)
        pale = pale_graphics(source_field) != 0
        self.assertTrue(np.array_equal(output[495:670, 1255:1830][pale], source_field[pale]))

    def test_subject_mask_optimization_preserves_previous_result(self):
        for path in ("source_refs/src-0059-f0190.png", "generated/fine-f0190.png"):
            image = read_image(ROOT / path)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            sky = ((h >= 109) & (h <= 145) & (s > 70) & (v > 212)) | ((h >= 84) & (h <= 147) & (s > 160))
            graphics = pale_graphics(image) | yellow_graphics(image)
            seed = ((~sky) & (graphics == 0)).astype(np.uint8)
            connected = cv2.morphologyEx(seed, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
            count, labels, stats, _ = cv2.connectedComponentsWithStats(connected, 8)
            selected = np.zeros_like(seed)
            for i in range(1, count):
                x, y, w, height, area = stats[i]
                region = labels == i
                warm = (h < 22) & (s > 35) & (v > 60)
                cool = (h >= 80) & (h <= 115) & (s >= 25) & (s < 155) & (v > 85)
                cores = np.count_nonzero(region & (warm | cool))
                if area >= 1000 and w >= 18 and height >= 18 and cores > 180:
                    selected[labels == i] = 255
            contours, _ = cv2.findContours(selected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            filled = np.zeros_like(seed)
            cv2.drawContours(filled, contours, -1, 255, cv2.FILLED)
            expected = cv2.dilate(filled, np.ones((5, 5), np.uint8))
            self.assertTrue(np.array_equal(subject_mask(image), expected), path)


if __name__ == "__main__":
    unittest.main()
