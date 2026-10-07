"""Reconstruct a complete Chinese line from inspected original f3402 glyphs."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "source_refs/src-1905-f3402.png"
REGION = (676, 954, 1213, 1047)
DONOR_REGION = (690, 1002, 1218, 1047)
TRANSLATION = (-15, 0)


def main():
    destination = HERE / "long-f3402-cn-clear-real-caption-v2.npz"
    if destination.exists():
        raise FileExistsError("Retain the saved donor layer")
    image = cv2.imread(str(SOURCE))
    x0, y0, x1, y1 = DONOR_REGION
    donor = image[y0:y1, x0:x1]
    b, g, r = cv2.split(donor.astype(np.int16))
    rows = np.zeros(donor.shape[:2], bool)
    rows[4:39] = True
    outline = rows & (b >= 155) & (g >= 185) & (r >= 210)
    core = rows & (b >= 194) & (g >= 215) & (r >= 230)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(outline.astype(np.uint8), 8)
    outline = np.isin(labels, [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= 3])
    core &= outline
    extent = cv2.dilate(outline.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0
    foreground = np.median(donor[core], axis=0).astype(np.float32)
    plate = cv2.inpaint(donor, extent.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA).astype(np.float32)
    direction = foreground - plate
    alpha = np.clip(np.sum((donor.astype(np.float32) - plate) * direction, axis=2)
                    / np.maximum(np.sum(direction * direction, axis=2), 1), 0, 1)
    alpha[~extent | (alpha < .04) | (g < 180) | (r < 208)] = 0
    alpha[outline] = np.maximum(alpha[outline], .85)
    alpha[core] = 1
    with np.load(HERE / "long-combined-before-v2.npz") as data:
        layer = {key: data[key].copy() for key in data.files}
    layer["region"] = np.array(REGION)
    dst_alpha = layer["alpha"]
    dst_ink = layer["ink_rgb"]
    cn_start = y0 - REGION[1]
    dst_alpha[cn_start:] = 0
    layer["core"][cn_start:] = False
    layer["extent"][cn_start:] = False
    offset = x0 + TRANSLATION[0] - REGION[0]
    assert offset == -1
    # The first donor column is background, as confirmed by the native crop.
    assert not np.any(alpha[:, :1])
    dst_alpha[cn_start:, :alpha.shape[1] - 1] = alpha[:, 1:]
    dst_ink[cn_start:, :alpha.shape[1] - 1] = foreground
    layer["extent"][cn_start:, :alpha.shape[1] - 1] = extent[:, 1:]
    visible = dst_alpha > .1
    layer["contrast_ring"] = (cv2.dilate(visible.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0) & ~visible
    np.savez_compressed(destination, **layer)
    glyphs = np.rint(dst_alpha[..., None] * dst_ink).clip(0, 255).astype(np.uint8)
    cv2.imwrite(str(HERE / "v2-long-glyphs-native.png"), glyphs)
    cv2.imwrite(str(HERE / "v2-cn-alpha-native.png"), np.rint(dst_alpha[cn_start:] * 255).astype(np.uint8))
    cv2.imwrite(str(HERE / "f3402-cn-exact-donor.png"), donor)
    report = {
        "accepted": False,
        "authorization": "允许先重建清晰字幕，看片后再指定返工",
        "interval": [1043, 1144],
        "source": str(SOURCE),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "original_chinese": "深爱着 把寂寞两人各分一半",
        "donor_region": DONOR_REGION,
        "integer_translation": TRANSLATION,
        "destination_region": REGION,
        "registration": {"basis": "clear left Chinese phrase only, excluding cream original cuff",
                         "best_dice": .850910957146523, "next_dx": -16, "next_dice": .8016401845207586},
        "layer_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "method": "Full same-phrase original donor; estimated AA from real pale pixels and inpainted donor plate; integer translation only. No AI text, scaling, or invented glyph strokes.",
        "japanese": "unchanged authorized f3402 alternate",
        "observed_current_source_core": "Chinese disabled; cream original cuff is not a glyph oracle",
        "review": "pending native viewing",
    }
    (HERE / "long-cn-provenance-v2.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
