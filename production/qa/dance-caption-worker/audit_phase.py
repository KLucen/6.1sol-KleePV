"""Create source-phase and transparent-matte evidence for the registered interval."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dance_caption_layers import (DONOR, LINE_CORE_ROWS, REGION, SOURCE_INTERVAL, dance_caption_layer,
                                  restore_dance_captions, warm_glyph_core)
from review_opening_preview import file_hash

OUT = Path(__file__).resolve().parent
SOURCES = {831: "src-0377-f0831.png", 835: "src-0381-f0835.png",
           839: "src-0385-f0839.png", 843: "src-0389-f0843.png",
           848: "src-0394-f0848.png", 852: "src-0398-f0852.png",
           856: "src-0402-f0856.png", 863: "src-0409-f0863.png",
           868: "src-0414-f0868.png", 873: "src-0419-f0873.png",
           880: "src-0426-f0880.png"}


def phase_stats(current, donor_crop, layer, stable):
    x0, y0, x1, y1 = REGION
    core = warm_glyph_core(current)
    line_rows = np.zeros(core.shape, bool)
    for start, end in LINE_CORE_ROWS:
        line_rows[start-y0:end-y0] = True
    core &= line_rows
    differences = np.max(cv2.absdiff(donor_crop, current), axis=2)
    offsets = []
    pad = cv2.copyMakeBorder(current, 2, 2, 2, 2, cv2.BORDER_REFLECT)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            shifted = pad[2+dy:2+dy+current.shape[0], 2+dx:2+dx+current.shape[1]]
            error = np.max(cv2.absdiff(donor_crop, shifted), axis=2)[stable].mean()
            offsets.append((float(error), dx, dy))
    best = min(offsets)
    unsupported = core & (layer["alpha"] == 0)
    strong_unsupported = unsupported & (current[..., 1] > 210)
    y, x = np.nonzero(unsupported)
    return {"donor_core_pixels": int(layer["source_core"].sum()),
            "current_warm_core_pixels": int(core.sum()),
            "current_warm_core_hits_on_donor_core": int(np.count_nonzero(core & layer["source_core"])),
            "current_warm_core_outside_donor_alpha_pixels": int(unsupported.sum()),
            "current_strong_warm_core_outside_donor_alpha_pixels": int(strong_unsupported.sum()),
            "unsupported_sample_xy": [[int(xx+x0), int(yy+y0)] for xx, yy in zip(x[:40], y[:40])],
            "stable_interior_pixels": int(stable.sum()),
            "stable_interior_mean_max_channel_delta": float(differences[stable].mean()),
            "stable_interior_p95_max_channel_delta": float(np.percentile(differences[stable], 95)),
            "best_local_offset_xy": [best[1], best[2]],
            "best_offset_mean_max_channel_delta": best[0]}


def main():
    layer = dance_caption_layer()
    x0, y0, x1, y1 = REGION
    donor = cv2.imread(str(DONOR), cv2.IMREAD_COLOR)
    crop = donor[y0:y1, x0:x1]
    stable = layer["source_core"] & (layer["alpha"] >= 0.96)
    rows, panels = [], []
    for frame, name in SOURCES.items():
        path = ROOT / "source_refs" / name
        source = cv2.imread(str(path), cv2.IMREAD_COLOR)
        current = source[y0:y1, x0:x1]
        rows.append({"frame": frame, "source_reference": str(path),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     **phase_stats(current, crop, layer, stable)})
        underlay = source.copy()
        underlay[y0:y1, x0:x1] = (35, 48, 68)
        over_boot, _ = restore_dance_captions(underlay, source, frame)
        panel = np.concatenate([current, over_boot[y0:y1, x0:x1]], axis=1)
        panel = cv2.resize(panel, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
        image = Image.fromarray(cv2.cvtColor(panel, cv2.COLOR_BGR2RGB))
        captioned = Image.new("RGB", (image.width, image.height+24), "white")
        captioned.paste(image, (0, 24))
        ImageDraw.Draw(captioned).text((5, 5), f"f{frame:04d} ORIGINAL | CONSTANT DARK BOOT UNDER TRANSPARENT SOURCE LYRICS", fill="black")
        panels.append(captioned)
    contact = Image.new("RGB", (panels[0].width, sum(p.height for p in panels)), "white")
    top = 0
    for panel in panels:
        contact.paste(panel, (0, top))
        top += panel.height
    contact.save(OUT / "source-phase-and-over-boot.png")
    rgba = np.zeros((*layer["alpha"].shape, 4), np.uint8)
    rgba[..., :3] = np.rint(layer["foreground_bgr"][::-1]).astype(np.uint8)
    rgba[..., 3] = np.rint(layer["alpha"] * 255).astype(np.uint8)
    Image.fromarray(rgba).save(OUT / "caption-transparent-local.png")
    cv2.imwrite(str(OUT / "estimated-local-background.png"), layer["estimated_plate_bgr"])
    metadata = json.loads((ROOT/"source_meta.json").read_text(encoding="utf-8"))
    source_path = Path(metadata["source"])
    source_hash = file_hash(source_path)
    if source_hash != metadata["sha256"]:
        raise ValueError("Source identity changed before caption audit")
    consecutive, unsupported_points, unsupported_panels = [], [], []
    cap = cv2.VideoCapture(str(source_path))
    try:
        for frame in range(SOURCE_INTERVAL[0]):
            if not cap.grab():
                raise ValueError("Source ended before audited interval")
        for frame in range(*SOURCE_INTERVAL):
            ok, source = cap.read()
            if not ok:
                raise ValueError("Source ended inside audited interval")
            current = source[y0:y1, x0:x1]
            consecutive.append({"frame": frame, "decoded_frame_sha256": hashlib.sha256(source.tobytes()).hexdigest(),
                                **phase_stats(current, crop, layer, stable)})
            core = warm_glyph_core(current)
            line_rows = np.zeros(core.shape, bool)
            for start, end in LINE_CORE_ROWS:
                line_rows[start-y0:end-y0] = True
            unsupported = core & line_rows & (layer["alpha"] == 0)
            y, x = np.nonzero(unsupported)
            unsupported_points.append(np.column_stack([np.full(len(x), frame), x+x0, y+y0]))
            marked = current.copy()
            marked[unsupported] = (0, 0, 255)
            pair = cv2.resize(np.concatenate([current, marked], axis=1), None,
                              fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
            panel = Image.new("RGB", (pair.shape[1], pair.shape[0]+24), "white")
            panel.paste(Image.fromarray(cv2.cvtColor(pair, cv2.COLOR_BGR2RGB)), (0, 24))
            ImageDraw.Draw(panel).text((5, 5), f"f{frame:04d} SOURCE | RED: CURRENT WARM CORE OUTSIDE DONOR ALPHA", fill="black")
            unsupported_panels.append(panel)
    finally:
        cap.release()
    np.savez_compressed(OUT / "unsupported-current-warm-core-points.npz",
                        frame_x_y=np.concatenate(unsupported_points).astype(np.int16))
    diagnostic_pages = []
    for start in range(0, len(unsupported_panels), 4):
        page_panels = unsupported_panels[start:start+4]
        page = Image.new("RGB", (page_panels[0].width, sum(p.height for p in page_panels)), "white")
        top = 0
        for panel in page_panels:
            page.paste(panel, (0, top))
            top += panel.height
        path = OUT / f"unsupported-current-core-page-{start//4+1:02d}.png"
        page.save(path)
        diagnostic_pages.append(str(path))
    tests = subprocess.run([sys.executable, "-m", "unittest", "test_dance_caption_layers", "-v"],
                           cwd=ROOT, capture_output=True, text=True)
    (OUT/"focused-tests.txt").write_text(tests.stdout+tests.stderr, encoding="utf-8")
    base_phase = [row for row in consecutive if 831 <= row["frame"] < 863]
    report = {"source_interval": list(SOURCE_INTERVAL), "region": list(REGION),
              "donor": str(DONOR), "donor_sha256": layer["donor_sha256"],
              "foreground_bgr": layer["foreground_bgr"].tolist(),
              "phase_donor_sha256": layer["phase_donor_sha256"],
              "implementation_sha256": {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                         for name in ("dance_caption_layers.py", "test_dance_caption_layers.py")},
              "alpha_support_pixels": int(np.count_nonzero(layer["alpha"])),
              "reconstruction": layer["reconstruction"], "source_phase_rows": rows,
              "source": str(source_path), "source_sha256": source_hash,
              "consecutive_source_frames": consecutive,
              "registered_source_frame_count": len(consecutive),
              "all_registered_source_frames_checked": len(consecutive) == SOURCE_INTERVAL[1]-SOURCE_INTERVAL[0],
              "all_registered_best_offsets_zero": all(r["best_local_offset_xy"] == [0, 0] for r in consecutive),
              "all_registered_current_warm_core_inside_donor_alpha": all(
                  r["current_warm_core_outside_donor_alpha_pixels"] == 0 for r in consecutive),
              "legacy_32_fields_scope": [831, 863],
              "all_32_source_frames_checked": len(base_phase) == 32,
              "all_best_offsets_zero": all(r["best_local_offset_xy"] == [0, 0] for r in rows),
              "all_32_best_offsets_zero": all(r["best_local_offset_xy"] == [0, 0] for r in base_phase),
              "all_32_current_warm_core_inside_donor_alpha": all(
                  r["current_warm_core_outside_donor_alpha_pixels"] == 0 for r in base_phase),
              "unsupported_point_archive": str(OUT/"unsupported-current-warm-core-points.npz"),
              "unsupported_point_archive_columns": ["frame", "x", "y"],
              "unsupported_diagnostic_pages": diagnostic_pages,
              "focused_tests": {"command": "python -m unittest test_dance_caption_layers -v",
                                "exit_code": tests.returncode, "count": 10,
                                "transcript": str(OUT/"focused-tests.txt")},
              "artistic_acceptance": False, "original_speed_watch": "not_performed",
              "limitations": ["Local offset and color agreement support one caption phase but are not OCR or manual full-frame acceptance.",
                              "The plate behind glyphs and projected AA are reconstructed, not observed exact source transparency.",
                              "Star crossings inside Japanese glyph counters remain less certain than the unobstructed Chinese line; no exact original alpha is claimed.",
                              "Transparent layer cannot correct pose, shoe extent, or final pale-on-pale contrast."]}
    (OUT / "phase-and-layer-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(OUT/"phase-and-layer-audit.json"),
                      "registered_source_frame_count": report["registered_source_frame_count"],
                      "all_registered_source_frames_checked": report["all_registered_source_frames_checked"],
                      "all_registered_best_offsets_zero": report["all_registered_best_offsets_zero"],
                      "all_registered_current_warm_core_inside_donor_alpha": report["all_registered_current_warm_core_inside_donor_alpha"],
                      "unsupported_range": [min(r["current_warm_core_outside_donor_alpha_pixels"] for r in consecutive),
                                            max(r["current_warm_core_outside_donor_alpha_pixels"] for r in consecutive)],
                      "focused_tests": report["focused_tests"]}, indent=2))


if __name__ == "__main__":
    main()
