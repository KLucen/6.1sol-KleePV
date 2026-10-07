"""Decode both outputs sequentially and record scoped evidence, not artwork approval."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
OUT = QA / "encoded-v2-evidence"
CAPTION_QA = ROOT / "qa/fast-fullpv-raised-caption-2026-10-04"
RECT = (780, 953, 1135, 1049)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    single = ROOT / "output/klee-raised-1225-1285-fast-draft-v2.mp4"
    compare = ROOT / "output/klee-raised-1225-1285-comparison-fast-draft-v2.mp4"
    a, b = cv2.VideoCapture(str(single)), cv2.VideoCapture(str(compare))
    rows, captions = [], []
    x0, y0, x1, y1 = RECT
    for frame in range(1225, 1285):
        oka, one = a.read()
        okb, two = b.read()
        if not oka or not okb or one.shape != (1080, 1920, 3) or two.shape != (1080, 3840, 3):
            raise ValueError(f"Wrong/missing frame{frame}")
        right = two[:, 1920:]
        raw_path = CAPTION_QA / "raw" / f"f{frame:04d}-composite.png"
        raw = cv2.imread(str(raw_path))
        if raw is None or raw.shape != one.shape:
            raise ValueError(f"Wrong raw composite{frame}")
        source_path = CAPTION_QA / "source" / f"f{frame:04d}.png"
        source = cv2.imread(str(source_path))
        masks = np.load(CAPTION_QA / "raw" / f"f{frame:04d}-caption-masks.npz")
        core = masks["source_core"]
        rc, oc, cc = raw[y0:y1, x0:x1], one[y0:y1, x0:x1], right[y0:y1, x0:x1]
        encoded_delta = np.abs(rc.astype(np.int16) - oc.astype(np.int16)).max(2)
        compare_delta = np.abs(cc.astype(np.int16) - oc.astype(np.int16)).max(2)
        rows.append({"source_frame": frame, "raw_sha256": sha(raw_path),
                     "single_comparison_right_full_RGB_max_delta": int(np.abs(one.astype(np.int16) - right.astype(np.int16)).max()),
                     "single_comparison_right_caption_RGB_max_delta": int(compare_delta.max()),
                     "raw_single_core_RGB_max_delta": int(encoded_delta[core].max()),
                     "raw_single_core_RGB_mean_maxchannel_delta": float(encoded_delta[core].mean()),
                     "raw_single_core_delta_gt20_pixels": int((core & (encoded_delta > 20)).sum()),
                     "source_core_pixels": int(core.sum()),
                     "comparison_left_source_full_RGB_max_delta": int(np.abs(source.astype(np.int16)-two[:, :1920].astype(np.int16)).max()),
                     "numeric_scope": "Lossy encode diagnostics only; no threshold-based artistic acceptance"})
        pair = np.concatenate([one[944:1052, 780:1135], right[944:1052, 780:1135]], 1)
        path = OUT / f"f{frame:04d}-single-comparison-right-caption.png"
        cv2.imwrite(str(path), pair)
        captions.append((frame, pair))
    if a.read()[0] or b.read()[0]:
        raise ValueError("Unexpected extra encoded frame")
    a.release()
    b.release()
    pages = []
    for offset in range(0, 60, 8):
        page = Image.new("RGB", (710, 1120), "#202024")
        draw = ImageDraw.Draw(page)
        chunk = captions[offset:offset + 8]
        for i, (frame, pair) in enumerate(chunk):
            draw.text((8, i * 140 + 7), f"f{frame:04d} SINGLE | COMPARISON RIGHT (BOTH V2)", fill="white")
            page.paste(Image.fromarray(cv2.cvtColor(pair, cv2.COLOR_BGR2RGB)), (0, i * 140 + 28))
        path = OUT / f"comparison-caption-page-{offset // 8 + 1:02d}.png"
        page.save(path)
        pages.append({"path": str(path), "sha256": sha(path), "frames": [f for f, _ in chunk]})
    report = {"single_video": str(single), "single_sha256": sha(single), "comparison_video": str(compare),
              "comparison_sha256": sha(compare), "frames_sequentially_decoded_both": 60,
              "caption_core_region": RECT, "rows": rows, "comparison_caption_pages": pages,
              "max_single_comparison_right_caption_RGB_delta": max(r["single_comparison_right_caption_RGB_max_delta"] for r in rows),
              "max_raw_single_core_RGB_delta": max(r["raw_single_core_RGB_max_delta"] for r in rows),
              "original_speed_watch": "not_performed; frame decoding/contact review is not playback",
              "artistic_accepted": False}
    (OUT / "comparison-and-raw-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ["rows", "comparison_caption_pages"]}, indent=2))


if __name__ == "__main__":
    main()
