"""Inspect every raw source-timed frame and emit all exposure-boundary contacts."""

import argparse
from functools import lru_cache
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from compose import compose, read_image, source_matches_metadata, validate_render_timing
from review_opening_preview import contact_pages, file_hash
from title_layers import registry, title_character_mask
from dance_caption_layers import CLEAR_INTERVAL, CLEAR_REGION, DONOR, PHASE_DONORS, REGION as DANCE_CAPTION_REGION, SOURCE_INTERVAL as DANCE_CAPTION_INTERVAL, dance_caption_layer, warm_glyph_core

ROOT = Path(__file__).resolve().parent


def caption_diagnostics(source, result, frame):
    fields = []
    if 38 <= frame < 210:
        fields.append(("left_lyric", (0, 350, 800, 840)))
    elif 210 <= frame < 287:
        fields.append(("left_lyric", (180, 495, 780, 635)))
    elif 287 <= frame < 323:
        rect = ((180, 470, 600, 545) if frame < 290 else
                (180, 205, 600, 340) if frame < 294 else (180, 290, 600, 380))
        fields.append(("moving_chinese", rect))
    elif 411 <= frame < 504:
        fields.append(("bottom_lyric", (700, 925, 1230, 1060)))
    elif 536 <= frame < 666:
        fields.append(("right_lyric", (1245, 495, 1830, 670)))
    rows = []
    for name, (x0, y0, x1, y1) in fields:
        original = source[y0:y1, x0:x1]
        rendered = result[y0:y1, x0:x1]
        h, s, v = cv2.split(cv2.cvtColor(original, cv2.COLOR_BGR2HSV))
        core = (((h >= 10) & (h <= 43) & (s < 65) & (v > 220))
                | ((s < 25) & (v > 230)))
        changed = np.max(cv2.absdiff(original, rendered), axis=2) > 30
        rows.append({"name": name, "rectangle": [x0, y0, x1, y1],
                     "source_bright_core_pixels": int(np.count_nonzero(core)),
                     "core_mismatch_gt30_pixels": int(np.count_nonzero(core & changed))})
    if 290 <= frame < 294:
        rows.append({"name": "source_exact_zoomed_bubble_interior",
                     "rectangle": [220, 390, 560, 550], "source_bright_core_pixels": 0,
                     "core_mismatch_gt30_pixels": 0,
                     "whole_region_mismatch_pixels": int(np.count_nonzero(np.any(
                         source[390:550, 220:560] != result[390:550, 220:560], axis=2)))})
    if CLEAR_INTERVAL[0] <= frame < CLEAR_INTERVAL[1]:
        x0, y0, x1, y1 = CLEAR_REGION
        rows.append({"name": "dance_source_exact_clear_phase", "rectangle": list(CLEAR_REGION),
                     "source_bright_core_pixels": 0, "core_mismatch_gt30_pixels": 0,
                     "whole_region_mismatch_pixels": int(np.count_nonzero(np.any(
                         source[y0:y1, x0:x1] != result[y0:y1, x0:x1], axis=2)))})
    if DANCE_CAPTION_INTERVAL[0] <= frame < DANCE_CAPTION_INTERVAL[1]:
        x0, y0, x1, y1 = DANCE_CAPTION_REGION
        original, rendered = source[y0:y1, x0:x1], result[y0:y1, x0:x1]
        layer = dance_caption_layer()
        current_core = warm_glyph_core(original)
        stable_core = layer["source_core"] & current_core
        changed = np.max(cv2.absdiff(original, rendered), axis=2) > 30
        rows.append({"name": "dance_stable_donor_lyric_subset", "rectangle": list(DANCE_CAPTION_REGION),
                     "source_bright_core_pixels": int(np.count_nonzero(stable_core)),
                     "core_mismatch_gt30_pixels": int(np.count_nonzero(stable_core & changed)),
                     "current_warm_candidates_outside_donor_alpha_pixels": int(np.count_nonzero(
                         current_core & (layer["alpha"] == 0))),
                     "scope": "stable donor subset only; not full glyph or contrast acceptance",
                     "alpha_reconstructed": True})
    return rows


