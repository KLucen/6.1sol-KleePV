"""Source-backed title backgrounds and shot-scoped character mattes.

Only explicitly registered title drafts use this path. Unobserved background
pixels need a separately identified reconstruction, never silent glyph reuse.
"""

from functools import lru_cache
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "title_layer_registry.json"


def phase(frame):
    if 1299 <= frame < 1403:
        return "title"
    return "plain" if frame < 1299 or frame >= 1497 else "credits"


def title_character_mask(image, margin=1):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hue, sat, val = cv2.split(hsv)
    seed = (val < 155) | ((hue < 17) & (sat > 65) & (val > 45))
    scoped = np.zeros(seed.shape, np.uint8)
    scoped[155:850, 680:1250] = seed[155:850, 680:1250]
    scoped = cv2.morphologyEx(scoped, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(scoped, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) > 10000]
    if len(contours) != 1:
        raise ValueError(f"Title character must have one main contour, found {len(contours)}")
    mask = np.zeros_like(scoped)
    cv2.drawContours(mask, contours, -1, 255, cv2.FILLED)
    return cv2.dilate(mask, np.ones((margin*2+1, margin*2+1), np.uint8))


@lru_cache(maxsize=1)
def registry():
    return json.loads(REGISTRY.read_text(encoding="utf-8")) if REGISTRY.exists() else {"assets": {}}


def read_canvas(path):
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Cannot decode title layer {path}")
    return cv2.resize(image, (1920, 1080), interpolation=cv2.INTER_LANCZOS4)


@lru_cache(maxsize=12)
def checked_layers(asset_name, shot_phase=None):
    row = registry()["assets"][asset_name]
    if shot_phase is not None and shot_phase != row["phase"]:
        variant = row.get("phase_variants", {}).get(shot_phase)
        if variant is None:
            raise ValueError(f"No registered {shot_phase} background for {asset_name}")
        row = {**row, **variant}
    for role in ("asset", "source_mask", "new_mask", "background", "background_known", "reconstructed", "reconstruction_asset", "provenance", "spatial_donor_x"):
        record = row[role]
        path = ROOT / record["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"Stale title-layer registration: {role} / {asset_name}")
    old = cv2.imread(str(ROOT / row["source_mask"]["path"]), cv2.IMREAD_GRAYSCALE)
    new = cv2.imread(str(ROOT / row["new_mask"]["path"]), cv2.IMREAD_GRAYSCALE)
    plate = read_canvas(ROOT / row["background"]["path"])
    known = cv2.imread(str(ROOT / row["background_known"]["path"]), cv2.IMREAD_GRAYSCALE)
    return row, old, new, plate, known


def compose_registered_title(source, generated, asset_source_frame, asset_name, transform, current_frame=None):
    if asset_name not in registry()["assets"]:
        return None
    row, old, new, plate, known = checked_layers(asset_name, phase(current_frame) if current_frame is not None else None)
    if row["source_frame"] != asset_source_frame or not np.allclose(transform, [[1, 0, 0], [0, 1, 0]]):
        raise ValueError("Registered title cel cannot silently change frame or camera transform")
    vacated = (old != 0) & (new == 0)
    unresolved = vacated & (known == 0)
    if np.any(unresolved):
        raise ValueError(f"Unobserved visible title background: {np.count_nonzero(unresolved)} pixels / {asset_name}")
    output = source.copy()
    output[vacated] = plate[vacated]
    output[new != 0] = generated[new != 0]
    diagnostic = np.concatenate([source, output], axis=1)
    masks = np.zeros_like(source)
    masks[old != 0] = (220, 90, 50)
    masks[new != 0] = (30, 160, 250)
    masks[vacated] = (80, 245, 90)
    return output, diagnostic, masks
