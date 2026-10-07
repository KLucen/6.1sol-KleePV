"""Restore source subtitle raster in the audited opening shots."""

from __future__ import annotations

import cv2
import numpy as np


def restore_opening_captions(output: np.ndarray, source: np.ndarray, frame: int | None,
                             asset_name: str | None = None):
    mask = np.zeros(source.shape[:2], np.uint8)
    if frame is None:
        return output, mask

    if 38 <= frame < 210:
        # The full left caption field is clear of both versions of the character.
        mask[350:840, :800] = 255
    elif 210 <= frame < 287:
        mask = _pale_ink_in_rect(source, (180, 495, 780, 635))
    elif 287 <= frame < 323:
        # The f290 zoom also adds spurious Chinese glyphs inside the bubble.
        # This source-only interior stays clear of both characters in 290..293.
        if 290 <= frame < 294:
            mask[390:550, 220:560] = 255
        rect = ((180, 470, 600, 545) if frame < 290 else
                (180, 205, 600, 340) if frame < 294 else
                (180, 290, 600, 380))
        mask |= _pale_ink_in_rect(source, rect)
    elif 411 <= frame < 504:
        # The two-line lyric sits below the kneeling character throughout this shot.
        mask[925:1060, 700:1230] = 255
    elif 536 <= frame < 666:
        if frame >= 661 and asset_name == "fine-f0661-source-extent-v2.png":
            # This reviewed redraw stops before x1245. Copy the unobstructed
            # source field, also erasing any differently rendered draft letters.
            mask[495:670, 1245:1830] = 255
            output[mask != 0] = source[mask != 0]
            return output, mask
        # Klee's extended legs can pass behind this caption in the replacement.
        return _restore_front_ink(output, source, (1245, 495, 1830, 670))

    output[mask != 0] = source[mask != 0]
    return output, mask


def _pale_ink_in_rect(source: np.ndarray, rect: tuple[int, int, int, int]):
    x0, y0, x1, y1 = rect
    hsv = cv2.cvtColor(source[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    core = (((h >= 10) & (h <= 43) & (s < 65) & (v > 190))
            | ((s < 25) & (v > 205))).astype(np.uint8)
    # Include compressed antialiasing around the bright glyph, but keep the
    # original shot's character and background outside those pixels untouched.
    local = cv2.dilate(core, np.ones((5, 5), np.uint8))
    mask = np.zeros(source.shape[:2], np.uint8)
    mask[y0:y1, x0:x1] = local * 255
    return mask


def _restore_front_ink(output, source, rect):
    x0, y0, x1, y1 = rect
    source_crop = source[y0:y1, x0:x1].astype(np.float32)
    output_crop = output[y0:y1, x0:x1].astype(np.float32)
    extent = _pale_ink_in_rect(source, rect)[y0:y1, x0:x1] != 0
    # This source field contains only the flat purple backdrop and the caption.
    background = np.median(source_crop[~extent], axis=0)
    distance = np.linalg.norm(source_crop-background, axis=2)
    foreground = np.median(source_crop[extent & (distance >= np.percentile(distance[extent], 85))], axis=0)
    direction = foreground-background
    alpha = np.clip(np.sum((source_crop-background)*direction, axis=2)
                    / np.dot(direction, direction), 0, 1)
    ink = extent & (alpha > 0.06)
    changed = np.max(np.abs(output_crop-source_crop), axis=2) > 12
    new_foreground = np.linalg.norm(output_crop-background, axis=2) > 25
    over_character = ink & changed & new_foreground
    result = source_crop.copy()
    # Preserve the source's compression residue while removing its purple matte
    # from partially covered glyph edges when a new limb is underneath.
    result[over_character] += ((1-alpha[over_character, None])
                              * (output_crop[over_character]-background))
    output[y0:y1, x0:x1][ink] = np.clip(np.rint(result[ink]), 0, 255).astype(np.uint8)
    mask = np.zeros(source.shape[:2], np.uint8)
    mask[y0:y1, x0:x1][ink] = 255
    return output, mask
