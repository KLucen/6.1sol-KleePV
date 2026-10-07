"""Sequential source/encoded caption evidence; no artwork or shared rules edits."""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
START, END = 1225, 1285
RECT = (780, 944, 1135, 1052)
CANONICAL = [1225, 1229, 1234, 1241, 1248, 1256, 1261, 1264, 1267,
             1270, 1274, 1278, 1282]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", choices=["v1", "v2"], default="v1")
    args = parser.parse_args()
    out = HERE / f"encoded-{args.version}-evidence"
    out.mkdir(exist_ok=True)
    timeline = ROOT / "timeline-raised-1225-1285-fast-draft-v1.json"
    data = json.loads(timeline.read_text(encoding="utf-8"))
    video = ROOT / "output" / f"klee-raised-1225-1285-fast-draft-{args.version}.mp4"
    source_cap = cv2.VideoCapture(data["source"])
    encoded_cap = cv2.VideoCapture(str(video))
    for frame in range(START):
        if not source_cap.grab():
            raise ValueError(f"Source ended before {frame}")
    rows = []
    pairs = []
    x0, y0, x1, y1 = RECT
    for frame in range(START, END):
        oks, source = source_cap.read()
        oke, encoded = encoded_cap.read()
        if not oks or not oke or source.shape != (1080, 1920, 3) or encoded.shape != source.shape:
            raise ValueError(f"Missing/wrong decoded frame {frame}")
        a, b = source[y0:y1, x0:x1], encoded[y0:y1, x0:x1]
        pair = np.concatenate([a, b], axis=1)
        native = out / f"f{frame:04d}-source-encoded-caption.png"
        cv2.imwrite(str(native), pair)
        pairs.append((frame, pair))
        full_paths = []
        if frame in CANONICAL or frame == END - 1:
            for label, image in (("source", source), ("encoded", encoded)):
                full = out / f"f{frame:04d}-{label}.png"
                cv2.imwrite(str(full), image)
                full_paths.append(str(full))
        hsv = cv2.cvtColor(a, cv2.COLOR_BGR2HSV)
        warm = (hsv[..., 0] >= 5) & (hsv[..., 0] <= 43) & (hsv[..., 1] < 65) & (hsv[..., 2] > 220)
        warm &= a[..., 1].astype(int) > a[..., 0].astype(int) + 2
        diff = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
        rows.append({"source_frame": frame, "caption_pair": str(native),
                     "caption_pair_sha256": sha(native), "full_paths": full_paths,
                     "source_frame_BGR_sha256": hashlib.sha256(source.tobytes()).hexdigest(),
                     "source_warm_candidate_pixels": int(warm.sum()),
                     "source_warm_candidate_RGB_delta_gt30": int((warm & (diff > 30)).sum()),
                     "diagnostic_scope": "Warm candidates may include original clothing; not validated glyph cores or artistic acceptance"})
    if encoded_cap.read()[0]:
        raise ValueError("Encoded clip contains extra frames")
    source_cap.release()
    encoded_cap.release()
    pages = []
    for offset in range(0, len(pairs), 8):
        chunk = pairs[offset:offset + 8]
        page = Image.new("RGB", (710, 8 * 140), "#202024")
        draw = ImageDraw.Draw(page)
        for i, (frame, pair) in enumerate(chunk):
            status = "BLOCKED BASELINE" if args.version == "v1" else "CORRECTED DRAFT, UNACCEPTED"
            draw.text((8, i * 140 + 7), f"f{frame:04d} SOURCE | ENCODED KLEE {args.version.upper()} ({status})", fill="white")
            page.paste(Image.fromarray(cv2.cvtColor(pair, cv2.COLOR_BGR2RGB)), (0, i * 140 + 28))
        path = out / f"caption-page-{offset // 8 + 1:02d}.png"
        page.save(path)
        pages.append({"path": str(path), "sha256": sha(path), "frames": [f for f, _ in chunk]})
    report = {"source_interval": [START, END], "sequential_source_and_encoded_frames": 60,
              "source": data["source"], "video": str(video), "video_sha256": sha(video),
              "timeline_sha256": sha(timeline), "caption_rect": list(RECT),
              "native_source_encoded_pairs": 60, "pages": pages, "frames": rows,
              "artistic_acceptance": False, "manual_review": "pending_separate_record",
              "original_speed_watch": "not_performed", "status": "blocked_baseline_evidence" if args.version == "v1" else "corrected_draft_evidence_pending_review"}
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"frames": 60, "caption_pages": len(pages), "report": str(out / "report.json")}))


if __name__ == "__main__":
    main()
