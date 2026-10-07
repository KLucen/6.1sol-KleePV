"""Bounded evidence for the full-batch cyan matte classification correction."""

import json
from pathlib import Path
import shutil
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compose import compose, read_image
from cyan_profile_layers import cyan_subject_mask
from cyan_layers_batch2_audit import OUT, exposure_map, digest, save_json


def main():
    cv2.setNumThreads(2)
    baseline = OUT / "raw-initial-full-batch"
    if not baseline.exists():
        baseline.mkdir()
        shutil.copytree(OUT / "raw-final-batch", baseline / "native")
        for path in OUT.glob("raw-final-batch-*.png"):
            shutil.copy2(path, baseline / path.name)
        for name in ("raw-final-batch-audit.json", "raw-layer-freeze.json"):
            shutil.copy2(OUT / name, baseline / name)
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    exposures = exposure_map(manifest)
    folder = OUT / "matte-refinement"
    folder.mkdir(exist_ok=True)
    rows = []
    for frame in (921, 925, 930, 933, 934, 935, 936, 937, 938, 967, 968, 976, 977, 978, 979, 984):
        row, exposure = exposures[frame]
        asset = ROOT / row["selected_asset"]["path"]
        source = cv2.imread(str(OUT / "actual-source" / f"f{frame:04d}.png"))
        art = read_image(asset)
        matte = cyan_subject_mask(art, frame, asset.name)
        matrix = exposure["source_transform"]["matrix"]
        output, _, _ = compose(source, read_image(ROOT / row["source_reference"]), art,
                               matrix, row["selected_asset"]["source_frame"], asset.name, frame)
        before = cv2.imread(str(baseline / "native" / f"f{frame:04d}-composite.png"))
        cv2.imwrite(str(folder / f"f{frame:04d}-composite.png"), output)
        cv2.imwrite(str(folder / f"f{frame:04d}-generated-matte.png"), matte)
        if frame in (933, 935, 967):
            contact = cv2.vconcat([cv2.hconcat([source, art]), cv2.hconcat([before, output])])
            cv2.imwrite(str(folder / f"f{frame:04d}-source-art-before-after-native.png"), contact)
        rows.append({"source_frame": frame, "changed_pixels": int(np.any(before != output, axis=2).sum()),
                     "asset": str(asset), "asset_sha256": digest(asset)})
    save_json(folder / "bounded-recomposition.json", {"frames": rows,
              "cause": "Generated S>=110 exterior flood entered pale blue hair in fine-f0933 and fine-f0935-repair. Generated threshold now S>=160; detached tiny bright generated star islands are excluded. Source green ink is included from observed HSV support.",
              "static_technical_only": True, "artistic_acceptance": False})
    print(json.dumps({"frames": len(rows), "folder": str(folder)}))


if __name__ == "__main__":
    main()
