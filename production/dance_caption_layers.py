"""Transparent source-derived lyrics for separately audited dance phases."""

from __future__ import annotations

from functools import lru_cache
import hashlib
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
DONOR = ROOT / "source_refs/src-0377-f0831.png"
SOURCE_INTERVAL = (831, 897)
REGION = (754, 954, 1136, 1047)
NIGHT_INTERVAL = (897, 911)
NIGHT_REGION = (628, 954, 1264, 1047)
NIGHT_DONOR = ROOT / "source_refs/src-0456-f0911.png"
NIGHT_PHASE_DONORS = (ROOT / "source_refs/src-0458-f0914.png",
                      ROOT / "source_refs/src-0461-f0919.png")
CLEAR_INTERVAL = (812, 831)
CLEAR_REGION = (870, 954, 1026, 1044)
CLEAR_ASSETS = {
    "fullpv-early-f0812-source-v1.png": (812, 814),
    "fullpv-early-f0814-source-v1.png": (814, 815),
    "fullpv-early-f0815-source-v1.png": (815, 819),
    "fullpv-early-f0819-source-v1.png": (819, 823),
    "fullpv-early-f0823-source-v1.png": (823, 827),
    "root-continuation-f0827-v1.png": (827, 831),
}
CANVAS_SHAPE = (1080, 1920)
LINE_CORE_ROWS = ((959, 988), (1006, 1040))
PHASE_DONORS = (ROOT / "source_refs/src-0381-f0835.png",
                ROOT / "source_refs/src-0385-f0839.png")


def restore_clear_dance_captions(output, source, frame, asset_name=None):
    mask = np.zeros(source.shape[:2], np.uint8)
    span = CLEAR_ASSETS.get(Path(asset_name).name) if asset_name else None
    if frame is None or span is None or not span[0] <= frame < span[1]:
        return output, mask
    if output.shape != source.shape or source.shape[:2] != CANVAS_SHAPE:
        raise ValueError("Clear dance phase requires the native source canvas")
    # Only these inspected cels leave the whole small lyric box unoccupied.
    x0, y0, x1, y1 = CLEAR_REGION
    output[y0:y1, x0:x1] = source[y0:y1, x0:x1]
    mask[y0:y1, x0:x1] = 255
    return output, mask


def warm_glyph_core(bgr: np.ndarray) -> np.ndarray:
    h, s, v = cv2.split(cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV))
    signed = bgr.astype(np.int16)
    # The pale pink stars have B >= G; the original cream letters have G > B.
    return ((h >= 5) & (h <= 43) & (s < 65) & (v > 220)
            & (signed[..., 1] > signed[..., 0] + 2))


def extract_dance_caption_layer(source: np.ndarray, phase_donors=(),
                                region=REGION, line_core_rows=LINE_CORE_ROWS) -> dict:
    if source.shape[:2] != CANVAS_SHAPE:
        raise ValueError("Dance caption donor must be the native 1920x1080 frame")
    x0, y0, x1, y1 = region
    crop = source[y0:y1, x0:x1]
    core = warm_glyph_core(crop)
    line_rows = np.zeros(core.shape, bool)
    for start, end in line_core_rows:
        line_rows[start-y0:end-y0] = True
    core &= line_rows
    if phase_donors:
        votes = core.astype(np.uint8)
        for donor in phase_donors:
            if donor.shape != source.shape:
                raise ValueError("Phase donors must have the same native canvas")
            votes += (warm_glyph_core(donor[y0:y1, x0:x1]) & line_rows)
        core &= votes >= 2
    if np.count_nonzero(core) < 1000:
        raise ValueError("Missing cream glyphs in the registered caption donor")
    extent = cv2.dilate(core.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0
    # The star under the Japanese line prevents a flat-purple alpha fit.
    # This local plate and AA are reconstructed, not source-observed hidden pixels.
    plate = cv2.inpaint(crop, extent.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
    bright = core & (crop[..., 1] > 218) & (crop[..., 2] > 230)
    foreground = np.median(crop[bright], axis=0).astype(np.float32)
    source_float, plate_float = crop.astype(np.float32), plate.astype(np.float32)
    direction = foreground - plate_float
    alpha = np.clip(np.sum((source_float - plate_float) * direction, axis=2)
                    / np.maximum(np.sum(direction * direction, axis=2), 1), 0, 1)
    alpha[~extent | (alpha < 0.035)] = 0
    # Opaque source glyph cores remain opaque despite compressed donor noise.
    alpha[core] = np.maximum(alpha[core], 0.9)
    return {"alpha": alpha.astype(np.float32), "foreground_bgr": foreground,
            "source_core": core, "extent": extent, "estimated_plate_bgr": plate,
            "reconstruction": "phase-filtered warm core, local inpaint plate, projected AA, constant observed cream foreground"}


@lru_cache(maxsize=1)
def dance_caption_layer() -> dict:
    donor = cv2.imread(str(DONOR), cv2.IMREAD_COLOR)
    if donor is None:
        raise FileNotFoundError(DONOR)
    phase_donors = [cv2.imread(str(path), cv2.IMREAD_COLOR) for path in PHASE_DONORS]
    if any(image is None for image in phase_donors):
        raise FileNotFoundError("Missing source glyph-phase donor")
    layer = extract_dance_caption_layer(donor, phase_donors)
    layer["donor_sha256"] = hashlib.sha256(DONOR.read_bytes()).hexdigest()
    layer["phase_donor_sha256"] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                   for path in PHASE_DONORS}
    return layer


@lru_cache(maxsize=1)
def night_caption_layer() -> dict:
    donor = cv2.imread(str(NIGHT_DONOR), cv2.IMREAD_COLOR)
    if donor is None:
        raise FileNotFoundError(NIGHT_DONOR)
    phase_donors = [cv2.imread(str(path), cv2.IMREAD_COLOR) for path in NIGHT_PHASE_DONORS]
    if any(image is None for image in phase_donors):
        raise FileNotFoundError("Missing source night-caption phase donor")
    layer = extract_dance_caption_layer(donor, phase_donors, NIGHT_REGION)
    visible_glyph = (layer["alpha"] >= 0.1).astype(np.uint8)
    layer["contrast_edge_support"] = ((cv2.dilate(visible_glyph, np.ones((3, 3), np.uint8)) != 0)
                                        & (visible_glyph == 0))
    layer["contrast_edge_bgr"] = np.array((54, 45, 65), np.uint8)
    layer["contrast_edge_policy"] = "Fixed 1px dark edge only on edited low-contrast bright underlay; glyph contents/core RGB unchanged"
    layer["donor_sha256"] = hashlib.sha256(NIGHT_DONOR.read_bytes()).hexdigest()
    layer["phase_donor_sha256"] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                   for path in NIGHT_PHASE_DONORS}
    return layer


