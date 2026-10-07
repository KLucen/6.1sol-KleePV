"""Complete real-glyph contrast without modifying retained body checkpoints."""

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from night_transition_layers import _source_gradient

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def _clear_short_layer():
    path = ROOT / "qa/oct6-star-extended-integration/short-f2420-clear-real-caption.npz"
    with np.load(path) as data:
        return {key: data[key].copy() for key in data.files}


@lru_cache(maxsize=1)
def _clear_long_layer():
    path = ROOT / "qa/caption-clear-v2-2026-10-06/long-f3402-cn-clear-real-caption-v2.npz"
    with np.load(path) as data:
        return {key: data[key].copy() for key in data.files}


def caption_layer(checkpoint, frame):
    if 1043 <= frame < 1144:
        return _clear_long_layer()
    if 1144 <= frame < 1162:
        return _clear_short_layer()
    return checkpoint.caption_layer(frame)


def compose_with_clear_captions(checkpoint, source, generated, frame):
    old_matte, sky = checkpoint._matte_and_sky(source, frame, source=True)
    new_matte, _ = checkpoint._matte_and_sky(generated, frame)
    old = cv2.dilate(old_matte, np.ones((9, 9), np.uint8)) != 0
    effects = checkpoint._warm_support(source) & ~old
    effects[950:] = False
    effects = cv2.dilate(effects.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0
    old &= ~effects
    new = new_matte != 0
    vacated = old & ~new
    plate = _source_gradient(source, sky, vacated)
    output = source.copy()
    output[vacated] = plate[vacated]
    output[new] = generated[new]
    layer = caption_layer(checkpoint, frame)
    x0, y0, x1, y1 = map(int, layer["region"])
    target = output[y0:y1, x0:x1]
    original = source[y0:y1, x0:x1]
    alpha = layer["alpha"]
    ink = layer.get("ink_rgb", layer.get("foreground"))
    paint = (alpha > 0) & np.any(target != original, axis=2)
    visible = alpha > .1
    ring = (cv2.dilate(visible.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0) & ~visible
    target[ring] = (54, 45, 65)
    blended = alpha[..., None] * ink + (1-alpha[..., None]) * target
    target[paint] = np.rint(blended[paint]).clip(0, 255).astype(np.uint8)
    # Only standing layers carry observed current-source cores. The closeup
    # donor's core is not a valid current-source pixel oracle at coat buttons.
    if frame < 1162:
        observed_core = layer["core"] & paint
        target[observed_core] = original[observed_core]
    caption = np.zeros(source.shape[:2], bool)
    caption[y0:y1, x0:x1] = paint | ring
    return output, {"old": old_matte, "new": new_matte, "vacated": vacated,
                    "effects": effects, "caption": caption,
                    "ownership": old | new | caption}
