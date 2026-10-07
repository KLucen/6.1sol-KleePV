"""Registered transparent source glyphs for the raised-arms close-up only."""

from functools import lru_cache
import hashlib
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE_INTERVAL = (1225, 1285)
CANVAS_SHAPE = (1080, 1920)
REGION = (780, 953, 1135, 1049)
LINE_CORE_ROWS = ((958, 991), (1005, 1043))
DONOR = ROOT / "source_refs/src-0761-f1229.png"
PHASE_DONORS = (ROOT / "source_refs/src-0757-f1225.png",
                ROOT / "source_refs/src-0773-f1241.png",
                ROOT / "source_refs/src-0788-f1256.png",
                ROOT / "source_refs/src-0793-f1261.png",
                ROOT / "source_refs/src-0814-f1282.png")
CORE_COLOR_BGR = np.array((211, 223, 237), np.float32)


def cream_glyph_candidate(image):
    # Source compression over the pink coat can turn real cream strokes B >= G.
    return ((np.max(np.abs(image.astype(np.float32)-CORE_COLOR_BGR), axis=2) <= 28)
            & (np.max(image, axis=2) > 220))


@lru_cache(maxsize=1)
def raised_caption_layer():
    paths = (DONOR, *PHASE_DONORS)
    donors = [cv2.imread(str(path), cv2.IMREAD_COLOR) for path in paths]
    if any(image is None for image in donors):
        raise FileNotFoundError("Missing raised-shot source glyph donor")
    if any(image.shape[:2] != CANVAS_SHAPE for image in donors):
        raise ValueError("Raised caption donors require the native source canvas")
    x0, y0, x1, y1 = REGION
    crops = [image[y0:y1, x0:x1] for image in donors]
    crop = crops[0]
    rows = np.zeros(crop.shape[:2], bool)
    for a, b in LINE_CORE_ROWS:
        rows[a-y0:b-y0] = True
    votes = np.stack([cream_glyph_candidate(image) & rows for image in crops]).sum(0)
    # The old button stays in the small shot but moves away in the close-up.
    # Five of six actual-source poses exclude that button and moving collar/hair.
    core = (votes >= 5) & cream_glyph_candidate(crop)
    if np.count_nonzero(core) < 7000:
        raise ValueError("Missing registered raised-shot glyph strokes")
    extent = cv2.dilate(core.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0
    plate = cv2.inpaint(crop, extent.astype(np.uint8)*255, 3, cv2.INPAINT_TELEA)
    foreground = np.median(crop[core], axis=0).astype(np.float32)
    direction = foreground - plate.astype(np.float32)
    alpha = np.clip(np.sum((crop.astype(np.float32)-plate)*direction, axis=2)
                    / np.maximum(np.sum(direction*direction, axis=2), 1), 0, 1)
    alpha[~extent | (alpha < .035)] = 0
    alpha[core] = np.maximum(alpha[core], .9)
    visible = (alpha >= .1).astype(np.uint8)
    ring = (cv2.dilate(visible, np.ones((3, 3), np.uint8)) != 0) & (visible == 0)
    return {"source_core": core, "core_votes": votes, "extent": extent,
            "alpha": alpha.astype(np.float32), "foreground_bgr": foreground,
            "estimated_plate_bgr": plate, "contrast_edge_support": ring,
            "contrast_edge_bgr": np.array((54, 45, 65), np.uint8),
            "donor_sha256": hashlib.sha256(DONOR.read_bytes()).hexdigest(),
            "phase_donor_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in PHASE_DONORS},
            "reconstruction": "Fixed cream-color source cores, 5/6 registered moving-body donors, local inpaint plate, projected AA; hidden plate and AA are reconstructed, not source-exact.",
            "contrast_edge_policy": "Fixed 1px dark edge within registered glyph ring, only edited low-contrast bright actual new-subject underlay; original glyph core RGB and position retained."}


def raised_caption_extent(frame, shape=CANVAS_SHAPE):
    mask = np.zeros(shape, np.uint8)
    if frame is None or not SOURCE_INTERVAL[0] <= frame < SOURCE_INTERVAL[1]:
        return mask
    if tuple(shape) != CANVAS_SHAPE:
        raise ValueError("Raised captions require the native source canvas")
    layer = raised_caption_layer()
    x0, y0, x1, y1 = REGION
    mask[y0:y1, x0:x1][layer["extent"] | layer["contrast_edge_support"]] = 255
    return mask


def restore_raised_captions(output, source, frame, character_mask=None):
    mask = np.zeros(source.shape[:2], np.uint8)
    if frame is None or not SOURCE_INTERVAL[0] <= frame < SOURCE_INTERVAL[1]:
        return output, mask
    if output.shape != source.shape or source.shape[:2] != CANVAS_SHAPE:
        raise ValueError("Raised captions require matching native source frames")
    layer = raised_caption_layer()
    x0, y0, x1, y1 = REGION
    target, original = output[y0:y1, x0:x1], source[y0:y1, x0:x1]
    alpha = layer["alpha"]
    edited = np.any(target != original, axis=2)
    paint = (alpha > 0) & edited
    halo = np.zeros(alpha.shape, bool)
    if character_mask is not None:
        if character_mask.shape != source.shape[:2]:
            raise ValueError("Raised contrast-edge mask must use the native canvas")
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
    observed = paint & layer["source_core"] & cream_glyph_candidate(original)
    target[observed] = original[observed]
    mask[y0:y1, x0:x1][paint | halo] = 255
    return output, mask
