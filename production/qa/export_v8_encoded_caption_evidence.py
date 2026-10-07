"""Sequential encoded/source caption comparison with explicit limited metrics."""

import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dance_caption_layers import CLEAR_REGION, REGION, dance_caption_layer, warm_glyph_core
from review_opening_preview import file_hash


def main():
    cv2.setNumThreads(2)
    video = ROOT / "output/klee-opening-36s958-draft-v8.mp4"
    metadata = json.loads((ROOT/"source_meta.json").read_text(encoding="utf-8"))
    source_path = Path(metadata["source"])
    if file_hash(source_path) != metadata["sha256"]:
        raise ValueError("Source identity changed")
    out = ROOT / "qa/opening-v8-encoded-caption-evidence"
    out.mkdir(exist_ok=True)
    source_cap, encoded_cap = cv2.VideoCapture(str(source_path)), cv2.VideoCapture(str(video))
    if not source_cap.isOpened() or not encoded_cap.isOpened():
        raise ValueError("Cannot decode source/encoded video")
    panels, rows = {"clear": [], "overlap": []}, []
    samples = {290, 661, 812, 819, 823, 827, 830, 831, 835, 839, 843, 848,
               856, 862, 863, 868, 873, 880, 886}
    full_samples = []
    try:
        for frame in range(887):
            ok_source, source = source_cap.read()
            ok_encoded, encoded = encoded_cap.read()
            if not ok_source or not ok_encoded:
                raise ValueError(f"Source/encoded decode stopped at {frame}")
            if encoded.shape != (1080, 1920, 3):
                raise ValueError("Unexpected encoded canvas")
            if frame in samples:
                path = out/f"f{frame:04d}-encoded.png"
                cv2.imwrite(str(path), encoded)
                full_samples.append({"frame": frame, "path": str(path), "sha256": file_hash(path)})
            if frame < 812:
                continue
            phase, rect = ("clear", CLEAR_REGION) if frame < 831 else ("overlap", REGION)
            x0, y0, x1, y1 = rect
            original, result = source[y0:y1, x0:x1], encoded[y0:y1, x0:x1]
            core = warm_glyph_core(original)
            metric_scope = "Current warm-color candidates in source-exact raw small box, not OCR"
            if phase == "overlap":
                core &= dance_caption_layer()["source_core"]
                metric_scope = "Current warm core intersected with stable donor only; not complete glyphs"
            delta = np.max(cv2.absdiff(original, result), axis=2)
            pair = np.concatenate([original, result], axis=1)
            path = out/f"f{frame:04d}-source-encoded-caption-pair.png"
            cv2.imwrite(str(path), pair)
            rows.append({"frame": frame, "phase": phase, "rectangle": list(rect),
                         "decoded_source_sha256": hashlib.sha256(source.tobytes()).hexdigest(),
                         "decoded_encoded_sha256": hashlib.sha256(encoded.tobytes()).hexdigest(),
                         "metric_scope": metric_scope, "core_pixels": int(core.sum()),
                         "core_difference_gt30_pixels": int(np.count_nonzero(core & (delta > 30))),
                         "pair": str(path), "pair_sha256": file_hash(path)})
            scale = 3 if phase == "clear" else 2
            enlarged = cv2.resize(pair, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
            panel = Image.new("RGB", (enlarged.shape[1], enlarged.shape[0]+24), "white")
            panel.paste(Image.fromarray(cv2.cvtColor(enlarged, cv2.COLOR_BGR2RGB)), (0, 24))
            ImageDraw.Draw(panel).text((5, 5), f"f{frame:04d} ORIGINAL | ENCODED SINGLE V8", fill="black")
            panels[phase].append(panel)
        if encoded_cap.read()[0]:
            raise ValueError("Encoded video has extra frames")
    finally:
        source_cap.release()
        encoded_cap.release()
    pages = {}
    for phase, items in panels.items():
        pages[phase] = []
        for start in range(0, len(items), 4):
            group = items[start:start+4]
            page = Image.new("RGB", (group[0].width, sum(p.height for p in group)), "white")
            top = 0
            for panel in group:
                page.paste(panel, (0, top))
                top += panel.height
            path = out/f"{phase}-encoded-page-{start//4+1:02d}.png"
            page.save(path)
            pages[phase].append({"path": str(path), "sha256": file_hash(path)})
    report = {"encoded_video": str(video), "video_sha256": file_hash(video),
              "source": str(source_path), "source_sha256": metadata["sha256"],
              "sequential_decoded_video_frames": 887, "caption_interval": [812, 887],
              "caption_rows": rows, "full_samples": full_samples, "pages": pages,
              "maximum_core_difference_gt30_pixels": {phase: max(r["core_difference_gt30_pixels"] for r in rows if r["phase"] == phase) for phase in panels},
              "manual_review": "pending", "artistic_acceptance": False,
              "actual_speed_watch": "not_performed",
              "limitations": ["Encoded YUV/compression can change RGB; no encoded source-exact claim.",
                              "Stable donor and warm-color metrics cannot certify all glyphs or contrast.",
                              "Static images are not actual-speed artistic playback."]}
    target = out/"report.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(target), "frames": 887, "caption_frames": len(rows),
                      "max_core_delta_gt30": report["maximum_core_difference_gt30_pixels"]}))


if __name__ == "__main__":
    main()
