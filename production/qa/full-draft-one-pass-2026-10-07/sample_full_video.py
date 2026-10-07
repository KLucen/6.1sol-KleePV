"""Extract diagnostics from an encoded master; never recomposite artwork."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CENTERS = (1037, 1129, 1144, 2145, 2163, 3235, 3259)
OVERVIEW = (0, 500, 1502, 2401, 3000, 3470, 3657)
CAPTION_ROI = (600, 920, 1320, 1080)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def decode_selected(path, wanted, destination, prefix):
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot decode {path}")
    frames = {}
    try:
        index = 0
        last = max(wanted)
        while index <= last:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode frame {index} of {path}")
            if index in wanted:
                if frame.shape != (1080, 1920, 3):
                    raise ValueError(f"Unexpected native frame dimensions: {frame.shape}")
                target = destination / f"{prefix}-f{index:04d}.png"
                if not cv2.imwrite(str(target), frame):
                    raise RuntimeError(f"Cannot save {target}")
                frames[index] = {"path": str(target), "png_sha256": sha256(target.read_bytes()).hexdigest(),
                                 "decoded_rgb_sha256": sha256(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).tobytes()).hexdigest()}
            index += 1
    finally:
        capture.release()
    return frames


def panel(frames, source, draft, roi=None):
    rows = []
    for label, records in (("SOURCE", source), ("ENCODED DRAFT", draft)):
        cells = []
        for frame in frames:
            image = cv2.imread(records[frame]["path"])
            if roi:
                x1, y1, x2, y2 = roi
                image = image[y1:y2, x1:x2]
            else:
                image = cv2.resize(image, (480, 270), interpolation=cv2.INTER_AREA)
            bar = np.full((28, image.shape[1], 3), 30, np.uint8)
            cv2.putText(bar, f"{label} f{frame:04d}", (8, 19), cv2.FONT_HERSHEY_SIMPLEX, .5, (240, 240, 240), 1)
            cells.append(np.vstack((bar, image)))
        rows.append(np.hstack(cells))
    return np.vstack(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, default=ROOT / "output/klee-full-oct7-draft-v1.mp4")
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    cv2.setNumThreads(2)
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    wanted = sorted({frame for center in CENTERS for frame in (center-1, center, center+1)} | set(OVERVIEW))
    plan = {
        "snapshot_utc": datetime.now(timezone.utc).isoformat(),
        "master": str(args.video.resolve()),
        "source": metadata["source"],
        "expected_master_frames": len(metadata["pts"]),
        "expected_canvas": [1920, 1080],
        "continuous_centers": list(CENTERS),
        "continuous_groups": [[center-1, center, center+1] for center in CENTERS],
        "overview_frames": list(OVERVIEW),
        "requested_frames": wanted,
        "source_pts_seconds": {str(frame): metadata["pts"][frame] for frame in wanted},
        "caption_crop_xyxy": list(CAPTION_ROI),
        "decode_method": "Sequential native encoded-frame decode, no approximate time seeking",
        "status": "prepared_not_sampled",
        "encoded_video_observed": False,
        "artistic_acceptance": "not_performed",
        "shared_selection_changed": False,
        "artwork_recomposited": False,
    }
    write_json(HERE / "encoded-sampling-plan.json", plan)
    if args.prepare or not args.video.is_file():
        if not args.prepare:
            plan["status"] = "master_missing_not_sampled"
            write_json(HERE / "encoded-sampling-plan.json", plan)
        print(json.dumps({"status": plan["status"], "master_exists": args.video.is_file(),
                          "requested_frames": len(wanted), "encoded_video_observed": False}))
        return
    destination = HERE / "encoded-samples"
    destination.mkdir(exist_ok=True)
    source = decode_selected(Path(metadata["source"]), set(wanted), destination, "source")
    draft = decode_selected(args.video, set(wanted), destination, "draft")
    groups = []
    for center in CENTERS:
        frames = (center-1, center, center+1)
        paths = {}
        for name, roi in (("full-strip", None), ("caption-native-strip", CAPTION_ROI)):
            path = destination / f"f{center:04d}-{name}.png"
            if not cv2.imwrite(str(path), panel(frames, source, draft, roi)):
                raise RuntimeError(f"Cannot save {path}")
            paths[name] = str(path)
        groups.append({"center": center, "frames": list(frames), "panels": paths,
                       "human_or_agent_visual_review": "pending"})
    report = dict(plan)
    report.update({"status": "encoded_samples_extracted_visual_review_pending",
                   "encoded_video_observed": "decoded_pixels_only_not_visual_acceptance",
                   "master_sha256": sha256(args.video.read_bytes()).hexdigest(),
                   "source_samples": source, "draft_samples": draft, "continuous_panels": groups})
    write_json(HERE / "encoded-sampling-report.json", report)
    print(json.dumps({"status": report["status"], "frames_per_video": len(wanted),
                      "continuous_strips": len(groups), "report": str(HERE / "encoded-sampling-report.json")}))


if __name__ == "__main__":
    main()
