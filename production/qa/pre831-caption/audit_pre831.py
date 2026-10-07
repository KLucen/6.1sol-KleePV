"""Source/selected/raw-composite evidence for the unregistered pre-f831 lyric."""

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
from compose import compose, read_image, source_matches_metadata
from dance_caption_layers import warm_glyph_core
from restoration_plan import (CHINESE_FIELD, JAPANESE_FIELD, PROPOSED_RECT,
                              apply_proposed_source_restore)

FRAMES = (812, 814, 815, 819, 823, 827)
BOTTOM = (820, 870, 1380, 1072)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crop(image, rect):
    x0, y0, x1, y1 = rect
    return image[y0:y1, x0:x1]


def make_board(images, labels):
    panels = []
    for image, label in zip(images, labels):
        panel = Image.new("RGB", (image.shape[1], image.shape[0]+24), "white")
        panel.paste(Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)), (0, 24))
        ImageDraw.Draw(panel).text((4, 5), label, fill="black")
        panels.append(panel)
    out = Image.new("RGB", (sum(p.width for p in panels), panels[0].height), "white")
    left = 0
    for panel in panels:
        out.paste(panel, (left, 0))
        left += panel.width
    return out


def main():
    cv2.setNumThreads(2)
    metadata_path = ROOT/"source_meta.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source_path = Path(metadata["source"])
    if not source_matches_metadata(source_path, metadata):
        raise ValueError("Source identity mismatch")
    timeline_path = ROOT/"timeline-opening-35s958-draft-v7.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    selections = json.loads((ROOT/"asset_selections.json").read_text(encoding="utf-8"))["selections"]
    selected = {row["source_frame"]: row for row in selections}
    paths = [ROOT/name for name in ("compose.py", "caption_layers.py", "dance_caption_layers.py", "asset_selections.json")]
    paths.extend([timeline_path, metadata_path, OUT/"restoration_plan.py"])
    for frame in FRAMES:
        paths.append(ROOT/selected[frame]["path"])
    provenance = {str(path): sha(path) for path in paths}
    cap = cv2.VideoCapture(str(source_path))
    sources = {}
    try:
        for frame in range(810):
            if not cap.grab():
                raise ValueError("Source ended before interval")
        for frame in range(810, 832):
            ok, source = cap.read()
            if not ok:
                raise ValueError("Source ended inside interval")
            sources[frame] = source
    finally:
        cap.release()
    assets = timeline["assets"]
    loaded = {}
    rows = []
    for frame in range(812, 831):
        exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = assets[exposure["cel"]]
        selected_row = selected[asset["source_frame"]]
        if selected_row["path"] != asset["path"]:
            raise ValueError("V7 timeline differs from current selected cel")
        if exposure["cel"] not in loaded:
            loaded[exposure["cel"]] = (read_image(ROOT/asset["source_reference"]), read_image(ROOT/asset["path"]))
        reference, generated = loaded[exposure["cel"]]
        source = sources[frame]
        current, _, _ = compose(source, reference, generated, exposure["source_matrix"],
                                asset["source_frame"], Path(asset["path"]).name, frame)
        proposed, declared = apply_proposed_source_restore(current.copy(), source, frame)
        fields = []
        for name, rect in (("Japanese", JAPANESE_FIELD), ("Chinese", CHINESE_FIELD)):
            original, rendered = crop(source, rect), crop(current, rect)
            core = warm_glyph_core(original)
            differences = np.max(cv2.absdiff(original, rendered), axis=2)
            baseline = crop(sources[812], rect)
            donor_core = warm_glyph_core(baseline)
            offsets = []
            padded = cv2.copyMakeBorder(original, 2, 2, 2, 2, cv2.BORDER_REFLECT)
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    shifted = padded[2+dy:2+dy+original.shape[0], 2+dx:2+dx+original.shape[1]]
                    error = np.max(cv2.absdiff(baseline, shifted), axis=2)[donor_core].mean()
                    offsets.append((float(error), dx, dy))
            fields.append({"name": name, "rectangle": list(rect),
                           "warm_source_core_pixels": int(core.sum()),
                           "current_core_mismatch_gt30_pixels": int(np.count_nonzero(core & (differences > 30))),
                           "best_source_offset_xy": list(min(offsets)[1:]),
                           "source_core_bbox_xyxy": ([int(np.nonzero(core)[1].min()+rect[0]),
                                                       int(np.nonzero(core)[0].min()+rect[1]),
                                                       int(np.nonzero(core)[1].max()+rect[0]+1),
                                                       int(np.nonzero(core)[0].max()+rect[1]+1)] if np.any(core) else None)})
        changed = np.any(proposed != current, axis=2)
        row = {"frame": frame, "cel": exposure["cel"], "selected_path": asset["path"],
               "fields": fields, "proposed_crop_source_exact": bool(np.array_equal(crop(proposed, PROPOSED_RECT), crop(source, PROPOSED_RECT))),
               "proposed_changed_pixels": int(changed.sum()),
               "proposed_undeclared_changed_pixels": int(np.count_nonzero(changed & (declared == 0)))}
        rows.append(row)
        if frame in FRAMES:
            full_path = OUT/f"f{frame:04d}-source-selected-current-full.png"
            make_board([cv2.resize(image, (640, 360), interpolation=cv2.INTER_AREA) for image in (source, generated, current)],
                       ["SOURCE (1/3 SIZE)", "SELECTED (1/3 SIZE)", "CURRENT COMPOSITE (1/3 SIZE)"]).save(full_path)
            row["full_board"] = str(full_path)
        if frame in FRAMES or frame >= 827:
            path = OUT/f"f{frame:04d}-native-bottom-source-selected-current-proposed.png"
            make_board([crop(image, BOTTOM) for image in (source, generated, current, proposed)],
                       [f"f{frame} SOURCE", "SELECTED", "CURRENT COMPOSITE", "PRIVATE SOURCE-RECT PROPOSAL"]).save(path)
            row["native_bottom_board"] = str(path)
    make_board([crop(sources[frame], (820, 930, 1150, 1060)) for frame in (810, 811, 812, 830, 831)],
               [f"SOURCE f{frame:04d}" for frame in (810, 811, 812, 830, 831)]).save(OUT/"source-phase-boundaries-native.png")
    report = {"audited_source_interval": [812, 831], "source_sha256": metadata["sha256"],
              "safe_rect_proposal": list(PROPOSED_RECT), "frames": rows,
              "all_19_source_frames_checked": len(rows) == 19,
              "all_source_best_offsets_zero": all(f["best_source_offset_xy"] == [0,0] for r in rows for f in r["fields"]),
              "all_proposed_crops_source_exact": all(r["proposed_crop_source_exact"] for r in rows),
              "all_proposed_changes_declared": all(r["proposed_undeclared_changed_pixels"] == 0 for r in rows),
              "provenance_sha256": provenance,
              "inputs_unchanged": all(sha(Path(path)) == digest for path, digest in provenance.items()),
              "manual_character_clearance": "pending_full_board_review_not_inferred_from_subject_mask",
              "artistic_acceptance": False, "original_speed_watch": "not_performed",
              "phase_note": "Same lyric is present on f810/811 over a macro human/effect. f812 is a cut/safe-region start, not its first lyrical occurrence; f831 changes text. No safe source-rectangle rule is proposed before f812."}
    (OUT/"pre831-caption-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(OUT/"pre831-caption-audit.json"),
                      "frames": [{"frame": r["frame"], "mismatches": [f["current_core_mismatch_gt30_pixels"] for f in r["fields"]],
                                  "offsets": [f["best_source_offset_xy"] for f in r["fields"]]} for r in rows],
                      "safe_rect_proposal": list(PROPOSED_RECT), "inputs_unchanged": report["inputs_unchanged"]}, indent=2))


if __name__ == "__main__":
    main()
