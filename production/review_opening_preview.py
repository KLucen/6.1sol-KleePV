"""Chronological raw-composite QA; this is not original-speed artistic acceptance."""

from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import inspect
import json
from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import compose as compositor
from opening_clock_layers import restore_clock

ROOT = Path(__file__).resolve().parent
PANEL_SIZE = (640, 360)
CLOCK_COLOR = np.array([210, 210, 30], dtype=np.uint8)


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_spans(mapping, end):
    return [{"start": span["start"], "end": min(span["end"], end), "cel": span["cel"]}
            for span in mapping["source_exposures"] if span["start"] < end]


def contact_pages(rows, thumbnails, output, prefix):
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    pages = []
    row_height, top = 386, 44
    for offset in range(0, len(rows), 8):
        batch = rows[offset:offset + 8]
        canvas = Image.new("RGB", (1280, top + row_height * len(batch)), (30, 33, 37))
        draw = ImageDraw.Draw(canvas)
        draw.text((10, 11), "SOURCE", font=font, fill=(255, 255, 255))
        draw.text((650, 11), "RAW COMPOSITE / PRE-ENCODING / DRAFT", font=font, fill=(255, 255, 255))
        for row, y in zip(batch, range(top, canvas.height, row_height)):
            draw.text((10, y + 3), row["label"], font=font, fill=(240, 240, 240))
            canvas.paste(thumbnails[row["frame"]], (0, y + 26))
        path = output / f"{prefix}-page-{offset // 8 + 1:02d}.jpg"
        canvas.save(path, quality=95, subsampling=0)
        pages.append({"path": str(path.resolve()), "frames": [r["frame"] for r in batch],
                      "rows": batch})
    return pages


