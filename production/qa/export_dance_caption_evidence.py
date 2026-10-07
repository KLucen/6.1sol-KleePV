"""Export native caption pairs and selected full composites, not new artwork."""

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compose import compose, read_image
from dance_caption_layers import CLEAR_REGION, REGION
from review_interval import caption_diagnostics
from review_opening_preview import file_hash


def main():
    cv2.setNumThreads(2)
    timeline_path = ROOT / "timeline-opening-36s958-draft-v8.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    out = ROOT / "qa/dance-caption-v8"
    out.mkdir(exist_ok=True)
    exposures = timeline["output_exposures"]
    panels = {"clear": [], "overlap": []}
    rows = []

    @lru_cache(maxsize=8)
    def load(cel):
        asset = timeline["assets"][cel]
        return read_image(ROOT / asset["source_reference"]), read_image(ROOT / asset["path"])

    cap = cv2.VideoCapture(timeline["source"])
    for _ in range(812):
        if not cap.grab():
            raise ValueError("Source ended before caption interval")
    index = 0
    while exposures[index]["end"] <= 812:
        index += 1
    try:
        for frame in range(812, 887):
            ok, source = cap.read()
            if not ok:
                raise ValueError(f"Source ended at {frame}")
            while exposures[index]["end"] <= frame:
                index += 1
            exposure = exposures[index]
            asset = timeline["assets"][exposure["cel"]]
            reference, generated = load(exposure["cel"])
            result, _, masks = compose(source, reference, generated, exposure["source_matrix"],
                                       asset["source_frame"], Path(asset["path"]).name, frame)
            phase, rect = ("clear", CLEAR_REGION) if frame < 831 else ("overlap", REGION)
            x0, y0, x1, y1 = rect
            pair = np.concatenate([source[y0:y1, x0:x1], result[y0:y1, x0:x1]], axis=1)
            native_path = out / f"f{frame:04d}-native-caption-pair.png"
            cv2.imwrite(str(native_path), pair)
            scale = 3 if phase == "clear" else 2
            enlarged = cv2.resize(pair, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
            panel = Image.new("RGB", (enlarged.shape[1], enlarged.shape[0]+24), "white")
            panel.paste(Image.fromarray(cv2.cvtColor(enlarged, cv2.COLOR_BGR2RGB)), (0, 24))
            ImageDraw.Draw(panel).text((5, 5), f"f{frame:04d} ORIGINAL | COMPOSITE, nearest-neighbor detail", fill="black")
            panels[phase].append(panel)
            mismatch = int(np.count_nonzero(np.any(source != result, axis=2) & np.all(masks == 0, axis=2)))
            row = {"frame": frame, "asset": asset["path"], "decoded_source_sha256": hashlib.sha256(source.tobytes()).hexdigest(),
                   "native_caption_pair": str(native_path), "pair_sha256": file_hash(native_path),
                   "undeclared_changed_pixels": mismatch,
                   "caption_diagnostics": caption_diagnostics(source, result, frame)}
            if frame in (812, 814, 815, 819, 823, 827, 863, 868, 873, 880):
                full_path = out / f"f{frame:04d}-full-composite.png"
                cv2.imwrite(str(full_path), result)
                row["full_composite"] = str(full_path)
            rows.append(row)
    finally:
        cap.release()
    pages = {}
    for phase, phase_panels in panels.items():
        pages[phase] = []
        for start in range(0, len(phase_panels), 4):
            group = phase_panels[start:start+4]
            page = Image.new("RGB", (group[0].width, sum(panel.height for panel in group)), "white")
            top = 0
            for panel in group:
                page.paste(panel, (0, top))
                top += panel.height
            path = out / f"{phase}-caption-page-{start//4+1:02d}.png"
            page.save(path)
            pages[phase].append(str(path))
    report = {"source_interval": [812, 887], "decoded_frames": len(rows), "frames": rows,
              "pages": pages, "all_undeclared_pixels_zero": all(row["undeclared_changed_pixels"] == 0 for row in rows),
              "artistic_acceptance": False, "manual_review": "pending", "actual_speed_watch": "not_performed",
              "provenance": {str(path): file_hash(path) for path in (timeline_path, ROOT/"compose.py", ROOT/"dance_caption_layers.py", Path(__file__))}}
    path = out / "evidence.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "decoded_frames": len(rows), "pages": {key: len(value) for key, value in pages.items()}, "undeclared_pixels_zero": report["all_undeclared_pixels_zero"]}))


if __name__ == "__main__":
    main()
