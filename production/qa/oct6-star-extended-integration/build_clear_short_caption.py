"""Replace the weak short donor with the inspected clear original f2420 prefix."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLOSEUP = ROOT / "qa/closeup-layers-2026-10-06"
STANDING = ROOT / "qa/standing-layers-private-2026-10-05"
sys.path.insert(0, str(ROOT))


def main():
    destination = HERE / "short-f2420-clear-real-caption.npz"
    if destination.exists():
        raise FileExistsError("Retain the saved real donor layer")
    spec = importlib.util.spec_from_file_location("_clear_original_caption_builder", CLOSEUP / "build_caption_layers.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    line = builder.real_line(2420, (650, 954, 820, 992))
    with np.load(STANDING / "short-caption-f1161-real.npz") as data:
        layer = {key: data[key].copy() for key in data.files}
    alpha, core = layer["alpha"], layer["core"]
    ink = np.broadcast_to(layer["foreground"], (*alpha.shape, 3)).copy()
    alpha[:38] = 0
    core[:38] = False
    offset = 650 + 214 - int(layer["region"][0])
    alpha[:38, offset:offset+170] = line["alpha"]
    ink[:38, offset:offset+170] = line["foreground"]
    visible = alpha > .1
    ring = (cv2.dilate(visible.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0) & ~visible
    np.savez_compressed(destination, region=layer["region"], alpha=alpha,
                        core=core, ink_rgb=ink, contrast_ring=ring)
    donor = CLOSEUP / "source/f2420.png"
    report = {"accepted": False, "japanese_donor_frame": 2420,
              "japanese_donor_sha256": hashlib.sha256(donor.read_bytes()).hexdigest(),
              "japanese_source_region": [650, 954, 820, 992],
              "japanese_integer_translation": [214, 0], "interval": [1144, 1162],
              "chinese_donor": "unchanged real f1161 layer", "outline_radius": 2,
              "method": "Measured clear original glyph alpha only; no AI text or guessed strokes",
              "layer_sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
    (HERE / "clear-short-caption-provenance.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
