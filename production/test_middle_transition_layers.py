"""Guard the exact file/exposure registration and observed middle-face repairs."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import middle_transition_layers as layer

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / "qa" / "middle-transition-layers-private-2026-10-06"
IDENTITY = [[1, 0, 0], [0, 1, 0]]


class RegistrationTests(unittest.TestCase):
    def test_outside_interval_never_loads_checkpoint(self):
        with patch.object(layer, "_checkpoint", side_effect=AssertionError("must remain scoped")):
            for frame in (None, 0, 2120, 2145, 3657):
                self.assertIsNone(layer.compose_registered_middle_transition(None, None, frame, "anything.png", IDENTITY))

    def test_unknown_filename_does_not_match(self):
        self.assertIsNone(layer.compose_registered_middle_transition(None, None, 2135, "unreviewed.png", IDENTITY))

    def test_registered_file_outside_its_exposure_does_not_match(self):
        self.assertIsNone(layer.compose_registered_middle_transition(None, None, 2134, "middle-next-f2135-oct6-v1.png", IDENTITY))

    def test_exact_registration_boundaries(self):
        private = layer._checkpoint()
        for name, (start, end) in private.REGISTERED.items():
            self.assertTrue(private.is_registered(start, name))
            self.assertTrue(private.is_registered(end-1, name))
            self.assertFalse(private.is_registered(start-1, name))
            self.assertFalse(private.is_registered(end, name))

    def test_even_tiny_transform_drift_rejected(self):
        transform = [[1, 0, .00001], [0, 1, 0]]
        with self.assertRaises(ValueError):
            layer.compose_registered_middle_transition(None, None, 2135, "middle-next-f2135-oct6-v1.png", transform)

    def test_native_canvas_required(self):
        image = np.zeros((540, 960, 3), np.uint8)
        with self.assertRaises(ValueError):
            layer.compose_registered_middle_transition(image, image, 2135, "middle-next-f2135-oct6-v1.png", IDENTITY)


class NativeCheckpointTests(unittest.TestCase):
    def test_warm_and_cold_faces_match_the_frozen_private_gate(self):
        timeline = json.loads((ROOT / "timeline-middle-2121-2145-oct6-draft-v1.json").read_text(encoding="utf-8"))
        for frame in (2135, 2143):
            exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
            asset = timeline["assets"][exposure["cel"]]
            source = cv2.imread(str(PRIVATE / "source" / f"f{frame:04d}.png"))
            generated = cv2.resize(cv2.imread(str(ROOT / asset["path"])), (1920, 1080), interpolation=cv2.INTER_LANCZOS4)
            output, diagnostic, masks = layer.compose_registered_middle_transition(source, generated, frame, Path(asset["path"]).name, IDENTITY)
            expected = cv2.imread(str(PRIVATE / "v5-foreground-ownership-audit" / f"f{frame:04d}-private.png"))
            self.assertTrue(np.array_equal(output, expected), frame)
            self.assertEqual(diagnostic.shape, (1080, 3840, 3))
            self.assertEqual(masks.shape, source.shape)


if __name__ == "__main__":
    unittest.main()
