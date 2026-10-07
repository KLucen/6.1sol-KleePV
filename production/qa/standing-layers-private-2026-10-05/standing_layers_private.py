"""Private, exact-registration standing mattes and real-source lyric layers."""

from functools import lru_cache
import json
from pathlib import Path
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from night_transition_layers import _source_gradient
import star_gestures_layers as base

SOURCE_INTERVAL = (1043, 1162)
CANVAS_SHAPE = (1080, 1920)


@lru_cache(maxsize=1)
def registration():
    timeline = json.loads((HERE / "timeline-private-1043-1162.json").read_text(encoding="utf-8"))
    return {(e["start"], e["end"]): Path(timeline["assets"][e["cel"]]["path"]).name
            for e in timeline["output_exposures"]}


def is_registered(frame, asset_name):
    return frame is not None and any(start <= frame < end and name == Path(asset_name or "").name
                                     for (start, end), name in registration().items())


def _warm_support(image):
    b, g, r = cv2.split(image.astype(np.int16))
    return (g >= b - 10) & (r >= g + 4) & (r > 190) & (g > 165) & (b > 135)


def _matte_and_sky(image, frame, source=False):
    if image.shape[:2] != CANVAS_SHAPE or not SOURCE_INTERVAL[0] <= frame < SOURCE_INTERVAL[1]:
        raise ValueError("Private standing extraction requires its native registered frame")
    value = np.max(image, axis=2)
    b, g, r = cv2.split(image.astype(np.int16))
    blue = (b > r + 18) & (b > g + 18) & (value >= 180)
    warm = _warm_support(image)
    # Both observed source and selected cels use dark enclosing character
    # contours. Pale star AA must not become a flood barrier at cuff contact.
    barrier = (value < 180).astype(np.uint8)
    barrier = cv2.morphologyEx(barrier, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    _, labels, _, _ = cv2.connectedComponentsWithStats(1 - barrier, 8)
    exterior_ids = np.unique(np.concatenate((labels[0], labels[:, 0], labels[:, -1])))
    exterior = np.isin(labels, exterior_ids[exterior_ids != 0])
    count, components, stats, _ = cv2.connectedComponentsWithStats((~exterior).astype(np.uint8), 8)
    anchors = ((950, 550), (900, 800), (1020, 800), (900, 1010), (1030, 1010))
    matte = np.zeros(CANVAS_SHAPE, np.uint8)
    for index in range(1, count):
        _, _, width, height, area = stats[index]
        anchored = any(np.any(components[y-20:y+20, x-20:x+20] == index) for x, y in anchors)
        if area >= 7000 and width >= 40 and height >= 40 and anchored:
            matte[components == index] = 255
    if source:
        matte[value < 180] = 255
        # Original pale clothing and hair have decoded contour gaps.
        # Their observed pink fill differs from blue sky and cream stars;
        # retain this source color support, not an invented silhouette.
        pink_fill = (r >= g + 24) & (r >= b + 12) & (r >= 160) & (g >= 90)
        crop = np.zeros(CANVAS_SHAPE, bool)
        if frame < 1161:
            crop[35:980, 610:1320] = True
        else:
            crop[:, 260:1600] = True
        matte[pink_fill & crop] = 255
    else:
        matte = cv2.dilate(matte, np.ones((3, 3), np.uint8))
    sky = exterior & blue & ~warm
    sky &= cv2.dilate(matte, np.ones((25, 25), np.uint8)) == 0
    return matte, sky


def subject_mask(image, frame, asset_name, source=False):
    return _matte_and_sky(image, frame, source)[0] if is_registered(frame, asset_name) else None


@lru_cache(maxsize=1)
def short_layer():
    with np.load(HERE / "short-caption-f1161-real.npz") as data:
        return {key: data[key].copy() for key in data.files}


def caption_layer(frame):
    if 1043 <= frame < 1144:
        return base.caption_layer(2)
    if 1144 <= frame < 1162:
        return short_layer()
    raise ValueError("Outside the private standing caption interval")


def compose_private(source, generated, frame, asset_name):
    if not is_registered(frame, asset_name):
        raise ValueError("Unregistered standing asset or source exposure")
    if source.shape != generated.shape or source.shape[:2] != CANVAS_SHAPE:
        raise ValueError("Private standing images must share native dimensions")
    old_matte, sky = _matte_and_sky(source, frame, source=True)
    new_matte, _ = _matte_and_sky(generated, frame)
    old = cv2.dilate(old_matte, np.ones((9, 9), np.uint8)) != 0
    effects = _warm_support(source) & ~old
    effects[950:] = False
    effects = cv2.dilate(effects.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0
    old &= ~effects
    new = new_matte != 0
    vacated = old & ~new
    plate = _source_gradient(source, sky, vacated)
    output = source.copy()
    output[vacated] = plate[vacated]
    output[new] = generated[new]
    ownership = old | new
    layer = caption_layer(frame)
    x0, y0, x1, y1 = map(int, layer["region"])
    target = output[y0:y1, x0:x1]
    original = source[y0:y1, x0:x1]
    alpha = layer["alpha"]
    ink = layer.get("ink_rgb", layer.get("foreground"))
    edited = np.any(target != original, axis=2)
    paint = (alpha > 0) & edited
    gap = np.max(np.abs(target.astype(np.float32) - ink), axis=2)
    ring = layer["contrast_ring"] & edited & (gap < 60) & new[y0:y1, x0:x1]
    if frame >= 1144:
        # A complete one-pixel contrast ring separates the real short glyphs
        # from the selected boot badges; it does not add any glyph strokes.
        ring = layer["contrast_ring"] & edited & new[y0:y1, x0:x1]
    target[ring] = (54, 45, 65)
    blended = alpha[..., None] * ink + (1 - alpha[..., None]) * target
    target[paint] = np.clip(np.rint(blended[paint]), 0, 255).astype(np.uint8)
    observed_core = layer["core"] & paint
    target[observed_core] = original[observed_core]
    caption_mask = np.zeros(CANVAS_SHAPE, bool)
    caption_mask[y0:y1, x0:x1] = paint | ring
    ownership |= caption_mask
    return output, {"old": old_matte, "new": new_matte, "vacated": vacated,
                    "effects": effects, "caption": caption_mask, "ownership": ownership,
                    "observed_core": observed_core, "caption_region": (x0, y0, x1, y1)}
