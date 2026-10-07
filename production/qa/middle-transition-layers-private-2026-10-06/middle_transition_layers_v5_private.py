"""Final private gate: original star-outline coverage with v4 body extraction."""

import cv2
import numpy as np

import middle_transition_layers_private as base
import middle_transition_layers_v4_private as previous

REGISTERED = base.REGISTERED
is_registered = base.is_registered


def effect_support(source):
    h, s, v = cv2.split(cv2.cvtColor(source, cv2.COLOR_BGR2HSV))
    yellow = ((h >= 22) & (h <= 38) & (s > 160) & (v > 215)).astype(np.uint8)
    # The actual f2130/2131 star has one black outline pixel beyond the 7px
    # support. Its native neighborhood contains sky, not an original hand.
    return cv2.dilate(yellow, np.ones((9, 9), np.uint8)) != 0


def compose_private(source, generated, frame, asset_name):
    if not is_registered(frame, asset_name):
        raise ValueError("Unregistered middle asset or source exposure")
    if source.shape != generated.shape or source.shape[:2] != base.CANVAS_SHAPE:
        raise ValueError("Middle images must share native dimensions")
    old_matte, sky = previous.extract(source, frame, source=True)
    new_matte, _ = previous.extract(generated, frame)
    effects = effect_support(source)
    old_matte[effects] = 0
    sky[effects] = False
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
