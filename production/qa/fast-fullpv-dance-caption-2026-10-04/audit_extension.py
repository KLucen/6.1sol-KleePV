"""Audit actual f887..910 source and available composites, not artistic acceptance."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import compose as compositor
from dance_caption_layers import (DONOR, NIGHT_DONOR, NIGHT_REGION, NIGHT_INTERVAL,
                                  REGION, SOURCE_INTERVAL, dance_caption_layer,
                                  NIGHT_PHASE_DONORS, night_caption_layer, restore_dance_captions, warm_glyph_core)

spec = importlib.util.spec_from_file_location("phase_audit", ROOT / "qa/dance-caption-worker/audit_phase.py")
phase_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase_audit)
START, END = 887, 911


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bgrsha(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def page(panels, stem, per_page=4):
    paths = []
    for start in range(0, len(panels), per_page):
        group = panels[start:start + per_page]
        canvas = Image.new("RGB", (max(p.width for p in group), sum(p.height for p in group)), "white")
        y = 0
        for panel in group:
            canvas.paste(panel, (0, y))
            y += panel.height
        path = OUT / f"{stem}-page-{start // per_page + 1:02d}.png"
        canvas.save(path)
        paths.append(str(path))
    return paths


def panel(images, label, scale=1):
    pair = np.concatenate(images, axis=1)
    if scale != 1:
        pair = cv2.resize(pair, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    canvas = Image.new("RGB", (pair.shape[1], pair.shape[0] + 24), "white")
    canvas.paste(Image.fromarray(cv2.cvtColor(pair, cv2.COLOR_BGR2RGB)), (0, 24))
    ImageDraw.Draw(canvas).text((6, 5), label, fill="black")
    return canvas


def available_assets(source_map, proposal_path=None):
    rows = {}
    anchors = json.loads((ROOT / "generation_jobs.json").read_text(encoding="utf-8"))["old_anchor_to_cel"]
    for anchor in anchors:
        stem = f"candidate-{anchor['old_id']}"
        choices = [ROOT / "generated" / f"{stem}{suffix}.png" for suffix in ("-red-eyes", "-clean", "")]
        asset = next((p for p in choices if p.exists()), None)
        if asset:
            rows[anchor["old_source_frame"]] = asset
    for selection in json.loads((ROOT / "asset_selections.json").read_text(encoding="utf-8"))["selections"]:
        if selection["path"]:
            rows[selection["source_frame"]] = ROOT / selection["path"]
        else:
            rows.pop(selection["source_frame"], None)
    if proposal_path:
        for proposal in json.loads(proposal_path.read_text(encoding="utf-8"))["proposed_assets"]:
            rows[proposal["source_frame"]] = ROOT / proposal["path"]
    result = {}
    for frame, asset in rows.items():
        candidate = next(c for c in source_map["candidates"] if c["start"] <= frame < c["end"])
        result[candidate["cel"]] = (frame, asset, candidate)
    return result


def main():
    global OUT, START, END
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="final")
    parser.add_argument("--proposal", type=Path)
    parser.add_argument("--frames", type=int, nargs="+", help="Audit only these affected native frames")
    arguments = parser.parse_args()
    requested_frames = set(arguments.frames) if arguments.frames else None
    if requested_frames:
        if not requested_frames.issubset(set(range(887, 911))):
            raise ValueError("This audit only registers f887..910")
        START, END = min(requested_frames), max(requested_frames)+1
    OUT = OUT / arguments.stage
    cv2.setNumThreads(2)
    OUT.mkdir(exist_ok=True, parents=True)
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    candidates = source_map["candidates"]
    assets = available_assets(source_map, arguments.proposal)
    source_path = Path(metadata["source"])
    if sha(source_path) != metadata["sha256"]:
        raise ValueError("Source video hash changed")
    rows, source_panels, diagnostic_panels, composite_panels, full_panels, simulation_panels = [], [], [], [], [], []
    donor_decodes = []
    cap = cv2.VideoCapture(str(source_path))
    try:
        for frame in range(START):
            if not cap.grab():
                raise ValueError(f"Source ended at {frame}")
        for frame in range(START, END):
            ok, current = cap.read()
            if not ok or current.shape != (1080, 1920, 3):
                raise ValueError(f"Native decode failed at {frame}")
            if requested_frames and frame not in requested_frames:
                continue
            night = frame >= NIGHT_INTERVAL[0]
            region = NIGHT_REGION if night else REGION
            donor_path = NIGHT_DONOR if night else DONOR
            layer = night_caption_layer() if night else dance_caption_layer()
            x0, y0, x1, y1 = region
            donor = cv2.imread(str(donor_path))[y0:y1, x0:x1]
            stable = layer["source_core"] & (layer["alpha"] >= .96)
            phase_audit.REGION = region
            candidate = next(c for c in candidates if c["start"] <= frame < c["end"])
            source_crop = current[y0:y1, x0:x1]
            stats = phase_audit.phase_stats(source_crop, donor, layer, stable)
            unsupported = warm_glyph_core(source_crop) & (layer["alpha"] == 0)
            marked = source_crop.copy()
            marked[unsupported] = (0, 0, 255)
            source_panels.append(panel([donor, source_crop], f"f{frame:04d}: {'f0911' if night else 'f0831'} DONOR | ACTUAL SEQUENTIAL SOURCE", 2))
            diagnostic_panels.append(panel([source_crop, marked], f"f{frame:04d}: ACTUAL SOURCE | RED = UNSUPPORTED WARM CANDIDATES (NOT GLYPHS)", 2))
            private = current.copy()
            private[y0:y1, x0:x1] = (35, 48, 68)
            simulation, simulation_mask = restore_dance_captions(private, current, frame)
            simulation_panels.append(panel([source_crop, simulation[y0:y1, x0:x1]], f"f{frame:04d}: ACTUAL SOURCE | REGISTERED TRANSPARENT LAYER OVER DARK", 2))
            source_file = OUT / f"f{frame:04d}-actual-source.png"
            cv2.imwrite(str(source_file), current)
            row = {"frame": frame, "source_pts": metadata["pts"][frame], "cel": candidate["cel"],
                   "source_reference": candidate["reference"], "source_png": str(source_file),
                   "source_png_sha256": sha(source_file), "actual_source_bgr_sha256": bgrsha(current),
                   "caption_region_xyxy": list(region), "registered_donor": str(donor_path),
                   "registered_donor_sha256": sha(donor_path), "phase_donor_sha256": layer["phase_donor_sha256"],
                   "registered_alpha_pixels": int(np.count_nonzero(layer["alpha"])),
                   "contrast_edge_support_pixels": int(np.count_nonzero(layer.get("contrast_edge_support", []))),
                   "contrast_edge_policy": layer.get("contrast_edge_policy", "not_enabled"),
                   "simulated_changes_outside_alpha": int(np.count_nonzero((simulation_mask[y0:y1, x0:x1] != 0) & (layer["alpha"] == 0))),
                   **stats}
            if candidate["cel"] in assets:
                anchor_frame, asset_path, anchor = assets[candidate["cel"]]
                generated = compositor.read_image(asset_path)
                reference = compositor.read_image(ROOT / anchor["reference"])
                capture = {}
                production_restore = compositor.restore_dance_captions

                def captured_restore(underlay, source, current_frame, character_mask=None):
                    before = underlay[y0:y1, x0:x1].copy()
                    edited = np.any(before != source_crop, axis=2)
                    halo = np.zeros(layer["alpha"].shape, bool)
                    new_character = np.zeros(halo.shape, bool)
                    if night and character_mask is not None:
                        new_character = character_mask[y0:y1, x0:x1] != 0
                        luma = before.astype(np.float32) @ np.array((.114, .587, .299), np.float32)
                        fg_luma = layer["foreground_bgr"] @ np.array((.114, .587, .299), np.float32)
                        color_gap = np.max(np.abs(before.astype(np.float32) - layer["foreground_bgr"]), axis=2)
                        halo = (layer["contrast_edge_support"] & edited & new_character
                                & (np.abs(luma - fg_luma) < 38) & (color_gap < 60))
                    restored, declared = production_restore(underlay, source, current_frame, character_mask)
                    after = restored[y0:y1, x0:x1]
                    changed = np.any(before != after, axis=2)
                    permitted = (layer["alpha"] > 0) | layer.get("contrast_edge_support", np.zeros(halo.shape, bool))
                    archive_path = OUT / f"f{frame:04d}-caption-masks.npz"
                    np.savez_compressed(archive_path, donor_alpha=layer["alpha"],
                                        predicted_1px_contrast_halo=halo, actual_new_character=new_character,
                                        actual_declared_caption_mask=declared[y0:y1, x0:x1],
                                        actual_caption_changed_pixels=changed, previously_untouched_source=~edited)
                    capture.update({"caption_mask_archive": str(archive_path), "caption_mask_archive_sha256": sha(archive_path),
                                    "predicted_1px_contrast_halo_pixels": int(np.count_nonzero(halo)),
                                    "predicted_halo_outside_explicit_new_subject_pixels": int(np.count_nonzero(halo & ~new_character)),
                                    "caption_restore_changed_outside_registered_alpha_or_1px_ring_pixels": int(np.count_nonzero(changed & ~permitted)),
                                    "caption_restore_previously_untouched_source_pixels_changed": int(np.count_nonzero(changed & ~edited))})
                    return restored, declared

                with patch.object(compositor, "restore_dance_captions", side_effect=captured_restore):
                    output, comparison, masks = compositor.compose(current, reference, generated,
                        candidate["source_transform"]["matrix"], anchor_frame, asset_path.name, frame)
                composite_file = OUT / f"f{frame:04d}-current-composite.png"
                mask_file = OUT / f"f{frame:04d}-current-masks.png"
                cv2.imwrite(str(composite_file), output)
                cv2.imwrite(str(mask_file), masks)
                composite_panels.append(panel([source_crop, output[y0:y1, x0:x1]], f"f{frame:04d}: ACTUAL SOURCE | CURRENT COMPOSITE {asset_path.name}", 2))
                actual_core = layer["source_core"] & warm_glyph_core(source_crop)
                if night:
                    actual_core &= np.max(np.abs(source_crop.astype(float) - layer["foreground_bgr"]), axis=2) <= 25
                core_delta = np.max(cv2.absdiff(source_crop, output[y0:y1, x0:x1]), axis=2)
                caption_mask = np.all(masks[y0:y1, x0:x1] == (245, 95, 180), axis=2)
                edge_painted = caption_mask & (layer["alpha"] == 0)
                permitted = (layer["alpha"] > 0) | layer.get("contrast_edge_support", np.zeros(layer["alpha"].shape, bool))
                row.update({"asset": str(asset_path), "asset_sha256": sha(asset_path), "asset_source_frame": anchor_frame,
                            **capture,
                            "composite_png": str(composite_file), "composite_png_sha256": sha(composite_file),
                            "composite_bgr_sha256": bgrsha(output),
                            "observed_stable_glyph_subset_pixels": int(np.count_nonzero(actual_core)),
                            "observed_stable_glyph_subset_not_source_exact_pixels": int(np.count_nonzero(actual_core & (core_delta != 0))),
                            "declared_caption_pixels_outside_alpha": int(np.count_nonzero(edge_painted)),
                            "declared_caption_pixels_outside_alpha_and_1px_edge": int(np.count_nonzero(caption_mask & ~permitted)),
                            "changed_outside_declared_masks": int(np.count_nonzero(np.any(output != current, axis=2) & np.all(masks == 0, axis=2)))})
                thumb = cv2.resize(comparison, (1280, 360), interpolation=cv2.INTER_AREA)
            else:
                row["missing_asset"] = True
                thumb = cv2.resize(current, (640, 360), interpolation=cv2.INTER_AREA)
            full_panels.append(panel([thumb], f"f{frame:04d}: SOURCE / CURRENT ASSET IF AVAILABLE"))
            rows.append(row)
        donor_frames = {911: NIGHT_DONOR, 914: NIGHT_PHASE_DONORS[0], 919: NIGHT_PHASE_DONORS[1]}
        for frame in range(END, 920):
            if frame not in donor_frames:
                if not cap.grab():
                    raise ValueError(f"Source ended before night donor at {frame}")
                continue
            ok, decoded = cap.read()
            if not ok:
                raise ValueError(f"Source donor decode failed at {frame}")
            reference = cv2.imread(str(donor_frames[frame]))
            donor_decodes.append({"frame": frame, "source_pts": metadata["pts"][frame],
                                  "actual_source_bgr_sha256": bgrsha(decoded),
                                  "donor_file": str(donor_frames[frame]), "donor_file_sha256": sha(donor_frames[frame]),
                                  "actual_decode_equals_donor_reference": bool(np.array_equal(decoded, reference))})
    finally:
        cap.release()
    report = {"scope_half_open": [START, END], "actual_source_count": len(rows),
              "requested_actual_frames": sorted(requested_frames) if requested_frames else list(range(START, END)),
              "production_interval_at_audit": list(SOURCE_INTERVAL), "night_interval_at_audit": list(NIGHT_INTERVAL),
              "old_donor": str(DONOR), "night_donor": str(NIGHT_DONOR),
              "old_donor_sha256": sha(DONOR), "night_donor_sha256": sha(NIGHT_DONOR),
              "source_video_sha256": metadata["sha256"],
              "additional_night_donor_actual_decodes": donor_decodes,
              "implementation_sha256": {str(p): sha(p) for p in [ROOT / "compose.py", ROOT / "dance_caption_layers.py", ROOT / "night_transition_layers.py", Path(__file__)]},
              "all_best_offsets_zero": all(r["best_local_offset_xy"] == [0, 0] for r in rows),
              "rows": rows, "source_caption_pages": page(source_panels, "source-caption"),
              "unsupported_pages": page(diagnostic_panels, "unsupported-candidates"),
              "registered_transparent_layer_simulation_pages": page(simulation_panels, "transparent-over-dark"),
              "current_composite_caption_pages": page(composite_panels, "current-composite-caption"),
              "full_pages": page(full_panels, "full-source-composite"),
              "artistic_acceptance": False, "original_speed_review": "not_performed",
              "actual_lyric_change_frame": 897,
              "asset_selection_status": "proposed QA composites only; global selections unchanged" if arguments.proposal else "current inventory resolution; not artistic acceptance",
              "proposal_file": str(arguments.proposal) if arguments.proposal else None,
              "proposal_sha256": sha(arguments.proposal) if arguments.proposal else None,
              "generic_foreground_condition": "For [831,897) OR [897,911), only dilated source yellow graphics are restored generically; registered glyph layers handle lyrics.",
              "contrast_edge_limit": "[897,911) only; fixed 1px dark edge derived from registered glyph support, edited pixels AND explicit new_subject character mask only, luminance gap <38 and max-channel gap <60. Core RGB/position untouched; edge is intentional reconstruction, not source-exact alpha.",
              "limits": ["Warm candidates include pale clothing/skin/AA, not only glyphs.",
                         "Local offset statistics do not prove source alpha or full glyph reproduction.",
                         "All full PNG source frames are actual native sequential decodes, not source-map approximations."]}
    report_path = OUT / "audit.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "actual_source_count": len(rows),
                      "all_best_offsets_zero": report["all_best_offsets_zero"],
                      "stable_p95": [r["stable_interior_p95_max_channel_delta"] for r in rows],
                      "assets": [r.get("asset") for r in rows]}, indent=2))


if __name__ == "__main__":
    main()
