"""Source-only 24-frame caption extension audit; no production mutation."""

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from dance_caption_layers import (
    DONOR, LINE_CORE_ROWS, REGION, SOURCE_INTERVAL, dance_caption_layer,
    restore_dance_captions, warm_glyph_core,
)
from review_opening_preview import file_hash

REFERENCE_AUDIT = ROOT / "qa/dance-caption-worker/audit_phase.py"
spec = importlib.util.spec_from_file_location("existing_caption_phase_audit", REFERENCE_AUDIT)
reference_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference_audit)
START, END = 863, 887
DARK_BGR = (35, 48, 68)


def digest_array(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def simulate_registered_layer(current, layer):
    # Private strategy test: identical crop formula, not an extended production call.
    target = np.empty_like(current)
    target[:] = DARK_BGR
    before = target.copy()
    alpha = layer["alpha"]
    paint = (alpha > 0) & np.any(target != current, axis=2)
    blended = (alpha[..., None] * layer["foreground_bgr"]
               + (1 - alpha[..., None]) * target.astype(np.float32))
    target[paint] = np.clip(np.rint(blended[paint]), 0, 255).astype(np.uint8)
    observed = paint & layer["source_core"] & warm_glyph_core(current)
    target[observed] = current[observed]
    return target, {
        "private_simulation_painted_pixels": int(paint.sum()),
        "private_simulation_observed_core_pixels": int(observed.sum()),
        "private_simulation_changed_outside_registered_alpha_pixels": int(
            np.count_nonzero(np.any(target != before, axis=2) & (alpha == 0))),
    }


def panel_pair(first, second, text):
    pair = cv2.resize(np.concatenate([first, second], axis=1), None,
                      fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    panel = Image.new("RGB", (pair.shape[1], pair.shape[0] + 24), "white")
    panel.paste(Image.fromarray(cv2.cvtColor(pair, cv2.COLOR_BGR2RGB)), (0, 24))
    ImageDraw.Draw(panel).text((6, 5), text, fill="black")
    return panel


def write_pages(panels, stem):
    paths = []
    for start in range(0, len(panels), 4):
        group = panels[start:start + 4]
        page = Image.new("RGB", (group[0].width, sum(p.height for p in group)), "white")
        y = 0
        for panel in group:
            page.paste(panel, (0, y))
            y += panel.height
        path = OUT / f"{stem}-page-{start // 4 + 1:02d}.png"
        page.save(path)
        paths.append(str(path))
    return paths


def components(mask):
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    x0, y0, _, _ = REGION
    return [{"box_xyxy": [int(x + x0), int(y + y0), int(x + x0 + w), int(y + y0 + h)],
             "pixels": int(area)} for x, y, w, h, area in stats[1:count] if area >= 2]


def main():
    metadata_path = ROOT / "source_meta.json"
    source_map_path = ROOT / "source_map.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    candidates = {c["frame"]: c for c in source_map["candidates"] if START <= c["frame"] < END}
    if set(candidates) != set(range(START, END)):
        raise ValueError("Missing source-map per-frame candidates in the requested interval")
    source_path = Path(metadata["source"])
    source_hash = file_hash(source_path)
    if source_hash != metadata["sha256"]:
        raise ValueError("Original source video identity changed")

    layer = dance_caption_layer()
    x0, y0, x1, y1 = REGION
    donor_full = cv2.imread(str(DONOR), cv2.IMREAD_COLOR)
    donor = donor_full[y0:y1, x0:x1]
    stable = layer["source_core"] & (layer["alpha"] >= 0.96)
    line_rows = np.zeros(layer["alpha"].shape, bool)
    for start, end in LINE_CORE_ROWS:
        line_rows[start-y0:end-y0] = True

    rows, unsupported_points = [], []
    unsupported_panels, simulation_panels, difference_panels = [], [], []
    cap = cv2.VideoCapture(str(source_path))
    if not cap.isOpened():
        raise ValueError("Cannot decode original video")
    try:
        for frame in range(START):
            if not cap.grab():
                raise ValueError(f"Original ended before actual frame {frame}")
        for frame in range(START, END):
            ok, source = cap.read()
            if not ok or source.shape != (1080, 1920, 3):
                raise ValueError(f"Failed actual native decode for f{frame}")
            position_after_read = float(cap.get(cv2.CAP_PROP_POS_FRAMES))
            decoder_timestamp_ms = float(cap.get(cv2.CAP_PROP_POS_MSEC))
            current = source[y0:y1, x0:x1]
            core = warm_glyph_core(current) & line_rows
            unsupported = core & (layer["alpha"] == 0)
            y, x = np.nonzero(unsupported)
            unsupported_points.append(np.column_stack([np.full(len(x), frame), x+x0, y+y0]))
            simulated, simulation_stats = simulate_registered_layer(current, layer)
            production_probe = source.copy()
            production_probe[y0:y1, x0:x1] = DARK_BGR
            unmodified_probe = production_probe.copy()
            production_return, production_mask = restore_dance_captions(production_probe, source, frame)
            production_noop = np.array_equal(production_return, unmodified_probe) and not np.any(production_mask)
            candidate = candidates[frame]
            reference_path = ROOT / candidate["reference"]
            reference = cv2.imread(str(reference_path), cv2.IMREAD_COLOR)
            reference_delta = np.max(cv2.absdiff(source, reference), axis=2)
            core_hits = core & layer["source_core"]
            outside = core & ~layer["source_core"]
            missing = layer["source_core"] & ~core
            abs_delta = np.max(cv2.absdiff(donor, current), axis=2)
            row = {
                "frame": frame,
                "actual_video_decoded": True,
                "decoded_native_bgr_sha256": digest_array(source),
                "decoded_caption_bgr_sha256": digest_array(current),
                "decoded_size_wh": [1920, 1080],
                "decoder_position_after_read": position_after_read,
                "decoder_timestamp_ms": decoder_timestamp_ms,
                "source_map_candidate": {k: candidate[k] for k in (
                    "id", "frame", "start", "end", "pts", "end_pts", "cel", "reference", "source_transform")},
                "source_reference_file_sha256": file_hash(reference_path),
                "source_reference_decoded_bgr_sha256": digest_array(reference),
                "decoded_equals_source_reference_pixels": np.array_equal(source, reference),
                "decoded_vs_reference_mean_max_rgb_delta": float(reference_delta.mean()),
                "decoded_vs_reference_pixels_max_rgb_delta_gt_28": int(np.count_nonzero(reference_delta > 28)),
                **reference_audit.phase_stats(current, donor, layer, stable),
                "warm_core_outside_registered_core_pixels": int(outside.sum()),
                "registered_core_missing_current_warm_pixels": int(missing.sum()),
                "warm_core_xor_registered_core_pixels": int((core ^ layer["source_core"]).sum()),
                "current_warm_hits_mean_max_channel_delta": float(abs_delta[core_hits].mean()),
                "current_warm_hits_p95_max_channel_delta": float(np.percentile(abs_delta[core_hits], 95)),
                "unsupported_warm_components_min_2_pixels": components(unsupported),
                "production_function_still_noop_for_this_frame": production_noop,
                **simulation_stats,
            }
            rows.append(row)
            marked = current.copy()
            marked[unsupported] = (0, 0, 255)
            unsupported_panels.append(panel_pair(current, marked, f"f{frame:04d} ACTUAL DECODE | RED: WARM CORE OUTSIDE REGISTERED ALPHA"))
            simulation_panels.append(panel_pair(current, simulated, f"f{frame:04d} ACTUAL DECODE | PRIVATE SAME-LAYER SIMULATION OVER DARK; NOT PRODUCTION"))
            diff = np.minimum(cv2.absdiff(donor, current).astype(np.uint16) * 4, 255).astype(np.uint8)
            difference_panels.append(panel_pair(current, diff, f"f{frame:04d} ACTUAL DECODE | ACTUAL RGB ABS DIFF x4 AGAINST f0831 DONOR"))
    finally:
        cap.release()

    archive = OUT / "extension-unsupported-warm-core-points.npz"
    np.savez_compressed(archive, frame_x_y=np.concatenate(unsupported_points).astype(np.int16))
    diagnostic = write_pages(unsupported_panels, "extension-unsupported-warm-core")
    simulation_pages = write_pages(simulation_panels, "extension-private-transparent-simulation")
    difference_pages = write_pages(difference_panels, "extension-source-rgb-difference")
    unsupported_counts = [r["current_warm_core_outside_donor_alpha_pixels"] for r in rows]
    report = {
        "audit_written_utc": datetime.now(timezone.utc).isoformat(),
        "audit_scope": "24 actual original-video decodes only; f863 inclusive through f886 inclusive",
        "source_interval_half_open": [START, END],
        "decoded_frames_count": len(rows),
        "all_24_actual_source_frames_decoded": len(rows) == 24 and all(r["actual_video_decoded"] for r in rows),
        "no_old_32_frame_labels_reused_as_56_frame_proof": True,
        "source": str(source_path), "source_video_sha256": source_hash,
        "source_metadata_file_sha256": file_hash(metadata_path),
        "source_map_file_sha256": file_hash(source_map_path),
        "implementation_provenance_sha256": {
            str(path): file_hash(path) for path in (
                ROOT / "dance_caption_layers.py", REFERENCE_AUDIT, Path(__file__).resolve())},
        "source_aliases_added": False,
        "production_core_or_selections_modified": False,
        "production_interval_at_audit": list(SOURCE_INTERVAL),
        "production_all_24_extension_frames_currently_noop": all(r["production_function_still_noop_for_this_frame"] for r in rows),
        "region_xyxy": list(REGION),
        "line_core_rows_y": [list(pair) for pair in LINE_CORE_ROWS],
        "donor": str(DONOR), "donor_file_sha256": layer["donor_sha256"],
        "phase_donor_file_sha256": layer["phase_donor_sha256"],
        "foreground_bgr": layer["foreground_bgr"].tolist(),
        "registered_core_pixels": int(layer["source_core"].sum()),
        "stable_interior_pixels": int(stable.sum()),
        "registered_alpha_support_pixels": int(np.count_nonzero(layer["alpha"])),
        "reconstruction": layer["reconstruction"],
        "offset_search_xy_range": [-2, 2],
        "offset_definition": "Minimize mean max-channel donor delta on fixed stable donor interior; dx,dy shift sampled current image, not a measured global text displacement.",
        "all_24_best_offsets_zero": all(r["best_local_offset_xy"] == [0, 0] for r in rows),
        "all_24_warm_candidate_inside_registered_alpha": all(c == 0 for c in unsupported_counts),
        "unsupported_warm_candidate_count_range": [min(unsupported_counts), max(unsupported_counts)],
        "stable_mean_max_channel_delta_range": [min(r["stable_interior_mean_max_channel_delta"] for r in rows), max(r["stable_interior_mean_max_channel_delta"] for r in rows)],
        "stable_p95_max_channel_delta_range": [min(r["stable_interior_p95_max_channel_delta"] for r in rows), max(r["stable_interior_p95_max_channel_delta"] for r in rows)],
        "all_private_simulations_unchanged_outside_registered_alpha": all(r["private_simulation_changed_outside_registered_alpha_pixels"] == 0 for r in rows),
        "decoded_frames": rows,
        "unsupported_point_archive": str(archive),
        "unsupported_point_archive_columns": ["frame", "x", "y"],
        "unsupported_diagnostic_pages": diagnostic,
        "private_simulation_pages": simulation_pages,
        "actual_rgb_difference_pages": difference_pages,
        "related_source_pose_plan": str(OUT / "next-source-pose-and-prompt-plan.md"),
        "static_visual_review": "pending; separate review notes will be added after viewing generated diagnostics",
        "artistic_acceptance": False,
        "original_speed_watch": "not_performed",
        "limitations": [
            "Warm-color candidates are not an OCR segmentation: pale source shoe/cuff pixels can be candidates and must not be promoted to glyph support.",
            "Zero best offsets within the local search support a fixed caption phase, not exact original alpha or perfect source text recovery.",
            "The hidden plate and AA are reconstructed by inpaint and projection; pink star crossings inside Japanese glyph counters remain uncertain.",
            "Private dark-underlay simulations exercise the same registered layer formula without extending the production interval; they are not actual new-Klee composites.",
            "The registered matte must remain separate from character coverage; a broad source-caption rectangle would reintroduce the source boot at crossing frames.",
            "The second shoe unfolds at f873 and lowers into the caption band at f880; final Klee boots, glyph contrast, masking and frame transitions require new-art composite checks.",
            "No full-speed watch, OCR certification, 56-frame combined proof or artistic acceptance is claimed.",
        ],
    }
    path = OUT / "extension-caption-audit.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = [
        "# Source-Only Caption Extension Audit", "",
        "Scope: f863..886 inclusive, 24 actual sequential video decodes at native 1920x1080. No core, selection or source-alias changes.", "",
        f"- Source SHA256: `{source_hash}`",
        f"- Donor: f831; current production interval: `{tuple(SOURCE_INTERVAL)}` (half-open).",
        f"- All 24 decoded: `{report['all_24_actual_source_frames_decoded']}`.",
        f"- All 24 local best offsets [0, 0]: `{report['all_24_best_offsets_zero']}`.",
        f"- Warm candidates outside registered alpha range: `{report['unsupported_warm_candidate_count_range']}`.",
        f"- Stable-interior mean max-channel delta range: `{report['stable_mean_max_channel_delta_range']}`.",
        f"- All 24 currently NOOP in production: `{report['production_all_24_extension_frames_currently_noop']}`.",
        "- Old 32-frame audit is independent provenance, not reused as a 56-frame proof.", "",
        "## Per-Frame Actual Decode Evidence", "",
        "| Frame | PTS | Cel | Best dx,dy | Stable mean delta | Warm candidates | Outside alpha | Native BGR SHA256 |",
        "|---|---:|---|---|---:|---:|---:|---|",
    ]
    for row in rows:
        markdown.append(f"| {row['frame']} | {row['source_map_candidate']['pts']} | {row['source_map_candidate']['cel']} | {row['best_local_offset_xy']} | {row['stable_interior_mean_max_channel_delta']:.3f} | {row['current_warm_core_pixels']} | {row['current_warm_core_outside_donor_alpha_pixels']} | `{row['decoded_native_bgr_sha256']}` |")
    markdown += ["", "## Limits And Next Checks", ""]
    markdown += ["- " + limitation for limitation in report["limitations"]]
    markdown += ["", "## Diagnostic Pages", ""]
    markdown += ["- " + str(page) for page in diagnostic + simulation_pages + difference_pages]
    markdown += ["", "Static review of generated diagnostic pages is pending and must be recorded separately."]
    (OUT / "extension-caption-audit.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "decoded_frames_count", "all_24_actual_source_frames_decoded", "all_24_best_offsets_zero",
        "all_24_warm_candidate_inside_registered_alpha", "unsupported_warm_candidate_count_range",
        "stable_mean_max_channel_delta_range", "stable_p95_max_channel_delta_range",
        "production_all_24_extension_frames_currently_noop")}, indent=2))
    print(path)


if __name__ == "__main__":
    main()
