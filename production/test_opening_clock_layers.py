"""Unit and actual-cel checks for the conservative isolated-clock helper."""

import json
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import opening_clock_layers as clock


class ClockLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mapping = json.loads((clock.ROOT / "source_map.json").read_text(encoding="utf-8"))
        cls.candidates = {c["frame"]: c for c in mapping["candidates"]}

    def load_pair(self,frame,name):
        gen = clock.read_image(clock.ROOT / "generated" / name)
        src = clock.read_image(clock.ROOT / self.candidates[frame]["reference"])
        return src,gen

    def test_all_supported_pairs_copy_current_source_only(self):
        for frame,name in [*clock.RECTANGLES,clock.RELEASE_KEY]:
            with self.subTest(frame=frame,name=name):
                src,gen = self.load_pair(frame,name)
                # Deliberately vary the current source so a cached reference fails.
                current = np.bitwise_xor(src,np.uint8(1))
                before = gen.copy()
                result,mask = clock.restore_clock(gen,current,gen,frame,name,clock.IDENTITY)
                selected = mask != 0
                self.assertGreater(np.count_nonzero(selected),0)
                np.testing.assert_array_equal(result[selected],current[selected])
                np.testing.assert_array_equal(result[~selected],before[~selected])
                np.testing.assert_array_equal(gen,before)
                np.testing.assert_array_equal(src,np.bitwise_xor(current,np.uint8(1)))

    def test_released_clock_preserves_generated_glove(self):
        src,gen = self.load_pair(*clock.RELEASE_KEY)
        result,mask = clock.restore_clock(gen,src,gen,*clock.RELEASE_KEY,clock.IDENTITY)
        hsv = cv2.cvtColor(gen,cv2.COLOR_BGR2HSV)
        h,s,v = cv2.split(hsv)
        brown = (h < 27) & (s > 75) & (v > 80) & (v < 190)
        guard = np.zeros(mask.shape,np.uint8)
        guard[450:570,985:1080] = brown[450:570,985:1080].astype(np.uint8)*255
        guard = cv2.dilate(guard,np.ones((5,5),np.uint8)) != 0
        self.assertEqual(np.count_nonzero((mask != 0) & guard),0)
        np.testing.assert_array_equal(result[guard],gen[guard])

    def test_unknown_asset_frame_and_held_clocks_are_noops(self):
        src,gen = self.load_pair(162,"fine-f0162.png")
        for frame,name in ((162,"new-unreviewed.png"),(163,"fine-f0162.png"),
                           (157,"fine-f0157.png"),(157,"fine-f0157-geometry-repair.png"),
                           (129,"fine-f0129-geometry-repair.png"),(79,"fine-f0079-geometry-repair.png")):
            with self.subTest(frame=frame,name=name):
                result,mask = clock.restore_clock(gen,src,gen,frame,name,clock.IDENTITY)
                self.assertEqual(np.count_nonzero(mask),0)
                np.testing.assert_array_equal(result,gen)

    def test_nonidentity_and_invalid_matrices_are_noops(self):
        src,gen = self.load_pair(162,"fine-f0162.png")
        transforms = ([[1,0,1],[0,1,0]],[[1.01,0,0],[0,1,0]],
                      [[1,0,0],[0,1,1e-12]],np.eye(3),[[1,0],[0,1]],
                      [[1,0,0],[0,float("nan"),0]],"invalid")
        for matrix in transforms:
            with self.subTest(matrix=str(matrix)):
                result,mask = clock.restore_clock(gen,src,gen,162,"fine-f0162.png",matrix)
                self.assertEqual(np.count_nonzero(mask),0)
                np.testing.assert_array_equal(result,gen)

    def test_identity_default_and_path_asset_name(self):
        src,gen = self.load_pair(162,"fine-f0162.png")
        result,mask = clock.restore_clock(gen,src,gen,162,"generated/fine-f0162.png",None)
        self.assertGreater(np.count_nonzero(mask),0)
        np.testing.assert_array_equal(result[mask != 0],src[mask != 0])

    def test_released_asset_and_mask_hash_fail_closed(self):
        src,gen = self.load_pair(*clock.RELEASE_KEY)
        for constant in ("RELEASE_ASSET_SHA256","RELEASE_MASK_SHA256"):
            with self.subTest(constant=constant),patch.object(clock,constant,"0"*64):
                result,mask = clock.restore_clock(gen,src,gen,*clock.RELEASE_KEY,clock.IDENTITY)
                self.assertEqual(np.count_nonzero(mask),0)
                np.testing.assert_array_equal(result,gen)

    def test_released_different_raster_fails_closed(self):
        src,gen = self.load_pair(*clock.RELEASE_KEY)
        changed = gen.copy()
        changed[500,1050,0] ^= np.uint8(1)
        result,mask = clock.restore_clock(changed,src,changed,*clock.RELEASE_KEY,clock.IDENTITY)
        self.assertEqual(np.count_nonzero(mask),0)
        np.testing.assert_array_equal(result,changed)

    def test_invalid_canvas_rejected(self):
        value = np.zeros((100,100,3),np.uint8)
        with self.assertRaises(ValueError):
            clock.restore_clock(value,value,value,162,"fine-f0162.png",None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
