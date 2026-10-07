"""Sequential native source and limited existing-composite caption evidence."""

import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from compose import compose, read_image

INTERVAL = (911, 1008)
EVIDENCE_REGION = (450, 938, 1470, 1056)
BASELINE_FRAMES = (911, 919, 927, 938, 948, 963)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bgrdigest(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def main():
    cv2.setNumThreads(2)
    native = OUT / "source"
    baseline = OUT / "baseline"
    native.mkdir(parents=True, exist_ok=True)
    baseline.mkdir(exist_ok=True)
    meta = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    if digest(meta["source"]) != meta["sha256"]:
        raise ValueError("Source video hash changed")
    cap = cv2.VideoCapture(meta["source"])
    images = {}
    records = []
    try:
        for frame in range(INTERVAL[0]):
            if not cap.grab():
                raise ValueError(f"Source ended before f{frame}")
        for frame in range(*INTERVAL):
            ok, image = cap.read()
            if not ok or image.shape != (1080, 1920, 3):
                raise ValueError(f"Invalid native decode f{frame}")
            images[frame] = image
            file = native / f"f{frame:04d}.png"
            cv2.imwrite(str(file), image)
            ref = next((ROOT / "source_refs").glob(f"*-f{frame:04d}.png"), None)
            records.append({"source_frame": frame, "source_pts": meta["pts"][frame],
                            "source_bgr_sha256": bgrdigest(image), "source_png": str(file),
                            "source_png_sha256": digest(file),
                            "existing_reference": str(ref) if ref else None,
                            "existing_reference_sha256": digest(ref) if ref else None,
                            "source_equals_existing_reference": bool(np.array_equal(image, cv2.imread(str(ref)))) if ref else None})
    finally:
        cap.release()
    x0, y0, x1, y1 = EVIDENCE_REGION
    pages = []
    for start in range(INTERVAL[0], INTERVAL[1], 8):
        frames = list(range(start, min(start+8, INTERVAL[1])))
        page = Image.new("RGB", (x1-x0, (y1-y0+24)*len(frames)), "white")
        draw = ImageDraw.Draw(page)
        for i, frame in enumerate(frames):
            draw.text((6, i*(y1-y0+24)+5), f"f{frame:04d} ACTUAL NATIVE SOURCE CAPTION BAND", fill="black")
            page.paste(Image.fromarray(cv2.cvtColor(images[frame][y0:y1, x0:x1], cv2.COLOR_BGR2RGB)), (0, i*(y1-y0+24)+24))
        file = OUT / f"source-caption-page-{(start-INTERVAL[0])//8+1:02d}.png"
        page.save(file)
        pages.append({"path": str(file), "sha256": digest(file), "source_frames": frames})
    baseline_rows = []
    for frame in BASELINE_FRAMES:
        row = next(r for r in manifest["cels"] if r["canonical_source_frame"] == frame)
        selected = row.get("selected_asset")
        if not selected:
            continue
        asset = ROOT / selected["path"]
        reference = read_image(ROOT / row["source_reference"])
        generated = read_image(asset)
        output, _, masks = compose(images[frame], reference, generated,
                                   asset_source_frame=frame, asset_name=asset.name,
                                   current_frame=frame)
        full = baseline / f"f{frame:04d}-actual-composite.png"
        pair = baseline / f"f{frame:04d}-source-composite-caption.png"
        mask = baseline / f"f{frame:04d}-composition-masks.png"
        cv2.imwrite(str(full), output)
        cv2.imwrite(str(pair), np.concatenate((images[frame][y0:y1, x0:x1], output[y0:y1, x0:x1]), axis=1))
        cv2.imwrite(str(mask), masks)
        baseline_rows.append({"source_frame": frame, "asset": str(asset), "asset_sha256": digest(asset),
                              "output_bgr_sha256": bgrdigest(output), "composite_png": str(full),
                              "composite_sha256": digest(full), "caption_pair": str(pair),
                              "caption_pair_sha256": digest(pair), "masks": str(mask), "mask_sha256": digest(mask)})
    report = {"source_interval_half_open": INTERVAL, "actual_source_count": len(records),
              "source_video_sha256": meta["sha256"], "evidence_region_xyxy": EVIDENCE_REGION,
              "source_pages": pages, "rows": records, "baseline_composites": baseline_rows,
              "compose_baseline_sha256": digest(ROOT / "compose.py"),
              "phase_status": "unregistered_pending_actual_source_review",
              "artistic_acceptance": False, "original_speed_video_review": "not_performed"}
    file = OUT / "source-audit.json"
    file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(file), "actual_source_count": len(records),
                      "source_pages": len(pages), "baseline_count": len(baseline_rows),
                      "all_existing_refs_match": all(r["source_equals_existing_reference"] is not False for r in records)}, indent=2))


if __name__ == "__main__":
    main()