def review(timeline_path, output):
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    mapping = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    validate_render_timing(timeline, metadata)
    start, end = timeline.get("source_start", 0), timeline.get("source_start", 0)+timeline["frames"]
    if not source_matches_metadata(Path(timeline["source"]), metadata):
        raise ValueError("Source identity changed")
    expected = [{"start": max(s["start"], start), "end": min(s["end"], end), "cel": s["cel"]}
                for s in mapping["source_exposures"] if s["start"] < end and s["end"] > start]
    exposures, assets = timeline["output_exposures"], timeline["assets"]
    actual = [{key: s[key] for key in ("start", "end", "cel")} for s in exposures]
    paths = [timeline_path, ROOT/"review_interval.py", ROOT/"compose.py", ROOT/"title_layers.py", ROOT/"title_layer_registry.json",
             ROOT/"opening_clock_layers.py", ROOT/"caption_layers.py", ROOT/"source_map.json", ROOT/"source_aliases.json"]
    dance_in_interval = start < DANCE_CAPTION_INTERVAL[1] and end > DANCE_CAPTION_INTERVAL[0]
    dance_phase_path = ROOT/"qa/dance-caption-worker/phase-and-layer-audit.json"
    if dance_in_interval:
        paths += [ROOT/"dance_caption_layers.py", DONOR, *PHASE_DONORS, dance_phase_path]
    if start < CLEAR_INTERVAL[1] and end > CLEAR_INTERVAL[0]:
        paths += [ROOT/"dance_caption_layers.py", ROOT/"qa/pre831-caption/pre831-caption-audit.json"]
    paths += [ROOT/assets[cel]["path"] for cel in {e["cel"] for e in exposures}]
    provenance = {str(p.resolve()): file_hash(p) for p in paths}
    starts, boundaries = [], []
    for i, exposure in enumerate(exposures):
        frame, cel = exposure["start"], exposure["cel"]
        label = f"f{frame:04d} | {metadata['pts'][frame]:.3f}s | {cel} | {Path(assets[cel]['path']).name}"
        starts.append({"frame": frame, "cel": cel, "label": "START "+label})
        if i:
            previous = exposures[i-1]
            before = frame-1
            boundaries += [{"frame": before, "cel": previous["cel"], "label": f"BEFORE f{before:04d} | {previous['cel']}"},
                           {"frame": frame, "cel": cel, "label": "AFTER "+label}]
    samples = {r["frame"] for r in starts+boundaries}
    thumbnails, rows = {}, []

    @lru_cache(maxsize=8)
    def load(cel):
        asset = assets[cel]
        return read_image(ROOT/asset["source_reference"]), read_image(ROOT/asset["path"])

    cap = cv2.VideoCapture(timeline["source"])
    for frame in range(start):
        if not cap.grab():
            raise ValueError("Source ended before interval")
    index = 0
    try:
        for frame in range(start, end):
            ok, source = cap.read()
            if not ok:
                raise ValueError(f"Source ended at {frame}")
            while frame >= exposures[index]["end"]:
                index += 1
            exposure = exposures[index]
            cel, asset = exposure["cel"], assets[exposure["cel"]]
            reference, generated = load(cel)
            result, _, masks = compose(source, reference, generated, exposure["source_matrix"],
                                       asset["source_frame"], Path(asset["path"]).name, frame)
            outside = np.all(masks == 0, axis=2)
            mismatch = int(np.count_nonzero(np.any(source != result, axis=2) & outside))
            row = {"frame": frame, "cel": cel, "asset": asset["path"],
                   "outside_declared_edit_region_mismatch_pixels": mismatch}
            row["audited_caption_fields"] = caption_diagnostics(source, result, frame)
            if Path(asset["path"]).name in registry()["assets"]:
                original_mask, new_mask = title_character_mask(source), title_character_mask(generated)
                row["floor_delta_pixels"] = int(np.nonzero(new_mask)[0].max()-np.nonzero(original_mask)[0].max())
                row["peripheral_text_region_mismatch_pixels"] = (
                    int(np.count_nonzero(np.any(result[:, :680] != source[:, :680], axis=2)))
                    + int(np.count_nonzero(np.any(result[:, 1250:] != source[:, 1250:], axis=2))))
            rows.append(row)
            if frame in samples:
                panels = [cv2.resize(img, (640, 360), interpolation=cv2.INTER_AREA) for img in (source, result)]
                thumbnails[frame] = Image.fromarray(cv2.cvtColor(np.concatenate(panels, axis=1), cv2.COLOR_BGR2RGB))
    finally:
        cap.release()
    output.mkdir(parents=True, exist_ok=True)
    contacts = {"exposure_starts": contact_pages(starts, thumbnails, output, "exposure-starts"),
                "boundary_pairs": contact_pages(boundaries, thumbnails, output, "boundary-pairs")}
    checks = {"exact_original_exposure_spans": expected == actual,
              "all_interval_raw_frames_checked": len(rows) == end-start,
              "source_equal_outside_declared_edits": all(r["outside_declared_edit_region_mismatch_pixels"] == 0 for r in rows),
              "registered_title_peripheral_text_exact": all(r.get("peripheral_text_region_mismatch_pixels", 0) == 0 for r in rows),
              "audited_opening_caption_cores_clear": all(
                  f["core_mismatch_gt30_pixels"] == 0 and f.get("whole_region_mismatch_pixels", 0) == 0
                  for r in rows for f in r["audited_caption_fields"]
                  if not f["name"].startswith("dance_")),
              "audited_dance_clear_phase_source_exact": all(
                  f["whole_region_mismatch_pixels"] == 0
                  for r in rows for f in r["audited_caption_fields"]
                  if f["name"] == "dance_source_exact_clear_phase"),
              "audited_dance_stable_caption_subset_clear": all(
                  f["core_mismatch_gt30_pixels"] == 0
                  for r in rows for f in r["audited_caption_fields"]
                  if f["name"] == "dance_stable_donor_lyric_subset"),
              "inputs_unchanged": all(file_hash(Path(p)) == digest for p, digest in provenance.items())}
    report = {"source_interval": [start, end], "frames": rows, "checks": checks,
              "contacts": contacts, "provenance_sha256": provenance,
              "technical_static_pass": all(checks.values()), "artistic_acceptance": False,
              "original_speed_watch": "not_performed", "manual_contact_review": "pending",
              "limitations": ["Reduced static contacts cannot establish actual-speed artistic acceptance.",
                              "Caption checks cover registered opening fields, the source-exact clear dance phase and the later stable-donor subset; source clocks, other text, complete glyph shapes and final encoded contrast require separate review.",
                              "Dance AA and the hidden plate are reconstructed. Some current warm candidates lie outside donor alpha; those include clothing and unresolved Japanese/star-edge candidates, not an all-glyph pass.",
                              "Declared edit-region equality does not validate the matte's artistic boundary.",
                              "Floor differences are diagnostics, not an acceptance threshold."]}
    if dance_in_interval:
        phase = json.loads(dance_phase_path.read_text(encoding="utf-8"))
        report["dance_caption_phase_diagnostic"] = {
            "report": str(dance_phase_path.resolve()),
            "source_interval": phase["source_interval"],
            "registered_source_frame_count": phase["registered_source_frame_count"],
            "all_registered_source_frames_checked": phase["all_registered_source_frames_checked"],
            "all_registered_current_warm_core_inside_donor_alpha": phase["all_registered_current_warm_core_inside_donor_alpha"],
            "legacy_32_fields_scope": phase["legacy_32_fields_scope"],
            "all_32_source_frames_checked": phase["all_32_source_frames_checked"],
            "all_32_current_warm_core_inside_donor_alpha": phase["all_32_current_warm_core_inside_donor_alpha"],
            "artistic_acceptance": False,
            "meaning": "Diagnostic candidates are not all classified; a stable-subset technical pass is not full-caption acceptance."}
    (output/"review-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"interval": [start, end], "technical_static_pass": report["technical_static_pass"],
                      "exposures": len(exposures), "pages": sum(map(len, contacts.values())),
                      "report": str((output/"review-report.json").resolve())}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cv2.setNumThreads(2)
    review(args.timeline, args.output)
