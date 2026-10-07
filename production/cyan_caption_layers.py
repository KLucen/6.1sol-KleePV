"""Two observed lyric phases for the cyan profile; the switch is actual f966."""

from functools import lru_cache
import hashlib
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
CANVAS_SHAPE = (1080, 1920)
CORE_COLOR_BGR = np.array((211, 223, 237), np.float32)
PHASES = (
    {"interval": (911, 966), "region": (628, 954, 1264, 1047),
     "donors": ("src-0456-f0911.png", "src-0458-f0914.png", "src-0461-f0919.png")},
    {"interval": (966, 1008), "region": (846, 954, 1048, 1047),
     "donors": ("src-0503-f0967.png", "src-0509-f0973.png", "src-0516-f0981.png", "src-0526-f0993.png")},
)


def cream_glyph_candidate(image):
    return ((np.max(np.abs(image.astype(np.float32)-CORE_COLOR_BGR), axis=2) <= 28)
            & (np.max(image, axis=2) > 220))


@lru_cache(maxsize=2)
def cyan_caption_layer(phase):
    registration = PHASES[phase]
    paths = tuple(ROOT / "source_refs" / path for path in registration["donors"])
    donors = [cv2.imread(str(path), cv2.IMREAD_COLOR) for path in paths]
    if any(image is None for image in donors):
        raise FileNotFoundError("Missing cyan-caption source donor")
    x0, y0, x1, y1 = registration["region"]
    crops = [image[y0:y1, x0:x1] for image in donors]
    crop = crops[0]
    rows = np.zeros(crop.shape[:2], bool)
    for a, b in ((955, 994), (1004, 1044)):
        rows[a-y0:b-y0] = True
    votes = np.stack([cream_glyph_candidate(image) & rows for image in crops]).sum(0)
    core = (votes >= len(crops)-1) & cream_glyph_candidate(crop) & rows
    if np.count_nonzero(core) < 1800:
        raise ValueError("Missing registered cyan-caption source glyphs")
    extent = cv2.dilate(core.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0
    plate = cv2.inpaint(crop, extent.astype(np.uint8)*255, 3, cv2.INPAINT_TELEA)
    foreground = np.median(crop[core], axis=0).astype(np.float32)
    direction = foreground-plate.astype(np.float32)
    alpha = np.clip(np.sum((crop.astype(np.float32)-plate)*direction, axis=2)
                    / np.maximum(np.sum(direction*direction, axis=2), 1), 0, 1)
    alpha[~extent | (alpha < .035)] = 0
    alpha[core] = np.maximum(alpha[core], .9)
    layer = {"source_core": core, "core_votes": votes, "extent": extent,
             "alpha": alpha.astype(np.float32), "foreground_bgr": foreground,
             "estimated_plate_bgr": plate}
    visible = (layer["alpha"] >= .1).astype(np.uint8)
    layer["contrast_edge_support"] = ((cv2.dilate(visible, np.ones((3, 3), np.uint8)) != 0)
                                       & (visible == 0))
    layer["contrast_edge_bgr"] = np.array((54, 45, 65), np.uint8)
    layer["donor_sha256"] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in paths}
    layer["reconstruction"] = "Observed fixed source glyph cores; local inpaint hidden plate and projected AA are reconstruction. Source RGB is retained for observable current-frame glyph cores."
    return layer


def registered_caption(frame):
    for phase, registration in enumerate(PHASES):
        a, b = registration["interval"]
        if frame is not None and a <= frame < b:
            return registration["region"], cyan_caption_layer(phase)
    return None


def cyan_caption_extent(frame, shape=CANVAS_SHAPE):
    mask = np.zeros(shape, np.uint8)
    registered = registered_caption(frame)
    if registered is None:
        return mask
    if tuple(shape) != CANVAS_SHAPE:
        raise ValueError("Cyan captions require the native source canvas")
    region, layer = registered
    x0, y0, x1, y1 = region
    mask[y0:y1, x0:x1][layer["extent"] | layer["contrast_edge_support"]] = 255
    return mask


def restore_cyan_captions(output, source, frame, character_mask):
    mask = np.zeros(source.shape[:2], np.uint8)
    registered = registered_caption(frame)
    if registered is None:
        return output, mask
    if output.shape != source.shape or source.shape[:2] != CANVAS_SHAPE:
        raise ValueError("Cyan captions require matching native source frames")
    region, layer = registered
    x0, y0, x1, y1 = region
    target, original = output[y0:y1, x0:x1], source[y0:y1, x0:x1]
    alpha = layer["alpha"]
    edited = np.any(target != original, axis=2)
    paint = (alpha > 0) & edited
    luma_weights = np.array((.114, .587, .299), np.float32)
    luma = target.astype(np.float32) @ luma_weights
    fg_luma = layer["foreground_bgr"] @ luma_weights
    color_gap = np.max(np.abs(target.astype(np.float32)-layer["foreground_bgr"]), axis=2)
    halo = (layer["contrast_edge_support"] & edited
            & (character_mask[y0:y1, x0:x1] != 0)
            & (np.abs(luma-fg_luma) < 38) & (color_gap < 60))
    target[halo] = layer["contrast_edge_bgr"]
    blended = alpha[..., None]*layer["foreground_bgr"] + (1-alpha[..., None])*target.astype(np.float32)
    target[paint] = np.clip(np.rint(blended[paint]), 0, 255).astype(np.uint8)
    # All actual phase frames have the same glyph position, drawn in front of
    # the moving source anatomy. Registered visible cores retain current RGB.
    observed = paint & layer["source_core"]
    target[observed] = original[observed]
    mask[y0:y1, x0:x1][paint | halo] = 255
    return output, mask
