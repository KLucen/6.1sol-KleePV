"""Private actual-exposure boundary evidence for the adopted back-view repair."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compose import compose, read_image

TARGET = ROOT / "qa" / "fast-fullpv-dance-backview-fragment-2026-10-04" / "fixed-v2"
ROI = (1125, 0, 1490, 285)


def green_mask(image):
    h, s, v = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
    mask = ((h >= 40) & (h < 90) & (s > 95) & (v > 80)).astype(np.uint8) * 255
    roi = np.zeros_like(mask)
    x0, y0, x1, y1 = ROI
    roi[y0:y1, x0:x1] = mask[y0:y1, x0:x1]
    return roi


def bounds(mask):
    yy, xx = np.nonzero(mask)
    return [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1] if len(xx) else None


def main():
    global TARGET
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-scoped", action="store_true")
    args = parser.parse_args()
    if args.final_scoped:
        TARGET = TARGET.parent / "final-scoped"
    cv2.setNumThreads(2)
    TARGET.mkdir(parents=True, exist_ok=True)
    timeline = json.loads((ROOT / "timeline-dance-812-911-fast-draft-v11.json").read_text())
    cap = cv2.VideoCapture(timeline["source"])
    sources = {}
    for frame in range(903):
        if 899 <= frame <= 902:
            ok, source = cap.read()
            if not ok:
                raise RuntimeError(f"Actual sequential source decode failed at {frame}")
            sources[frame] = source
        elif not cap.grab():
            raise RuntimeError(f"Actual sequential source decode failed at {frame}")
    cap.release()
    records = []
    boundary = []
    fragment_rows = []
    for frame, source in sources.items():
        exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = timeline["assets"][exposure["cel"]]
        generated = read_image(ROOT / asset["path"])
        output, _, _ = compose(source, source, generated, exposure.get("source_matrix"),
                               asset["source_frame"], Path(asset["path"]).name, frame)
        record = {"frame": frame, "asset": asset["path"], "exposure": [exposure["start"], exposure["end"]],
                  "review_state": exposure.get("review"), "accepted_by_this_check": False}
        if args.final_scoped:
            baseline = cv2.imread(str(TARGET.parent / "fixed-v2" / f"f{frame:04d}-composite-native.png"))
            declared_roi = np.zeros(source.shape[:2], bool)
            x0, y0, x1, y1 = ROI
            declared_roi[y0:y1, x0:x1] = True
            changed = np.any(output != baseline, axis=2)
            record["changed_pixels_vs_unscoped_v2"] = int(np.count_nonzero(changed))
            record["changed_outside_checked_roi"] = int(np.count_nonzero(changed & ~declared_roi))
            record["unchanged_adjacent_exposure"] = bool(np.array_equal(output, baseline)) if frame in (899, 902) else None
            if frame in (900, 901):
                h, s, v = cv2.split(cv2.cvtColor(source, cv2.COLOR_BGR2HSV))
                fringe = (declared_roi & (h >= 40) & (h < 101) & (s > 90) & (v > 80)
                          & np.all(source == output, axis=2)
                          & (np.max(np.abs(source.astype(int) - generated.astype(int)), axis=2) > 8))
                record["source_exact_greenish_threshold_pixels"] = int(np.count_nonzero(fringe))
                record["threshold_limit"] = "Color threshold also selects the original sky star at [1466,34,1470,38]; not anatomy evidence alone"
        crops = []
        for name, image in (("source", source), ("generated", generated), ("composite", output)):
            record[f"{name}_bgr_sha256"] = hashlib.sha256(image.tobytes()).hexdigest()
            cv2.imwrite(str(TARGET / f"f{frame:04d}-{name}-native.png"), image)
            x0, y0, x1, y1 = ROI
            crop = image[y0:y1, x0:x1]
            cv2.imwrite(str(TARGET / f"f{frame:04d}-{name}-fragment-native.png"), crop)
            crops.append(crop)
            if frame in (900, 901):
                mask = green_mask(image)
                record[f"{name}_old_green_pixels"] = int(np.count_nonzero(mask))
                record[f"{name}_old_green_bounds"] = bounds(mask)
                cv2.imwrite(str(TARGET / f"f{frame:04d}-{name}-old-green-mask.png"), mask)
        fragment_rows.append(np.concatenate(crops, axis=1))
        boundary.append(cv2.resize(output, (960, 540), interpolation=cv2.INTER_AREA))
        records.append(record)
        print(json.dumps(record), flush=True)
    cv2.imwrite(str(TARGET / "source-generated-composite-fragment-boundary-contact.png"),
                np.concatenate(fragment_rows, axis=0))
    cv2.imwrite(str(TARGET / "f0899-f0900-f0901-f0902-composite-boundary-contact.jpg"),
                np.concatenate((np.concatenate(boundary[:2], axis=1), np.concatenate(boundary[2:], axis=1)), axis=0))
    (TARGET / "actual-fixed-v2-boundary-evidence.json").write_text(json.dumps({
        "timeline": "timeline-dance-812-911-fast-draft-v11.json", "source": timeline["source"],
        "sequential_decode": [0, 902], "crop_roi_xyxy": ROI, "records": records,
        "scope": "Back-view repair900/901 with adjacent899/902 inspection only",
        "inspection": "pending_actual_native_review", "art_acceptance": False}, indent=2))


if __name__ == "__main__":
    main()
