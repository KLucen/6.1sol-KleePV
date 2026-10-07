"""Native closeup ownership and independently registered real-source lyrics."""

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

SOURCE_INTERVAL = (1162, 1225)
CANVAS_SHAPE = (1080, 1920)


@lru_cache(maxsize=1)
def registration():
    timeline = json.loads((HERE / "timeline-private-1162-1225.json").read_text(encoding="utf-8"))
    return {(e["start"], e["end"]): Path(timeline["assets"][e["cel"]]["path"]).name
            for e in timeline["output_exposures"]}


def is_registered(frame, asset_name):
    return frame is not None and any(a <= frame < b and name == Path(asset_name or "").name
                                     for (a, b), name in registration().items())


def _warm_support(image):
    b, g, r = cv2.split(image.astype(np.int16))
    return (g >= b-10) & (r >= g+4) & (r > 190) & (g > 165) & (b > 135)


def _matte_and_sky(image, frame, source=False):
    if image.shape[:2] != CANVAS_SHAPE or not SOURCE_INTERVAL[0] <= frame < SOURCE_INTERVAL[1]:
        raise ValueError("Private closeups require their native canvas and interval")
    value = np.max(image, axis=2)
    b, g, r = cv2.split(image.astype(np.int16))
    blue = (b > r+18) & (b > g+18) & (value >= 180)
    barrier = cv2.morphologyEx((value < 180).astype(np.uint8), cv2.MORPH_CLOSE,
                             np.ones((7, 7), np.uint8))
    _, labels, _, _ = cv2.connectedComponentsWithStats(1-barrier, 8)
    # Cropped hands and sleeves meet borders: only observed blue border
    # pixels can seed the exterior, never every border component.
    border = np.concatenate((labels[0][blue[0]], labels[-1][blue[-1]],
                             labels[:, 0][blue[:, 0]], labels[:, -1][blue[:, -1]]))
    exterior_ids = np.unique(border)
    exterior = np.isin(labels, exterior_ids[exterior_ids != 0])
    count, components, stats, _ = cv2.connectedComponentsWithStats((~exterior).astype(np.uint8), 8)
    matte = np.zeros(CANVAS_SHAPE, np.uint8)
    anchors = ((950, 550), (850, 550), (1050, 550), (950, 800), (950, 1000))
    for index in range(1, count):
        _, _, width, height, area = stats[index]
        anchored = any(np.any(components[y-20:y+20, x-20:x+20] == index) for x, y in anchors)
        if area >= 3000 and width >= 20 and height >= 20 and anchored:
            matte[components == index] = 255
    if source:
        pink = (r >= g+24) & (r >= b+12) & (r >= 160) & (g >= 90)
        cream = (r >= b+31) & (g >= b+14) & (r > 205) & (g > 185) & (b > 140)
        observed = cv2.morphologyEx((pink | cream | (value < 180)).astype(np.uint8),
                                   cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        count, components, stats, _ = cv2.connectedComponentsWithStats(observed, 8)
        for index in range(1, count):
            anchored = any(np.any(components[y-20:y+20, x-20:x+20] == index) for x, y in anchors)
            if stats[index, cv2.CC_STAT_AREA] >= 3000 and anchored:
                matte[components == index] = 255
    else:
        # The f1172 cuff has a decoded contour gap. Its observed cream fill
        # is warmer than generated stars and remains connected to the sleeve.
        warm_fill = (r >= g+8) & (g >= b+18) & (r >= b+25)
        observed = cv2.morphologyEx((warm_fill | (value < 180)).astype(np.uint8),
                                   cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        count, components, stats, _ = cv2.connectedComponentsWithStats(observed, 8)
        for index in range(1, count):
            anchored = any(np.any(components[y-20:y+20, x-20:x+20] == index) for x, y in anchors)
            if stats[index, cv2.CC_STAT_AREA] >= 3000 and anchored:
                matte[components == index] = 255
        matte = cv2.dilate(matte, np.ones((3, 3), np.uint8))
    sky = exterior & blue & ~_warm_support(image)
    sky &= cv2.dilate(matte, np.ones((25, 25), np.uint8)) == 0
    return matte, sky


@lru_cache(maxsize=2)
def _caption(kind):
    with np.load(HERE / f"{kind}-real-caption.npz") as data:
        return {key: data[key].copy() for key in data.files}


def caption_layer(frame):
    if 1162 <= frame < 1217:
        return _caption("pain")
    if 1217 <= frame < 1225:
        return _caption("magic")
    raise ValueError("Unregistered private closeup subtitle frame")


def compose_private(source, generated, frame, asset_name):
    if not is_registered(frame, asset_name):
        raise ValueError("Unregistered closeup source exposure or image filename")
    if source.shape != generated.shape or source.shape[:2] != CANVAS_SHAPE:
        raise ValueError("Private closeups require native BGR images")
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
    alpha, ink = layer["alpha"], layer["ink_rgb"]
    edited = np.any(target != original, axis=2)
    paint = (alpha > 0) & edited
    gap = np.max(np.abs(target.astype(np.float32)-ink), axis=2)
    ring = layer["contrast_ring"] & edited & (gap < 60) & new[y0:y1, x0:x1]
    target[ring] = (54, 45, 65)
    before_text = target.copy()
    blended = alpha[..., None]*ink + (1-alpha[..., None])*target
    target[paint] = np.rint(blended[paint]).clip(0, 255).astype(np.uint8)
    caption_mask = np.zeros(CANVAS_SHAPE, bool)
    caption_mask[y0:y1, x0:x1] = paint | ring
    ownership |= caption_mask
    return output, {"old": old_matte, "new": new_matte, "vacated": vacated,
                    "effects": effects, "caption": caption_mask, "ownership": ownership,
                    "caption_region": (x0, y0, x1, y1), "paint": paint,
                    "before_text": before_text, "expected_text": np.rint(blended).clip(0, 255).astype(np.uint8)}
