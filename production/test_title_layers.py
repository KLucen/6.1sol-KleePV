"""Technical layer regressions; these checks do not grant artistic acceptance."""

import unittest

import numpy as np

from compose import compose, read_image
from title_layers import ROOT, checked_layers, compose_registered_title, registry


class TitleLayerTests(unittest.TestCase):
    def test_registered_title_preserves_source_outside_reviewed_union(self):
        for name, registration in registry()["assets"].items():
            frame = registration["source_frame"]
            from json import loads
            source_map = loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
            cel = next(c for c in source_map["cels"] if c["frame"] == frame)
            source, generated = read_image(ROOT / cel["reference"]), read_image(ROOT / "generated" / name)
            _, old, new, plate, known = checked_layers(name)
            output, _, _ = compose(source, source, generated, asset_source_frame=frame,
                                   asset_name=name, current_frame=frame)
            outside = (old | new) == 0
            self.assertTrue(np.array_equal(output[outside], source[outside]), name)
            self.assertTrue(np.array_equal(output[new != 0], generated[new != 0]), name)
            vacated = (old != 0) & (new == 0)
            self.assertTrue(np.all(known[vacated] != 0), name)
            self.assertTrue(np.array_equal(output[vacated], plate[vacated]), name)

    def test_title_registry_rejects_wrong_source_frame_and_camera(self):
        name = next(iter(registry()["assets"]))
        row, _, _, _, _ = checked_layers(name)
        dummy = np.zeros((1080, 1920, 3), np.uint8)
        with self.assertRaisesRegex(ValueError, "frame or camera"):
            compose_registered_title(dummy, dummy, row["source_frame"]+1, name, [[1, 0, 0], [0, 1, 0]])
        with self.assertRaisesRegex(ValueError, "frame or camera"):
            compose_registered_title(dummy, dummy, row["source_frame"], name, [[1, 0, 1], [0, 1, 0]])

    def test_unregistered_asset_does_not_enable_title_layers(self):
        dummy = np.zeros((1080, 1920, 3), np.uint8)
        self.assertIsNone(compose_registered_title(dummy, dummy, 1314, "unknown.png", [[1, 0, 0], [0, 1, 0]]))

    def test_reconstructed_pixels_have_explicit_non_source_provenance(self):
        import cv2
        for row in registry()["assets"].values():
            reconstructed = cv2.imread(str(ROOT / row["reconstructed"]["path"]), 0) != 0
            provenance = cv2.imread(str(ROOT / row["provenance"]["path"]), cv2.IMREAD_UNCHANGED)
            known = cv2.imread(str(ROOT / row["background_known"]["path"]), 0)
            self.assertEqual(int(np.count_nonzero(reconstructed)), row["reconstructed_visible_pixels"])
            self.assertTrue(np.all(provenance[reconstructed] == 65534))
            self.assertTrue(np.all(known[reconstructed] == 128))
            self.assertFalse(row["accepted"])

    def test_flat_spatial_repairs_use_exact_registered_source_pixels(self):
        import cv2
        import json
        source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
        refs = {c["frame"]: c["reference"] for c in source_map["cels"]}
        for name, row in registry()["assets"].items():
            provenance = cv2.imread(str(ROOT / row["provenance"]["path"]), cv2.IMREAD_UNCHANGED)
            donor_x = cv2.imread(str(ROOT / row["spatial_donor_x"]["path"]), cv2.IMREAD_UNCHANGED)
            y, x = np.nonzero(provenance == 65533)
            self.assertEqual(len(y), row["spatial_donor_visible_pixels"])
            _, _, _, plate, known = checked_layers(name)
            source = read_image(ROOT / refs[row["source_frame"]])
            self.assertTrue(np.array_equal(plate[y, x], source[y, donor_x[y, x]]), name)
            self.assertTrue(np.all(known[y, x] == 64))
            if len(y):
                self.assertNotEqual(row["phase"], "title")

    def test_original_copy_alias_switches_plain_to_title_background(self):
        import json
        source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
        refs = {c["frame"]: c["reference"] for c in source_map["cels"]}
        name = next(n for n, row in registry()["assets"].items() if row["source_frame"] == 1296)
        plain, _, _, plain_plate, _ = checked_layers(name, "plain")
        title, old, new, title_plate, known = checked_layers(name, "title")
        self.assertEqual((plain["background_source_frame"], title["background_source_frame"]), (1296, 1299))
        self.assertTrue(all(1299 <= f < 1403 for f in title["donor_frames"]))
        self.assertFalse(np.array_equal(plain_plate, title_plate))
        source, generated = read_image(ROOT/refs[1299]), read_image(ROOT/"generated"/name)
        output, _, _ = compose(source, source, generated, asset_source_frame=1296, asset_name=name, current_frame=1299)
        vacated = (old != 0) & (new == 0)
        self.assertTrue(np.all(known[vacated] != 0))
        self.assertTrue(np.array_equal(output[vacated], title_plate[vacated]))
        self.assertTrue(np.array_equal(output[(old|new) == 0], source[(old|new) == 0]))
        with self.assertRaisesRegex(ValueError, "No registered credits"):
            checked_layers(name, "credits")


if __name__ == "__main__":
    unittest.main()
