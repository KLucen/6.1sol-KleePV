"""All 99 final single-preview captions, decoded sequentially at native size."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "encoded-v10"
sys.path.insert(0, str(ROOT))
from dance_caption_layers import (CLEAR_INTERVAL, CLEAR_REGION, DONOR, NIGHT_DONOR,
    registered_caption, warm_glyph_core)
from night_transition_layers import is_registered as night_matte_registered


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bgrsha(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", type=int, default=10)
    args = parser.parse_args()
    version = args.version
    OUT = Path(__file__).resolve().parent / f"encoded-v{version}"
    cv2.setNumThreads(2)
    OUT.mkdir(parents=True, exist_ok=True)
    video = ROOT / f"output/klee-dance-812-911-fast-draft-v{version}.mp4"
    timeline_file = ROOT / f"timeline-dance-812-911-fast-draft-v{version}.json"
    timeline = json.loads(timeline_file.read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    if sha(meta["source"]) != meta["sha256"]:
        raise ValueError("Source file changed")
    if timeline["source_start"] != 812 or timeline["frames"] != 99:
        raise ValueError("Expected the fixed 99-frame dance interval")
    source_cap, encoded_cap = cv2.VideoCapture(meta["source"]), cv2.VideoCapture(str(video))
    panels, rows = [], []
    try:
        for frame in range(812):
            if not source_cap.grab():
                raise ValueError(f"Source ended at {frame}")
        for frame in range(812, 911):
            ok, source = source_cap.read()
            encoded_ok, encoded = encoded_cap.read()
            if not ok or not encoded_ok or source.shape != (1080, 1920, 3) or encoded.shape != source.shape:
                raise ValueError(f"Actual native decode failed at {frame}")
            exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
            asset = timeline["assets"][exposure["cel"]]
            registration = registered_caption(frame)
            if registration is None:
                if not CLEAR_INTERVAL[0] <= frame < CLEAR_INTERVAL[1]:
                    raise ValueError(f"Unregistered caption phase {frame}")
                region, layer, strict = CLEAR_REGION, None, False
                phase = "clear-source-small-caption"
            else:
                region, layer, strict = registration
                phase = "night-f897-lyric" if strict else "dance-f831-lyric"
            x0, y0, x1, y1 = region
            raw_source_crop = source[y0:y1, x0:x1]
            glyph = warm_glyph_core(raw_source_crop)
            if layer is not None:
                glyph &= layer["source_core"]
                if strict:
                    glyph &= np.max(np.abs(raw_source_crop.astype(np.float32)-layer["foreground_bgr"]), axis=2) <= 25
            delta = np.max(cv2.absdiff(raw_source_crop, encoded[y0:y1, x0:x1]), axis=2)[glyph]
            # Evidence gets margins; restoration never copies this rectangle.
            cx0, cy0, cx1, cy1 = x0-12, y0-10, x1+12, y1+7
            pair = np.concatenate((source[cy0:cy1, cx0:cx1], encoded[cy0:cy1, cx0:cx1]), axis=1)
            pair_path = OUT / f"f{frame:04d}-source-encoded-caption.png"
            cv2.imwrite(str(pair_path), pair)
            image = Image.new("RGB", (pair.shape[1]*2, pair.shape[0]*2+24), "white")
            ImageDraw.Draw(image).text((6, 5), f"f{frame}: {phase} | ACTUAL SOURCE / ENCODED V{version} (STATIC CAPTION SCOPE)", fill="black")
            scaled = cv2.resize(pair, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
            image.paste(Image.fromarray(cv2.cvtColor(scaled, cv2.COLOR_BGR2RGB)), (0, 24))
            panels.append(image)
            archive = OUT / f"f{frame:04d}-registered-glyph-mask.npz"
            support = layer["extent"] if layer is not None else np.ones(glyph.shape, bool)
            np.savez_compressed(archive, actual_observed_registered_core=glyph,
                                registered_support=support,
                                registered_alpha=layer["alpha"] if layer is not None else np.ones(glyph.shape, np.float32))
            rows.append({"source_frame": frame, "source_pts": meta["pts"][frame],
                "encoded_frame_index": frame-812, "encoded_decode_msec": encoded_cap.get(cv2.CAP_PROP_POS_MSEC),
                "source_bgr_sha256": bgrsha(source), "encoded_bgr_sha256": bgrsha(encoded),
                "cel": exposure["cel"], "asset": asset["path"], "asset_sha256": sha(ROOT / asset["path"]),
                "phase": phase, "registered_region_xyxy": region, "evidence_region_xyxy": [cx0, cy0, cx1, cy1],
                "caption_pair": str(pair_path), "caption_pair_sha256": sha(pair_path),
                "glyph_mask_archive": str(archive), "glyph_mask_archive_sha256": sha(archive),
                "actual_observed_registered_core_pixels": int(glyph.sum()),
                "encoded_core_max_channel_delta_p95": float(np.quantile(delta, .95)) if delta.size else None,
                "encoded_core_max_channel_delta_gt30_pixels": int(np.count_nonzero(delta > 30)),
                "donor_sha256": layer["donor_sha256"] if layer is not None else None,
                "phase_donor_sha256": layer["phase_donor_sha256"] if layer is not None else None,
                "scoped_night_matte_registered": bool(night_matte_registered(frame, Path(asset["path"]).name)),
                "diagnostic_limit": "Registered observed core only; encoded YUV color error is not exact-RGB or glyph-readability acceptance."})
        if encoded_cap.read()[0]:
            raise ValueError("Preview has extra encoded frames")
    finally:
        source_cap.release()
        encoded_cap.release()
    pages = []
    for start in range(0, len(panels), 8):
        group = panels[start:start+8]
        canvas = Image.new("RGB", (max(im.width for im in group), sum(im.height for im in group)), "white")
        y = 0
        for image in group:
            canvas.paste(image, (0, y))
            y += image.height
        file = OUT / f"caption-page-{start//8+1:02d}.png"
        canvas.save(file)
        pages.append({"path": str(file), "sha256": sha(file), "source_frames": list(range(812+start, min(820+start, 911)))})
    report = {"source_interval_half_open": [812, 911], "source_actual_native_decodes": 99,
        "encoded_actual_native_decodes": 99, "extra_encoded_frames": 0,
        "source_video_sha256": meta["sha256"], "video": str(video), "video_sha256": sha(video),
        "timeline": str(timeline_file), "timeline_sha256": sha(timeline_file),
        "donor_sha256": {str(p): sha(p) for p in (DONOR, NIGHT_DONOR)},
        "implementation_sha256": {str(p): sha(p) for p in (ROOT / "compose.py", ROOT / "dance_caption_layers.py", ROOT / "night_transition_layers.py", Path(__file__))},
        "pages": pages, "rows": rows, "artistic_acceptance": False,
        "original_speed_video_review": "not_performed_by_this_caption_task",
        "caption_static_review": "pending_all_13_pages",
        "limits": ["Color diagnostics use registered source glyph support, not arbitrary warm clothing candidates.",
                   "Every image is a native actual encoded/source crop, not a raw-composite substitute.",
                   "Static crops cannot establish character motion, original-speed continuity or full-PV acceptance."]}
    path = OUT / "report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "count": len(rows), "pages": len(pages),
                      "video_sha256": report["video_sha256"],
                      "p95_minmax": [min(r["encoded_core_max_channel_delta_p95"] for r in rows),
                                     max(r["encoded_core_max_channel_delta_p95"] for r in rows)]}, indent=2))


if __name__ == "__main__":
    main()
