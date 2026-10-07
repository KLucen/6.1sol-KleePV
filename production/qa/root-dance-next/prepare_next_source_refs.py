"""Build next-cel source QA references; no artwork, alias or selection edits."""
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta

FRAMES = (863, 868, 873, 880)
BOXES = [
    ("head-eyelids-mouth", (520, 150, 1250, 620)),
    ("hands-cuffs", (250, 70, 1350, 680)),
    ("legs-boots-caption-contact", (580, 620, 1330, 1080)),
]


def make_local(before_path, target_path, output):
    images = [Image.open(path).convert("RGB") for path in (before_path, target_path)]
    arrays = [np.asarray(im) for im in images]
    difference = np.abs(arrays[0].astype(np.int16) - arrays[1].astype(np.int16))
    rgb_x4 = np.minimum(difference * 4, 255).astype(np.uint8)
    edges = [cv2.Canny(arr, 80, 160) for arr in arrays]
    overlay = np.full_like(arrays[0], 245)
    overlay[edges[0] != 0] = (30, 110, 235)
    overlay[edges[1] != 0] = (235, 80, 30)
    overlay[(edges[0] != 0) & (edges[1] != 0)] = (50, 50, 50)
    panels = images + [Image.fromarray(rgb_x4), Image.fromarray(overlay)]
    contact = Image.new("RGB", (2400, 1290), "#242426")
    draw = ImageDraw.Draw(contact)
    for row, (label, box) in enumerate(BOXES):
        for column, (panel, role) in enumerate(zip(panels, ["SOURCE BEFORE", "CURRENT SOURCE", "ACTUAL RGB x4", "BLUE BEFORE / RED CURRENT"])):
            crop = panel.crop(box)
            crop.thumbnail((580, 380))
            x, y = column * 600, row * 430
            draw.text((x + 8, y + 8), label + " " + role, fill="white")
            contact.paste(crop, (x + (600 - crop.width) // 2, y + 36))
    contact.save(output)
    max_rgb = difference.max(axis=2)
    return {
        "pixels_max_rgb_delta_gt_28": int(np.count_nonzero(max_rgb > 28)),
        "pixels_max_rgb_delta_gte_28": int(np.count_nonzero(max_rgb >= 28)),
        "max_rgb_delta": int(max_rgb.max()),
        "local_board": str(output),
        "local_crops_xyxy": [{"role": label, "box": list(box)} for label, box in BOXES],
    }


def main():
    manifest_path = ROOT / "full-pv-progress-manifest.json"
    source_map_path = ROOT / "source_map.json"
    coverage_path = ROOT / "full-pv-coverage-report.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    rows = manifest["cels"]
    anchor = next(row for row in rows if row["canonical_source_frame"] == 856)
    anchor_path = ROOT / anchor["source_reference"]
    planned = []
    for frame in FRAMES:
        index = next(i for i, row in enumerate(rows) if row["canonical_source_frame"] == frame)
        target, before = rows[index], rows[index - 1]
        before_path, target_path = [ROOT / row["source_reference"] for row in (before, target)]
        source_candidates = [c for c in source_map["candidates"] if c["cel"] == target["cel"]]
        expected = [(e["start"], e["end"]) for e in target["source_exposures"]]
        actual = [(c["start"], c["end"]) for c in source_candidates]
        if len(expected) != 1 or not actual or min(a[0] for a in actual) != expected[0][0] or max(a[1] for a in actual) != expected[0][1]:
            raise ValueError(f"Unexpected exposure range for f{frame}")
        if any(c["source_transform"]["kind"] != "identity" for c in source_candidates):
            raise ValueError(f"Nonidentity source candidate for f{frame}; do not silently approximate")
        delta_path = QA / f"f{frame:04d}-source-ab-rgb-contours.png"
        make_delta(before_path, target_path, delta_path)
        metric = make_local(before_path, target_path, QA / f"f{frame:04d}-source-local-ab.png")
        current_image = Image.open(target_path).convert("RGB")
        crops = []
        for label, box in BOXES:
            path = QA / f"f{frame:04d}-source-{label}.png"
            current_image.crop(box).save(path)
            crops.append({"role": label, "path": str(path), "box": list(box)})
        anchor_delta = None
        if before["canonical_source_frame"] != 856:
            anchor_delta = QA / f"f0856-to-f{frame:04d}-source-ab-rgb-contours.png"
            make_delta(anchor_path, target_path, anchor_delta)
        planned.append({
            "frame": frame, "cel": target["cel"],
            "source_candidate": target["source_candidate"],
            "source_reference": str(target_path),
            "source_sha256": sha256(target_path.read_bytes()).hexdigest(),
            "source_size": list(current_image.size),
            "source_before_frame": before["canonical_source_frame"],
            "source_before": str(before_path),
            "source_exposures": target["source_exposures"],
            "source_frames_covered": target["source_frames_covered"],
            "source_map_candidates": [{k: c[k] for k in ("id", "frame", "start", "end", "pts", "end_pts", "cel", "reference", "source_transform")} for c in source_candidates],
            "selected_asset_at_snapshot": target.get("selected_asset"),
            "status_at_snapshot": target["status"],
            "neighbor_ab_rgb_contours": str(delta_path),
            "anchor_856_ab_rgb_contours": str(anchor_delta or delta_path),
            "neighbor_difference": metric,
            "crops": crops,
            "approved_alias": False,
            "artistically_accepted": False,
        })
    caption_frames = (856, 862, 863, 867, 868, 872, 873, 879, 880)
    caption_box = (650, 935, 1180, 1070)
    caption_board = Image.new("RGB", (1590, 465), "#242426")
    draw = ImageDraw.Draw(caption_board)
    for i, frame in enumerate(caption_frames):
        candidate = next(c for c in source_map["candidates"] if c["frame"] == frame)
        source_path = ROOT / candidate["reference"]
        x, y = i % 3 * 530, i // 3 * 155
        draw.text((x + 8, y + 5), f"SOURCE f{frame} - caption phase; crop {caption_box}", fill="white")
        caption_board.paste(Image.open(source_path).convert("RGB").crop(caption_box), (x, y + 20))
    caption_path = QA / "f0856-f0880-source-caption-phase-contact.png"
    caption_board.save(caption_path)
    result = {
        "scope": "Source-only preparation of four retained target cels, not artwork or alias approval",
        "manifest_snapshot_utc": manifest["snapshot_utc"],
        "source_map_sha256": sha256(source_map_path.read_bytes()).hexdigest(),
        "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        "coverage_snapshot_utc": coverage["snapshot_utc"],
        "coverage_summary": coverage["summary"],
        "full_cel_count_is_conservative_upper_bound": True,
        "source_map_candidate_ranges_cross_checked": True,
        "shared_selections_modified": False,
        "core_files_modified": False,
        "generation_called": False,
        "aliases_created": False,
        "caption_phase_contact": str(caption_path),
        "queue": planned,
        "limitations": [
            "Whole-frame RGB counts also include stars, captions and compression; numbers alone do not establish drawing uniqueness.",
            "This preparation retains the existing strict-source cel/exposure mapping and does not create aliases.",
            "Full generated artwork, composited all-frame masks, and original-speed playback are still unperformed for these missing cels.",
        ],
    }
    output = QA / "next-source-reference-queue.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"queue": str(output), "caption": str(caption_path), "frames": FRAMES}))


if __name__ == "__main__":
    main()
