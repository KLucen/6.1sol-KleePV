"""Actual final comparison decode: all captions and observed failure locations."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT / "qa/middle-transition-layers-private-2026-10-06/v5-foreground-ownership-audit"
VIDEO = ROOT / "output/klee-middle-2121-2145-oct6-comparison-draft-v1.mp4"


def main():
    destination = HERE / "encoded24-check.json"
    if destination.exists():
        raise FileExistsError("Preserve encoded review evidence")
    cap = cv2.VideoCapture(str(VIDEO))
    rows, crop_rows, pages, figures = [], [], [], []
    for frame in range(2121, 2145):
        ok, comparison = cap.read()
        if not ok or comparison.shape != (1080, 3840, 3):
            raise RuntimeError(f"Invalid decoded comparison at f{frame}")
        source = cv2.imread(str(PRIVATE / "source" / f"f{frame:04d}.png"))
        raw = cv2.imread(str(PRIVATE / f"f{frame:04d}-private.png"))
        encoded = comparison[:, 1920:]
        rows.append({"source_frame": frame, "comparison_frame": frame-2121,
                     "raw_bgr_sha256": hashlib.sha256(raw.tobytes()).hexdigest(),
                     "encoded_right_bgr_sha256": hashlib.sha256(encoded.tobytes()).hexdigest(),
                     "whole_mean_absolute_error": float(np.abs(raw.astype(np.int16)-encoded.astype(np.int16)).mean()),
                     "caption_mean_absolute_error": float(np.abs(raw[950:1052, 695:1225].astype(np.int16)-encoded[950:1052, 695:1225].astype(np.int16)).mean())})
        row = np.full((127, 1590, 3), 248, np.uint8)
        cv2.putText(row, f"f{frame} SOURCE / RAW / ACTUAL ENCODED RIGHT", (6, 17), cv2.FONT_HERSHEY_SIMPLEX,
                    .5, (25, 25, 25), 1, cv2.LINE_AA)
        for column, image in enumerate((source, raw, encoded)):
            row[23:125, column*530:(column+1)*530] = image[950:1052, 695:1225]
        crop_rows.append(row)
        if len(crop_rows) == 8:
            path = HERE / f"encoded24-caption-native-page-{len(pages)+1:02d}.png"
            cv2.imwrite(str(path), np.concatenate(crop_rows, axis=0))
            pages.append(str(path.relative_to(ROOT)))
            crop_rows = []
        if frame in (2121, 2122, 2130, 2135, 2143):
            path = HERE / f"f{frame}-actual-encoded-right.png"
            cv2.imwrite(str(path), encoded)
            figures.append(str(path.relative_to(ROOT)))
        for target_frame, name, (x0, y0, x1, y1) in [
            (2135, "warm-head", (1080, 220, 1810, 935)),
            (2143, "cool-face", (1220, 320, 1580, 740)),
            (2122, "source-star-glove-edge", (1170, 585, 1370, 725))
        ]:
            if frame == target_frame:
                path = HERE / f"f{frame}-{name}-raw-encoded-native.png"
                cv2.imwrite(str(path), np.concatenate((raw[y0:y1, x0:x1], encoded[y0:y1, x0:x1]), axis=1))
                figures.append(str(path.relative_to(ROOT)))
    extra, _ = cap.read()
    cap.release()
    if extra:
        raise RuntimeError("Unexpected additional comparison frame")
    report = {"accepted": False, "frames_decoded": 24, "no_extra_frame": True,
              "source_interval": [2121, 2145], "video": str(VIDEO),
              "video_sha256": hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
              "rows": rows, "native_caption_pages": pages, "figure_and_failure_location_evidence": figures,
              "note": "Lossy codec RGB differences are measured, not called byte-exact source/effect recovery or artistic acceptance.",
              "native_static_review": "pending actual viewing", "actual_speed_review": "not performed"}
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"frames": 24, "caption_pages": pages, "figure_evidence": figures, "sha256": report["video_sha256"]}))


if __name__ == "__main__":
    main()
