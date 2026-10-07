import unittest
from unittest.mock import patch

import numpy as np

import star_extended_layers as layers


class ExtendedStarRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.image = np.zeros((3, 4, 3), np.uint8)
        self.identity = np.float32([[1, 0, 0], [0, 1, 0]])

    def test_outside_scope_does_not_load_checkpoint(self):
        with patch.object(layers, "_checkpoint") as checkpoint:
            for frame in (None, 0, 1042, 1225, 3657):
                self.assertIsNone(layers.compose_registered_star_extended(
                    self.image, self.image, frame, "unknown.png", self.identity))
            checkpoint.assert_not_called()

    def test_unknown_filename_does_not_override_existing_renderer(self):
        with patch.object(layers, "_checkpoint") as checkpoint:
            checkpoint.return_value.is_registered.return_value = False
            self.assertIsNone(layers.compose_registered_star_extended(
                self.image, self.image, 1043, "unknown.png", self.identity))
            checkpoint.return_value.compose_private.assert_not_called()

    def test_registered_transform_must_be_identity(self):
        with patch.object(layers, "_checkpoint") as checkpoint:
            checkpoint.return_value.is_registered.return_value = True
            with self.assertRaises(ValueError):
                layers.compose_registered_star_extended(self.image, self.image,
                    1162, "registered.png", [[1, 0, 1], [0, 1, 0]])
            checkpoint.return_value.compose_private.assert_not_called()

    def test_registered_result_and_diagnostic_masks(self):
        empty = np.zeros(self.image.shape[:2], bool)
        detail = {key: empty.copy() for key in ("old", "new", "vacated", "effects", "caption")}
        detail["caption"][1, 2] = True
        result = self.image + 7
        with patch.object(layers, "_checkpoint") as checkpoint, patch.object(
                layers, "compose_with_clear_captions", return_value=(result, detail)):
            checkpoint.return_value.is_registered.return_value = True
            output, comparison, masks = layers.compose_registered_star_extended(
                self.image, self.image, 1217, "registered.png", self.identity)
        self.assertTrue(np.array_equal(output, result))
        self.assertEqual(comparison.shape, (3, 8, 3))
        self.assertTrue(np.array_equal(masks[1, 2], [245, 95, 180]))


if __name__ == "__main__":
    unittest.main()
