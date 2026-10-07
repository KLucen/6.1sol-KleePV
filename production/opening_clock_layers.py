"""Copy only reviewed isolated source clocks, never pillows or held clocks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
SIZE = (1920, 1080)
SHAPE = (1080, 1920, 3)
IDENTITY = np.asarray([[1, 0, 0], [0, 1, 0]], dtype=np.float64)
OPENING_RECT = (854, 375, 1050, 533)
FLOATING_RECT = (866, 464, 1018, 624)
RECTANGLES = {
    (38, "candidate-001-clean.png"): OPENING_RECT,
    (38, "fine-f0038-eye-repair.png"): OPENING_RECT,
    (50, "fine-f0050.png"): OPENING_RECT,
    (54, "fine-f0054.png"): OPENING_RECT,
    **{(frame, f"fine-f{frame:04d}.png"): FLOATING_RECT
       for frame in (162, 167, 172, 176, 180, 185, 190, 194)},
    (176, "fine-f0176-hair-cuff-repair.png"): FLOATING_RECT,
    (185, "fine-f0185-hair-repair.png"): FLOATING_RECT,
    (167, "fine-f0167-sleeve-repair-v2.png"): FLOATING_RECT,
}
RELEASE_KEY = (157, "fine-f0157-glove-repair.png")
RELEASE_ASSET_SHA256 = "1ec40ef8df5c1999ececaa2bc963deec59355dbd2b75ae2eec27290ce548c1b7"
RELEASE_MASK_SHA256 = "71d23bdfe9ac32ec9d83f1a6c63b0b9d1f50ba7bd0e6378f7df4e0866058cbd4"
RELEASE_MASK_PATH = ROOT / "qa/opening-new-review/f0157-clock-mask-glove-guarded.png"
REVIEW_PATH = ROOT / "qa/opening-new-review/metrics.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_image(path):
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Cannot decode {path}")
    return cv2.resize(image, SIZE, interpolation=cv2.INTER_LANCZOS4)


def is_identity(transform):
    """None denotes the renderer's identity default; all nonidentity values fail."""
    if transform is None:
        return True
    try:
        value = np.asarray(transform, dtype=np.float64)
    except (TypeError, ValueError):
        return False
    return value.shape == IDENTITY.shape and np.array_equal(value, IDENTITY)


def released_clock_mask(generated):
    """The hand-contact mask is valid only for the exact reviewed generated cel."""
    asset = ROOT / "generated" / RELEASE_KEY[1]
    try:
        if sha256(asset) != RELEASE_ASSET_SHA256 or sha256(RELEASE_MASK_PATH) != RELEASE_MASK_SHA256:
            return None
        review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        recorded = next(e for e in review["assets"] if e["frame"] == RELEASE_KEY[0])
        if (Path(recorded["asset"]).name != RELEASE_KEY[1]
                or recorded["asset_sha256"] != RELEASE_ASSET_SHA256):
            return None
        if not np.array_equal(read_image(asset), generated):
            return None
        mask = cv2.imread(str(RELEASE_MASK_PATH), cv2.IMREAD_GRAYSCALE)
        if mask is None or mask.shape != SHAPE[:2] or not np.isin(mask, (0, 255)).all():
            return None
        return mask
    except (OSError, ValueError, KeyError, StopIteration, TypeError):
        return None


def restore_clock(output, source, generated_in_source_coordinates,
                  asset_source_frame, asset_name, transform):
    """Return a copied output and 0/255 mask, copying CURRENT source pixels.

    Arrays must be normalized uint8 BGR 1920x1080 canvases. Unknown pairs,
    unverified camera transforms and failed released-clock provenance are no-ops.
    The generated argument must be in the same source coordinates as output.
    This helper grants no artistic acceptance and never changes its input arrays.
    """
    for name, value in (("output", output), ("source", source),
                        ("generated", generated_in_source_coordinates)):
        if not isinstance(value, np.ndarray) or value.shape != SHAPE or value.dtype != np.uint8:
            raise ValueError(f"{name} must be a uint8 BGR 1920x1080 canvas")
    result = output.copy()
    mask = np.zeros(SHAPE[:2], np.uint8)
    if not is_identity(transform) or not isinstance(asset_source_frame, (int, np.integer)):
        return result, mask
    try:
        key = (int(asset_source_frame), Path(asset_name).name)
    except TypeError:
        return result, mask
    if key in RECTANGLES:
        x0, y0, x1, y1 = RECTANGLES[key]
        mask[y0:y1, x0:x1] = 255
    elif key == RELEASE_KEY:
        verified = released_clock_mask(generated_in_source_coordinates)
        if verified is None:
            return result, mask
        mask = verified.copy()
    else:
        return result, mask
    result[mask != 0] = source[mask != 0]
    return result, mask


