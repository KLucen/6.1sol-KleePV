"""Explicit current source/new-draft static references; no shared-state writes."""

from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FRAMES = (856, 863, 868, 873, 880)
EXPLICIT = {
    863: "root-continuation-f0863-hair-v2.png",
    868: "root-continuation-f0868-v1.png",
    873: "root-continuation-f0873-v1.png",
    880: "root-continuation-f0880-v1.png",
}
BOXES = (
    ("head-mouth-hair-collar", (500, 70, 1290, 635)),
    ("hands-cuffs-arms", (250, 65, 1370, 795)),
    ("hip-leg-overlap-boots", (540, 595, 1340, 1080)),
)
HELPER_PATH = ROOT / "qa/root-dance-continuation/make_explicit_neighbor_contacts.py"
spec = importlib.util.spec_from_file_location("prior_private_contact_helper", HELPER_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def identity(path):
    raw = path.read_bytes()
    image = Image.open(path).convert("RGB")
    return {
        "path": str(path), "file_sha256": sha256(raw).hexdigest(),
        "native_size_wh": list(image.size),
        "native_rgb_pixel_sha256": sha256(np.asarray(image).tobytes()).hexdigest(),
    }


def local_board(before_source, current_source, before_draft, current_draft, frame):
    images = (before_source, current_source, before_draft, current_draft)
    board = Image.new("RGB", (2400, 1410), "#242426")
    draw = ImageDraw.Draw(board)
    for row, (role, box) in enumerate(BOXES):
        for column, (im, label) in enumerate(zip(images, ("SOURCE BEFORE", "SOURCE CURRENT", "KLEE BEFORE", "KLEE CURRENT"))):
            crop = im.crop(box)
            crop.thumbnail((584, 420), Image.Resampling.LANCZOS)
            x, y = column * 600, row * 470
            draw.text((x + 8, y + 8), role + " " + label, fill="white")
            board.paste(crop, (x + (600 - crop.width) // 2, y + 34))
    path = OUT / f"f{frame:04d}-new-selected-local-static-contact.png"
    board.save(path)
    return path


def main():
    manifest_path = ROOT / "full-pv-progress-manifest.json"
    selection_path = ROOT / "asset_selections.json"
    manifest_bytes, selection_bytes = manifest_path.read_bytes(), selection_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    selections = json.loads(selection_bytes.decode("utf-8"))["selections"]
    rows = {r["canonical_source_frame"]: r for r in manifest["cels"] if r["canonical_source_frame"] in FRAMES}
    drafts, sources, frame_evidence = {}, {}, []
    for frame in FRAMES:
        row = rows[frame]
        if frame == 856:
            draft_path = ROOT / row["selected_asset"]["path"]
        else:
            draft_path = ROOT / "generated" / EXPLICIT[frame]
        selection_matches = [s for s in selections if s["source_frame"] == frame and Path(s["path"]).name == draft_path.name]
        if not selection_matches or selection_matches[-1].get("accepted") is not False:
            raise ValueError(f"Expected explicit unaccepted draft selection missing for f{frame}")
        source_path = ROOT / row["source_reference"]
        original = Image.open(draft_path).convert("RGB")
        drafts[frame] = original.resize((1920, 1080), Image.Resampling.LANCZOS)
        sources[frame] = Image.open(source_path).convert("RGB")
        frame_evidence.append({
            "frame": frame, "cel": row["cel"],
            "source_exposures": row["source_exposures"],
            "source": identity(source_path), "draft": identity(draft_path),
            "draft_canvas_normalization": {"target_size_wh": [1920, 1080], "resampling": "PIL LANCZOS", "alignment": "whole-frame scaling only; no pose registration or warping"},
            "explicit_asset_selection_snapshot": selection_matches[-1],
            "manifest_selection_snapshot": row.get("selected_asset"),
            "manifest_selected_path_matches_explicit_draft": bool(row.get("selected_asset") and Path(row["selected_asset"]["path"]).name == draft_path.name),
            "artistically_accepted": False,
        })
    group = Image.new("RGB", (3000, 780), "#242426")
    draw = ImageDraw.Draw(group)
    for i, frame in enumerate(FRAMES):
        x = i * 600
        draw.text((x + 8, 8), f"SOURCE f{frame:04d}", fill="white")
        draw.text((x + 8, 398), f"EXPLICIT UNACCEPTED KLEE f{frame:04d}", fill="white")
        group.paste(sources[frame].resize((600, 338), Image.Resampling.LANCZOS), (x, 30))
        group.paste(drafts[frame].resize((600, 338), Image.Resampling.LANCZOS), (x, 420))
    group_path = OUT / "f0856-f0880-explicit-new-source-draft-group.png"
    group.save(group_path)

    pairs = []
    for before, current in zip(FRAMES[:-1], FRAMES[1:]):
        panels = [sources[before], sources[current], drafts[before], drafts[current],
                  helper.contours([sources[before], sources[current]]), helper.contours([drafts[before], drafts[current]])]
        labels = [f"SOURCE BEFORE f{before}", f"SOURCE CURRENT f{current}",
                  f"EXPLICIT KLEE BEFORE f{before}", f"EXPLICIT KLEE CURRENT f{current}",
                  "SOURCE CONTOURS blue before / red current", "DRAFT CONTOURS blue before / red current"]
        board = Image.new("RGB", (1920, 1740), "#242426")
        draw = ImageDraw.Draw(board)
        for i, (panel, label) in enumerate(zip(panels, labels)):
            x, y = i % 2 * 960, i // 2 * 580
            draw.text((x + 8, y + 8), label, fill="white")
            board.paste(panel.resize((960, 540), Image.Resampling.LANCZOS), (x, y + 30))
        board_path = OUT / f"f{current:04d}-new-selected-neighbor-static-contact.png"
        board.save(board_path)
        local_path = local_board(sources[before], sources[current], drafts[before], drafts[current], current)
        delta_path = OUT / f"f{current:04d}-source-ab-rgb-contours.png"
        if not delta_path.exists():
            raise FileNotFoundError("Required actual source RGB/2D delta evidence missing: " + str(delta_path))
        pairs.append({
            "before_frame": before, "current_frame": current,
            "neighbor_source_and_draft_board": str(board_path),
            "local_source_and_draft_board": str(local_path),
            "actual_source_rgb_contour_reference": identity(delta_path),
            "original_source_delta_metrics": str(delta_path.with_suffix(".json")),
            "local_boxes_xyxy": [{"role": role, "box": list(box)} for role, box in BOXES],
        })
        crop_boxes = (("head-mouth-hair-collar", (500, 70, 1290, 635)),
                      ("legs-boots", (540, 595, 1340, 1080)),
                      ("torso-costume", (460, 260, 1210, 800)))
        for role, box in crop_boxes:
            pair = Image.new("RGB", ((box[2] - box[0]) * 2, box[3] - box[1] + 24), "white")
            pair.paste(sources[current].crop(box), (0, 24))
            pair.paste(drafts[current].crop(box), (box[2] - box[0], 24))
            ImageDraw.Draw(pair).text((5, 5), f"f{current} CURRENT SOURCE | EXPLICIT DRAFT NORMALIZED TO NATIVE; {role}", fill="black")
            path = OUT / f"f{current:04d}-new-source-draft-{role}.png"
            pair.save(path)
            pairs[-1].setdefault("native_scale_current_detail_pairs", []).append(str(path))
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Source/native-normalized draft static comparisons of explicit f856,863,868,873,880 only",
        "manifest_snapshot_utc": manifest["snapshot_utc"],
        "manifest_file_sha256_at_read": sha256(manifest_bytes).hexdigest(),
        "selection_file_sha256_at_read": sha256(selection_bytes).hexdigest(),
        "explicit_new_paths_authorized_by_parent": True,
        "selection_state_modified": False, "production_core_modified": False,
        "source_aliases_added": False, "artistically_accepted": False,
        "actual_speed_playback_performed": False,
        "group_contact": str(group_path), "frames": frame_evidence, "neighbor_pairs": pairs,
        "static_review": "pending viewing and written findings; generated references are not an acceptance test",
        "limitations": ["Native-normalized generated images are not actual source-resolved output composites.",
                        "Static silhouette comparisons do not verify exposure timing or full-speed motion.",
                        "Source stars, yellow sparkle drawings and captions also appear in full-frame contours; not every edge is character anatomy.",
                        "Manifest can lag saved asset_selections; explicit parent-specified new drafts and saved unaccepted selection entries were checked directly."]}
    findings = OUT / "new-cels-static-findings.json"
    if findings.exists():
        report["static_review"] = json.loads(findings.read_text(encoding="utf-8"))
    report_path = OUT / "new-cels-static-review.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "group": str(group_path), "pairs": pairs}, indent=2))


if __name__ == "__main__":
    main()