def registered_caption(frame):
    if frame is not None and SOURCE_INTERVAL[0] <= frame < SOURCE_INTERVAL[1]:
        return REGION, dance_caption_layer(), False
    if frame is not None and NIGHT_INTERVAL[0] <= frame < NIGHT_INTERVAL[1]:
        return NIGHT_REGION, night_caption_layer(), True
    return None


def dance_caption_extent(frame: int | None, shape=CANVAS_SHAPE) -> np.ndarray:
    mask = np.zeros(shape, np.uint8)
    registered = registered_caption(frame)
    if registered is None:
        return mask
    if tuple(shape) != CANVAS_SHAPE:
        raise ValueError("Dance caption compositor requires the native source canvas")
    region, layer, has_contrast_edge = registered
    x0, y0, x1, y1 = region
    extent = layer["extent"]
    if has_contrast_edge:
        extent = extent | layer["contrast_edge_support"]
    mask[y0:y1, x0:x1][extent] = 255
    return mask


def restore_dance_captions(output: np.ndarray, source: np.ndarray,
                           frame: int | None, character_mask=None) -> tuple[np.ndarray, np.ndarray]:
    mask = np.zeros(source.shape[:2], np.uint8)
    registered = registered_caption(frame)
    if registered is None:
        return output, mask
    if output.shape != source.shape or source.shape[:2] != CANVAS_SHAPE:
        raise ValueError("Dance caption frames must share the native source canvas")
    region, layer, strict_observed_color = registered
    x0, y0, x1, y1 = region
    alpha = layer["alpha"]
    target = output[y0:y1, x0:x1]
    original = source[y0:y1, x0:x1]
    # Leave untouched source glyphs alone: painting them twice thickens the AA.
    edited = np.any(target != original, axis=2)
    paint = (alpha > 0) & edited
    contrast_edge = np.zeros(alpha.shape, bool)
    if strict_observed_color and character_mask is not None:
        if character_mask.shape != source.shape[:2]:
            raise ValueError("Caption contrast-edge character mask must use the native canvas")
        # New pale Klee hair can erase cream text contrast; no source pixels are pasted here.
        luminance = target.astype(np.float32) @ np.array((0.114, 0.587, 0.299), np.float32)
        foreground_luminance = layer["foreground_bgr"] @ np.array((0.114, 0.587, 0.299), np.float32)
        color_gap = np.max(np.abs(target.astype(np.float32) - layer["foreground_bgr"]), axis=2)
        low_contrast = (np.abs(luminance - foreground_luminance) < 38) & (color_gap < 60)
        new_character = character_mask[y0:y1, x0:x1] != 0
        contrast_edge = layer["contrast_edge_support"] & edited & low_contrast & new_character
        target[contrast_edge] = layer["contrast_edge_bgr"]
    blended = (alpha[..., None] * layer["foreground_bgr"]
               + (1 - alpha[..., None]) * target.astype(np.float32))
    target[paint] = np.clip(np.rint(blended[paint]), 0, 255).astype(np.uint8)
    # Observed current glyph cores need no color reconstruction; never expand support.
    observed_core = paint & layer["source_core"] & warm_glyph_core(original)
    if strict_observed_color:
        # Warm foreground-face pixels are not glyphs, even at registered glyph locations.
        color_delta = np.max(np.abs(original.astype(np.float32) - layer["foreground_bgr"]), axis=2)
        observed_core &= color_delta <= 25
    target[observed_core] = original[observed_core]
    mask[y0:y1, x0:x1][paint | contrast_edge] = 255
    return output, mask
