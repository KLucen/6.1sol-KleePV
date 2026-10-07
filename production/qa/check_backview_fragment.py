"""Actual source/candidate/composite evidence for the two back-view frames."""

import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compose import compose, read_image

TARGET = ROOT / "qa" / "fast-fullpv-dance-backview-fragment-2026-10-04"
ROI = (1080, 0, 1530, 330)


def visible_old_anatomy(image):
    h, s, v = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
    green = (h >= 40) & (h < 90) & (s > 95) & (v > 80)
    cyan = (h >= 95) & (h <= 115) & (s >= 30) & (s <= 155) & (v > 210)
    selected = np.zeros(image.shape[:2], np.uint8)
    x0, y0, x1, y1 = ROI
    selected[y0:y1, x0:x1] = (green | cyan)[y0:y1, x0:x1].astype(np.uint8) * 255
    ys, xs = np.nonzero(selected)
    return selected, [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def main():
    cv2.setNumThreads(2)
    TARGET.mkdir(exist_ok=True)
    timeline = json.loads((ROOT / "timeline-dance-812-911-fast-draft-v10.json").read_text())
    cap = cv2.VideoCapture(timeline["source"])
    sources = {}
    for frame in range(902):
        if frame in (900, 901):
            ok, image = cap.read()
            if not ok:
                raise RuntimeError(f"Sequential decode failed at {frame}")
            sources[frame] = image
        elif not cap.grab():
            raise RuntimeError(f"Sequential decode failed at {frame}")
    cap.release()
    generated = read_image(ROOT / "generated" / "candidate-028-clean.png")
    records = []
    for frame, source in sources.items():
        output, _, _ = compose(source, source, generated, asset_source_frame=900,
                               asset_name="candidate-028-clean.png", current_frame=frame)
        columns = []
        record = {"frame": frame, "exposure": [900, 902], "asset": "generated/candidate-028-clean.png"}
        for name, image in (("source", source), ("generated", generated), ("current-composite", output)):
            mask, bounds = visible_old_anatomy(image)
            record[f"{name}_visible_old_core_bounds_xyxy"] = bounds
            record[f"{name}_bgr_sha256"] = hashlib.sha256(image.tobytes()).hexdigest()
            cv2.imwrite(str(TARGET / f"f{frame:04d}-{name}-native.png"), image)
            cv2.imwrite(str(TARGET / f"f{frame:04d}-{name}-old-cyan-green-core-mask.png"), mask)
            x0, y0, x1, y1 = ROI
            crop = image[y0:y1, x0:x1]
            cv2.imwrite(str(TARGET / f"f{frame:04d}-{name}-fragment-native.png"), crop)
            columns.append(cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST))
        cv2.imwrite(str(TARGET / f"f{frame:04d}-source-generated-composite-fragment-2x.png"),
                    np.concatenate(columns, axis=1))
        records.append(record)
        print(json.dumps(record), flush=True)
    (TARGET / "actual-fragment-evidence.json").write_text(json.dumps({
        "source": timeline["source"], "sequential_decode": [0, 901],
        "roi_xyxy": ROI, "bounds_definition": "Visible cyan/green anatomical core, not all compression fringe",
        "inspection": "pending_native_review", "records": records}, indent=2))


if __name__ == "__main__":
    main()
