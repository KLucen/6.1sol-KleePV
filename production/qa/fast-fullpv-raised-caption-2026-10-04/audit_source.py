"""Native sequential source audit for the fixed raised-shot caption phase."""

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
from dance_caption_layers import warm_glyph_core

REGION = (780, 953, 1135, 1049)
ROWS = ((958, 991), (1005, 1043))
DONOR_FRAMES = (1225, 1229, 1241, 1256, 1261, 1282)
FOREGROUND = np.array((211, 223, 237), np.float32)


def cream_core(image):
    # Compression near the pink coat also makes genuine strokes have B >= G.
    return ((np.max(np.abs(image.astype(np.float32)-FOREGROUND), axis=2) <= 28)
            & (np.max(image, axis=2) > 220))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bgrsha(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def main():
    cv2.setNumThreads(2)
    OUT.mkdir(parents=True, exist_ok=True)
    native = OUT / "source"
    native.mkdir(exist_ok=True)
    meta = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    if sha(meta["source"]) != meta["sha256"]:
        raise ValueError("Source video hash mismatch")
    cap = cv2.VideoCapture(meta["source"])
    images = {}
    records = []
    try:
        for frame in range(1225):
            if not cap.grab():
                raise ValueError(f"Source ended at {frame}")
        for frame in range(1225, 1285):
            ok, image = cap.read()
            if not ok or image.shape != (1080, 1920, 3):
                raise ValueError(f"Native source decode failed at {frame}")
            file = native / f"f{frame:04d}.png"
            cv2.imwrite(str(file), image)
            images[frame] = image
            reference = next((ROOT / "source_refs").glob(f"*-f{frame:04d}.png"))
            records.append({"frame": frame, "source_pts": meta["pts"][frame],
                            "actual_source_bgr_sha256": bgrsha(image), "source_png": str(file),
                            "source_png_sha256": sha(file), "reference": str(reference),
                            "reference_sha256": sha(reference),
                            "actual_decode_equals_reference": bool(np.array_equal(image, cv2.imread(str(reference))))})
    finally:
        cap.release()
    x0, y0, x1, y1 = REGION
    crops = [images[f][y0:y1, x0:x1] for f in DONOR_FRAMES]
    lines = np.zeros(crops[0].shape[:2], bool)
    for a, b in ROWS:
        lines[a-y0:b-y0] = True
    votes = np.stack([cream_core(c) & lines for c in crops]).sum(0)
    core = (votes >= 5) & cream_core(crops[1])
    extent = cv2.dilate(core.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0
    pages = []
    donor = crops[1]
    stable = core & (donor[..., 1] > 218) & (donor[..., 2] > 230)
    for start in range(1225, 1285, 6):
        canvas = Image.new("RGB", (710*2, (96*2+24)*6), "white")
        draw = ImageDraw.Draw(canvas)
        for index, frame in enumerate(range(start, min(start+6, 1285))):
            crop = images[frame][y0:y1, x0:x1]
            marked = crop.copy()
            marked[warm_glyph_core(crop) & ~extent] = (0, 0, 255)
            pair = cv2.resize(np.concatenate((crop, marked), axis=1), None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
            y = index * (96*2+24)
            draw.text((6, y+5), f"f{frame}: ACTUAL SOURCE | RED = UNSUPPORTED WARM CANDIDATES, NOT GLYPHS", fill="black")
            canvas.paste(Image.fromarray(cv2.cvtColor(pair, cv2.COLOR_BGR2RGB)), (0, y+24))
            offsets = []
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    moved = images[frame][y0+dy:y1+dy, x0+dx:x1+dx]
                    offsets.append((float(np.median(np.max(cv2.absdiff(moved, donor), axis=2)[stable])), dx, dy))
            best = min(offsets, key=lambda row: (row[0], abs(row[1])+abs(row[2])))
            delta = np.max(cv2.absdiff(crop, donor), axis=2)[stable]
            records[frame-1225].update({"best_local_offset_xy": [best[1], best[2]],
                "stable_core_p95_max_channel_delta": float(np.quantile(delta, .95)),
                "unsupported_warm_candidates": int(np.count_nonzero(warm_glyph_core(crop) & ~extent))})
        file = OUT / f"source-caption-page-{(start-1225)//6+1:02d}.png"
        canvas.save(file)
        pages.append({"path": str(file), "sha256": sha(file)})
    marked = donor.copy()
    marked[core] = (0, 255, 0)
    marked[extent & ~core] = (255, 160, 30)
    cv2.imwrite(str(OUT / "registered-core-extent.png"), cv2.resize(marked, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST))
    np.savez_compressed(OUT / "source-registered-core.npz", votes=votes, core=core, extent=extent)
    report = {"scope_half_open": [1225, 1285], "source_video_sha256": meta["sha256"],
              "actual_source_count": len(records), "registered_region_xyxy": REGION,
              "line_core_rows": ROWS, "donor_frames": DONOR_FRAMES,
              "required_votes": 5, "core_candidate_policy": "Observed cream BGR within 28/channel; max channel >220. Five of six moving-body donors plus primary donor.",
              "core_pixels": int(core.sum()),
              "extent_pixels": int(extent.sum()), "pages": pages, "rows": records,
              "limits": ["Warm candidates are not exclusively glyphs.",
                         "This is registration evidence, not transparent-alpha or artistic acceptance."]}
    (OUT / "source-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(OUT / "source-audit.json"), "count": len(records),
                      "all_source_refs_equal": all(r["actual_decode_equals_reference"] for r in records),
                      "all_offsets_zero": all(r["best_local_offset_xy"] == [0, 0] for r in records),
                      "core_pixels": int(core.sum()),
                      "p95_range": [min(r["stable_core_p95_max_channel_delta"] for r in records),
                                    max(r["stable_core_p95_max_channel_delta"] for r in records)]}, indent=2))


if __name__ == "__main__":
    main()