def review(timeline_path, output):
    started = time.monotonic()
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    mapping = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    compositor.validate_render_timing(timeline, metadata)
    if timeline["frames"] != 210:
        raise ValueError("This bounded review covers exactly source frames [0,210)")
    required_arguments = {"asset_source_frame", "asset_name", "current_frame"}
    if not required_arguments <= set(inspect.signature(compositor.compose).parameters):
        raise ValueError("Updated compositor frame gates are not ready")
    source = Path(timeline["source"])
    if not compositor.source_matches_metadata(source, metadata):
        raise ValueError("Original source hash does not match saved metadata")
    exposures = timeline["output_exposures"]
    expected_spans = source_spans(mapping, 210)
    actual_spans = [{key: span[key] for key in ("start", "end", "cel")} for span in exposures]
    used_cels = sorted({span["cel"] for span in exposures})
    assets = timeline["assets"]
    provenance_paths = [timeline_path.resolve(), ROOT / "compose.py", ROOT / "opening_clock_layers.py",
                        ROOT / "source_map.json", ROOT / "source_meta.json"]
    provenance_paths.extend((timeline_path.parent / assets[cel]["path"]).resolve() for cel in used_cels)
    provenance_paths = list(dict.fromkeys(provenance_paths))
    provenance = {str(path): file_hash(path) for path in provenance_paths}
    path_to_cels = {}
    for cel in used_cels:
        path = str((timeline_path.parent / assets[cel]["path"]).resolve())
        path_to_cels.setdefault(path, []).append(cel)
    duplicated_paths = [{"path": path, "cels": cels} for path, cels in path_to_cels.items() if len(cels) > 1]
    alias_valid = all(assets[cel].get("verified_source_alias", {}).get("review") == "manual_full_resolution_source_approved"
                      for group in duplicated_paths for cel in group["cels"][1:])
    report = {"version": 1, "scope": "chronological static/raw-composite technical review",
              "artistic_acceptance": False, "original_speed_watch": "not_performed",
              "source_interval": [0, 210], "timeline": str(timeline_path.resolve()),
              "exposure_count": len(exposures), "retained_source_cel_count": len(used_cels),
              "distinct_generated_file_count": len(path_to_cels), "used_cels": used_cels,
              "duplicated_asset_paths": duplicated_paths, "provenance_sha256": provenance,
              "limitations": ["Contact sheets are static and reduced to 640x360 per panel.",
                              "Pixel equality is measured before lossy video encoding.",
                              "Supported clock copying is checked; held clocks and unverified camera transforms remain excluded.",
                              "Matching source cel IDs does not grant single-drawing or temporal artistic acceptance."],
              "checks": {"exact_source_exposure_mapping": actual_spans == expected_spans,
                         "expected_33_exposures": len(exposures) == 33,
                         "full_prefix_coverage": bool(exposures) and exposures[0]["start"] == 0
                         and exposures[-1]["end"] == 210
                         and all(a["end"] == b["start"] for a, b in zip(exposures, exposures[1:])),
                         "no_unverified_held_substitute_across_distinct_cels": not duplicated_paths or alias_valid},
              "frames": [], "contacts": {}}
    if not report["checks"]["full_prefix_coverage"]:
        raise ValueError("Exposure list does not completely cover [0,210)")
    start_rows, boundary_rows = [], []
    for index, exposure in enumerate(exposures):
        frame = exposure["start"]
        label = f"START {index + 1:02d} f{frame:04d} | {timeline['source_pts'][frame]:.3f}s | {exposure['cel']} | {Path(assets[exposure['cel']]['path']).name}"
        start_rows.append({"frame": frame, "cel": exposure["cel"], "label": label})
        if index:
            before = frame - 1
            previous = exposures[index - 1]
            boundary_rows.extend([
                {"frame": before, "cel": previous["cel"],
                 "label": f"BOUNDARY {index:02d} BEFORE f{before:04d} | {timeline['source_pts'][before]:.3f}s | {previous['cel']} | {Path(assets[previous['cel']]['path']).name}"},
                {"frame": frame, "cel": exposure["cel"],
                 "label": f"BOUNDARY {index:02d} AFTER  f{frame:04d} | {timeline['source_pts'][frame]:.3f}s | {exposure['cel']} | {Path(assets[exposure['cel']]['path']).name}"}])
    selected_frames = {row["frame"] for row in start_rows + boundary_rows}
    thumbnails = {}

    @lru_cache(maxsize=8)
    def load_cel(cel):
        asset = assets[cel]
        return compositor.read_image(timeline_path.parent / asset["source_reference"]), compositor.read_image(timeline_path.parent / asset["path"])

    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise ValueError("Cannot open original source video")
    index = 0
    try:
        for frame in range(210):
            ok, current = cap.read()
            if not ok:
                raise ValueError(f"Original source ended at frame {frame}")
            while frame >= exposures[index]["end"]:
                index += 1
            exposure = exposures[index]
            cel, transform = exposure["cel"], exposure.get("source_matrix")
            asset = assets[cel]
            reference, generated = load_cel(cel)
            result, _, diagnostic_masks = compositor.compose(current, reference, generated, transform,
                                                             asset["source_frame"], Path(asset["path"]).name, frame)
            matrix = np.float32(transform or [[1, 0, 0], [0, 1, 0]])
            transformed = generated if np.allclose(matrix, [[1, 0, 0], [0, 1, 0]]) else cv2.warpAffine(generated, matrix, (1920, 1080))
            _, expected_clock = restore_clock(current, current, transformed, asset["source_frame"],
                                              Path(asset["path"]).name, matrix)
            applied_clock = np.all(diagnostic_masks == CLOCK_COLOR, axis=2)
            clock_pixels = expected_clock != 0
            caption_mismatches = int(np.count_nonzero(np.any(result[350:840, :800] != current[350:840, :800], axis=2))) if frame >= 38 else None
            clock_mismatches = int(np.count_nonzero(np.any(result != current, axis=2) & clock_pixels))
            row = {"frame": frame, "source_pts": timeline["source_pts"][frame], "cel": cel,
                   "asset": asset["path"], "asset_source_frame": asset["source_frame"],
                   "caption_roi_mismatch_pixels": caption_mismatches,
                   "supported_clock_copy_pixels": int(np.count_nonzero(clock_pixels)),
                   "clock_source_mismatch_pixels": clock_mismatches,
                   "clock_mask_application_mismatch_pixels": int(np.count_nonzero(applied_clock != clock_pixels))}
            report["frames"].append(row)
            if frame in selected_frames:
                left, right = cv2.resize(current, PANEL_SIZE, interpolation=cv2.INTER_AREA), cv2.resize(result, PANEL_SIZE, interpolation=cv2.INTER_AREA)
                thumbnails[frame] = Image.fromarray(cv2.cvtColor(np.concatenate([left, right], axis=1), cv2.COLOR_BGR2RGB))
            if caption_mismatches or clock_mismatches or row["clock_mask_application_mismatch_pixels"]:
                evidence = output / "mismatches"
                evidence.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(evidence / f"f{frame:04d}-source.png"), current)
                cv2.imwrite(str(evidence / f"f{frame:04d}-composite.png"), result)
            if (frame + 1) % 25 == 0:
                print(json.dumps({"raw_frames_checked": frame + 1, "elapsed_seconds": round(time.monotonic() - started, 2)}), flush=True)
    finally:
        cap.release()
    output.mkdir(parents=True, exist_ok=True)
    report["contacts"]["exposure_starts"] = contact_pages(start_rows, thumbnails, output, "exposure-starts")
    report["contacts"]["boundary_pairs"] = contact_pages(boundary_rows, thumbnails, output, "boundary-pairs")
    rows = report["frames"]
    report["checks"].update({"all_210_raw_frames_checked": len(rows) == 210,
                             "complete_left_caption_roi_pixel_equal_frames_38_to_209": all(r["caption_roi_mismatch_pixels"] == 0 for r in rows if r["frame"] >= 38),
                             "all_supported_clock_pixels_source_equal": all(r["clock_source_mismatch_pixels"] == 0 for r in rows),
                             "all_supported_clock_masks_applied": all(r["clock_mask_application_mismatch_pixels"] == 0 for r in rows),
                             "inputs_unchanged_during_review": all(file_hash(Path(path)) == digest for path, digest in provenance.items()),
                             "original_source_unchanged": compositor.source_matches_metadata(source, metadata)})
    report["clock_copy_summary"] = {"supported_frames": [r["frame"] for r in rows if r["supported_clock_copy_pixels"]],
                                    "unsupported_or_unverified_frames": [r["frame"] for r in rows if not r["supported_clock_copy_pixels"]],
                                    "total_source_equal_copied_pixels": sum(r["supported_clock_copy_pixels"] for r in rows),
                                    "total_source_mismatch_pixels": sum(r["clock_source_mismatch_pixels"] for r in rows)}
    report["caption_summary"] = {"checked_frames": 172, "roi": [0, 350, 800, 840],
                                 "total_mismatch_pixels": sum(r["caption_roi_mismatch_pixels"] or 0 for r in rows)}
    report["contact_summary"] = {"start_rows": len(start_rows), "boundary_rows": len(boundary_rows),
                                 "distinct_sampled_frames": len(selected_frames), "panel_size": list(PANEL_SIZE),
                                 "pages": sum(len(pages) for pages in report["contacts"].values())}
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    report["technical_static_pass"] = all(report["checks"].values())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "qa/opening-210-review")
    args = parser.parse_args()
    cv2.setNumThreads(2)
    report = review(args.timeline, args.output)
    destination = args.output / "review-report.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(destination.resolve()), "technical_static_pass": report["technical_static_pass"],
                      "retained_source_cels": report["retained_source_cel_count"], "exposures": report["exposure_count"],
                      "pages": report["contact_summary"]["pages"], "elapsed_seconds": report["elapsed_seconds"],
                      "failed_checks": [name for name, passed in report["checks"].items() if not passed]}))
    raise SystemExit(0 if report["technical_static_pass"] else 1)


if __name__ == "__main__":
    main()