def technical_audit(output_path):
    mapping = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    candidates = {c["frame"]: c for c in mapping["candidates"]}
    manifest = {"version": 1, "scope": "clock-only technical pixel-copy audit",
                "status": "technical_only_not_artistic_acceptance", "canvas": list(SIZE),
                "camera_policy": "exact 2x3 identity only; None is identity default",
                "input_policy": "same normalized source coordinates; current source pixels copied",
                "unsupported": ["held clocks", "pillow restoration", "old shifted frame-157 clock eraser",
                                "unknown filename/frame pairs", "nonidentity camera transforms"],
                "released_clock_provenance": {"asset_sha256": RELEASE_ASSET_SHA256,
                                               "mask_sha256": RELEASE_MASK_SHA256,
                                               "mask": str(RELEASE_MASK_PATH.relative_to(ROOT)),
                                               "geometry_reference_frame": 162,
                                               "pixels_reference": "current source frame, not mask-reference frame"},
                "assets": []}
    for frame, filename in [*RECTANGLES, RELEASE_KEY]:
        asset_path = ROOT / "generated" / filename
        source_path = ROOT / candidates[frame]["reference"]
        gen, src = read_image(asset_path), read_image(source_path)
        result, mask = restore_clock(gen, src, gen, frame, filename, IDENTITY)
        restore = mask != 0
        changed = np.any(result != gen, axis=2)
        entry = {"source_frame": frame, "asset": f"generated/{filename}",
                 "generated_sha256": sha256(asset_path), "source": candidates[frame]["reference"],
                 "source_sha256": sha256(source_path), "restored_pixels": int(np.count_nonzero(restore)),
                 "source_mismatch_inside_mask": int(np.count_nonzero(np.any(result != src, axis=2) & restore)),
                 "outside_mask_changed_pixels": int(np.count_nonzero(changed & ~restore)),
                 "rectangle": list(RECTANGLES[(frame,filename)]) if (frame,filename) in RECTANGLES else None}
        if frame == 157:
            hsv = cv2.cvtColor(gen, cv2.COLOR_BGR2HSV)
            h,s,v = cv2.split(hsv)
            brown = (h < 27) & (s > 75) & (v > 80) & (v < 190)
            guard = np.zeros(mask.shape,np.uint8)
            guard[450:570,985:1080] = brown[450:570,985:1080].astype(np.uint8)*255
            guard = cv2.dilate(guard,np.ones((5,5),np.uint8))
            entry["guarded_glove_mask_overlap_pixels"] = int(np.count_nonzero(restore & (guard != 0)))
            entry["glove_changed_pixels"] = int(np.count_nonzero(changed & (guard != 0)))
        manifest["assets"].append(entry)
    manifest["all_supported_pixel_copies_verified"] = all(
        e["restored_pixels"] > 0 and e["source_mismatch_inside_mask"] == 0
        and e["outside_mask_changed_pixels"] == 0 and e.get("glove_changed_pixels",0) == 0
        for e in manifest["assets"])
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps({"manifest": str(output_path), "assets": len(manifest["assets"]),
                      "all_supported_pixel_copies_verified": manifest["all_supported_pixel_copies_verified"]},indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-output",type=Path,
                        default=ROOT / "qa/opening-new-review/clock-layer-provenance.json")
    technical_audit(parser.parse_args().audit_output)
