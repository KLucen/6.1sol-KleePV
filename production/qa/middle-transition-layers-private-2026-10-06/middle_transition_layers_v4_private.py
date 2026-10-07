"""Observed warm-face ownership and source-exact yellow effects; no artwork edits."""

import cv2
import numpy as np

import middle_transition_layers_private as base
import middle_transition_layers_v3_private as previous

REGISTERED = base.REGISTERED
is_registered = base.is_registered


def effect_support(source):
    h, s, v = cv2.split(cv2.cvtColor(source, cv2.COLOR_BGR2HSV))
    yellow = ((h >= 22) & (h <= 38) & (s > 160) & (v > 215)).astype(np.uint8)
    return cv2.dilate(yellow, np.ones((7, 7), np.uint8)) != 0


def extract(image, frame, source=False):
    matte, sky = previous.extract(image, frame, source)
    if source:
        effects = effect_support(image)
        matte[effects] = 0
        sky[effects] = False
        return matte, sky
    if frame != 2135:
        return matte, sky
    b, g, r = cv2.split(image.astype(np.int16))
    actual_sky, _, _ = base._sky_color(image)
    observed_fill = ((r >= g + 18) & (r >= b + 15) & (r >= 150) & (g >= 75)).astype(np.uint8)
    observed_fill[:, :850] = 0
    count, labels, stats, _ = cv2.connectedComponentsWithStats(observed_fill, 8)
    fill = np.zeros(image.shape[:2], np.uint8)
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] >= 5000:
            fill[labels == index] = 255
    fill = cv2.dilate(fill, np.ones((3, 3), np.uint8))
    matte = np.maximum(matte, fill)
    _, holes = cv2.connectedComponents((matte == 0).astype(np.uint8), 8)
    border = np.unique(np.concatenate((holes[0], holes[-1], holes[:, 0], holes[:, -1])))
    enclosed = (holes != 0) & ~np.isin(holes, border)
    retain = enclosed & ~actual_sky
    retain[:, :850] = False
    matte[retain] = 255
    matte[actual_sky] = 0
    sky[matte != 0] = False
    return matte, sky


def compose_private(source, generated, frame, asset_name):
    if not is_registered(frame, asset_name):
        raise ValueError("Unregistered middle asset or source exposure")
    if source.shape != generated.shape or source.shape[:2] != base.CANVAS_SHAPE:
        raise ValueError("Middle images must share native dimensions")
    old_matte, sky = extract(source, frame, source=True)
    new_matte, _ = extract(generated, frame)
    effects = effect_support(source)
    old = cv2.dilate(old_matte, np.ones((17 if frame >= 2141 else 9,) * 2, np.uint8)) != 0
    old[effects] = False
    new = new_matte != 0
    layer = base.caption_layer()
    x0, y0, x1, y1 = map(int, layer["region"])
    old_caption = np.zeros(base.CANVAS_SHAPE, bool)
    old_caption[y0:y1, x0:x1] = layer["extent"]
    vacated = (old | old_caption) & ~new & ~effects
    plate = base._plate(source, sky, vacated)
    output = source.copy()
    output[vacated] = plate[vacated]
    output[new] = generated[new]
    output[effects] = source[effects]
    visible = layer["alpha"] > .1
    ring = (cv2.dilate(visible.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0) & ~visible
    target = output[y0:y1, x0:x1]
    target[ring] = (54, 45, 65)
    alpha = layer["alpha"]
    blend = alpha[..., None] * layer["ink_rgb"] + (1-alpha[..., None]) * target
    paint = alpha > 0
    target[paint] = np.rint(blend[paint]).clip(0, 255).astype(np.uint8)
    caption = np.zeros(base.CANVAS_SHAPE, bool)
    caption[y0:y1, x0:x1] = paint | ring
    ownership = old | new | old_caption | caption | effects
    return output, {"old": old_matte, "new": new_matte, "old_support": old,
                    "old_caption": old_caption, "vacated": vacated,
                    "caption": caption, "effects": effects,
                    "ownership": ownership, "sky": sky}
