"""Exact registered cels, dark-contour ownership, and real same-line captions."""

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

SOURCE_INTERVAL = (2121, 2145)
CANVAS_SHAPE = (1080, 1920)
REGISTERED = {
    "middle-after-f2115-2026-10-05-source-v1.png": (2121, 2122),
    "middle-after-f2122-2026-10-05-source-v1.png": (2122, 2129),
    "middle-after-f2129-2026-10-05-source-v1.png": (2129, 2130),
    "middle-after-f2130-2026-10-05-source-v1.png": (2130, 2132),
    "middle-next-f2132-oct6-v1.png": (2132, 2135),
    "middle-next-f2135-oct6-v1.png": (2135, 2136),
    "middle-next-f2136-oct6-v1.png": (2136, 2138),
    "middle-next-f2138-oct6-v1.png": (2138, 2141),
    "middle-next-f2141-oct6-v2.png": (2141, 2143),
    "middle-next-f2143-oct6-v1.png": (2143, 2145)
}


def is_registered(frame, asset_name):
    interval = REGISTERED.get(Path(asset_name or "").name)
    return interval is not None and frame is not None and interval[0] <= frame < interval[1]


def _sky_color(image):
    h, s, v = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
    b, g, r = cv2.split(image.astype(np.int16))
    purple = (h >= 118) & (h <= 140) & (s >= 60) & (s <= 160) & (v >= 205)
    purple &= (b >= r + 35) & (b >= g + 55)
    night = (h >= 95) & (h <= 140) & (s >= 165) & (v >= 185)
    return purple | night, purple, night


def _matte_and_sky(image, frame, source=False):
    if image.shape[:2] != CANVAS_SHAPE or not SOURCE_INTERVAL[0] <= frame < SOURCE_INTERVAL[1]:
        raise ValueError("Private middle extraction requires its registered native canvas")
    b, g, r = cv2.split(image.astype(np.int16))
    value = np.max(image, axis=2)
    sky_color, purple, night = _sky_color(image)
    # White scribbled stars cannot enclose an opaque object: only actual dark
    # character contours form the flood barrier. The cool face is enclosed by
    # dark ink, not classified as bright sky (observed HSV H~108-113/S~90).
    barrier = (value < 180).astype(np.uint8)
    gap = 9 if source else 5
    barrier = cv2.morphologyEx(barrier, cv2.MORPH_CLOSE, np.ones((gap, gap), np.uint8))
    _, labels, _, _ = cv2.connectedComponentsWithStats(1 - barrier, 8)
    border_ids = np.unique(np.concatenate((labels[0][sky_color[0]], labels[-1][sky_color[-1]],
                                           labels[:, 0][sky_color[:, 0]], labels[:, -1][sky_color[:, -1]])))
    exterior = np.isin(labels, border_ids[border_ids != 0])
    count, components, stats, _ = cv2.connectedComponentsWithStats((~exterior).astype(np.uint8), 8)
    warm = (r >= g + 18) & (r >= b + 15) & (r >= 150) & (g >= 75)
    cold_anchor = np.zeros(CANVAS_SHAPE, bool)
    if frame >= 2141:
        cold_anchor[:900, 1020:1630] = True
    cold = (b >= r + 25) & (b >= g + 10) & ~sky_color & (value >= 180)
    matte = np.zeros(CANVAS_SHAPE, np.uint8)
    for index in range(1, count):
        _, _, width, height, area = stats[index]
        if area < 5000 or width < 40 or height < 40:
            continue
        component = components == index
        anchored_warm = np.count_nonzero(component & warm) >= 500
        anchored_cold = np.count_nonzero(component & cold & cold_anchor) >= 500
        if anchored_warm or anchored_cold:
            matte[component] = 255
    if source:
        # Observed pink fill and green compressed source ink repair open source
        # contours; these colors are absent from this frame's actual sky/stars.
        pink = (r >= g + 24) & (r >= b + 12) & (r >= 160) & (g >= 90)
        matte[pink] = 255
        if frame >= 2141:
            h, s, v = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
            old_green = (h >= 45) & (h <= 95) & (s >= 90) & (v < 215)
            matte[old_green] = 255
    else:
        # Sky in genuine gaps between warm hair/legs remains source-owned.
        # This predicate excludes the inspected low-saturation H108-113 cool face.
        matte[sky_color] = 0
        matte = cv2.dilate(matte, np.ones((3, 3), np.uint8))
        matte[sky_color] = 0
    sky = exterior & sky_color & (cv2.dilate(matte, np.ones((25, 25), np.uint8)) == 0)
    sky[950:1052, 695:1225] = False
    return matte, sky


def _plate(source, sky, target):
    if not np.any(target):
        return source.copy()
    _, purple, night = _sky_color(source)
    purple_sky = sky & purple
    night_sky = sky & night
    # During the observed wipe, reconstruct separately from each actual sky
    # population. Nearest visible support assigns only the hidden vacated area.
    if np.count_nonzero(night_sky[::8, ::8]) < 400:
        return _source_gradient(source, purple_sky, target)
    if np.count_nonzero(purple_sky[::8, ::8]) < 400:
        return _source_gradient(source, night_sky, target)
    purple_distance = cv2.distanceTransform((~purple_sky).astype(np.uint8), cv2.DIST_L2, 5)
    night_distance = cv2.distanceTransform((~night_sky).astype(np.uint8), cv2.DIST_L2, 5)
    purple_target = target & (purple_distance <= night_distance)
    night_target = target & ~purple_target
    result = _source_gradient(source, purple_sky, purple_target)
    night_plate = _source_gradient(source, night_sky, night_target)
    result[night_target] = night_plate[night_target]
    return result


@lru_cache(maxsize=1)
def caption_layer():
    with np.load(HERE / "middle-same-line-f2141-real-caption.npz") as data:
        return {key: data[key].copy() for key in data.files}


def compose_private(source, generated, frame, asset_name):
    if not is_registered(frame, asset_name):
        raise ValueError("Unregistered middle asset or source exposure")
    if source.shape != generated.shape or source.shape[:2] != CANVAS_SHAPE:
        raise ValueError("Private middle images must share native dimensions")
    old_matte, sky = _matte_and_sky(source, frame, source=True)
    new_matte, _ = _matte_and_sky(generated, frame)
    old = cv2.dilate(old_matte, np.ones((17 if frame >= 2141 else 9,) * 2, np.uint8)) != 0
    new = new_matte != 0
    layer = caption_layer()
    x0, y0, x1, y1 = map(int, layer["region"])
    old_caption = np.zeros(CANVAS_SHAPE, bool)
    old_caption[y0:y1, x0:x1] = layer["extent"]
    vacated = (old | old_caption) & ~new
    plate = _plate(source, sky, vacated)
    output = source.copy()
    output[vacated] = plate[vacated]
    output[new] = generated[new]
    visible = layer["alpha"] > .1
    ring = (cv2.dilate(visible.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0) & ~visible
    target = output[y0:y1, x0:x1]
    target[ring] = (54, 45, 65)
    alpha = layer["alpha"]
    blend = alpha[..., None] * layer["ink_rgb"] + (1-alpha[..., None]) * target
    paint = alpha > 0
    target[paint] = np.rint(blend[paint]).clip(0, 255).astype(np.uint8)
    caption = np.zeros(CANVAS_SHAPE, bool)
    caption[y0:y1, x0:x1] = paint | ring
    ownership = old | new | old_caption | caption
    return output, {"old": old_matte, "new": new_matte, "old_support": old,
                    "old_caption": old_caption, "vacated": vacated,
                    "caption": caption, "ownership": ownership, "sky": sky}
