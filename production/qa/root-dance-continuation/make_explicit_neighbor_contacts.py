"""Complete private neighbor boards without modifying shared selection state."""
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
FRAMES = (827, 831, 835, 839, 843, 848, 852, 856)


def contours(images):
    edges = [cv2.Canny(np.asarray(im), 80, 160) for im in images]
    overlay = np.full((1080, 1920, 3), 245, dtype=np.uint8)
    overlay[edges[0] != 0] = (30, 110, 235)
    overlay[edges[1] != 0] = (235, 80, 30)
    overlay[(edges[0] != 0) & (edges[1] != 0)] = (50, 50, 50)
    return Image.fromarray(overlay)


def main():
    manifest_path = ROOT / "full-pv-progress-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest["cels"]
    evidence = []
    group = Image.new("RGB", (2400, 1560), "#242426")
    group_draw = ImageDraw.Draw(group)
    for position, frame in enumerate(FRAMES):
        column, group_row = position % 4, position // 4
        index = next(i for i, row in enumerate(rows) if row["canonical_source_frame"] == frame)
        current, before = rows[index], rows[index - 1]
        before_frame = before["canonical_source_frame"]
        draft_paths = [ROOT / row["selected_asset"]["path"] for row in (before, current)]
        drafts = [Image.open(path).convert("RGB").resize((1920, 1080)) for path in draft_paths]
        source_paths = [ROOT / row["source_reference"] for row in (before, current)]
        sources = [Image.open(path).convert("RGB") for path in source_paths]
        panels = sources + drafts + [contours(sources), contours(drafts)]
        board = Image.new("RGB", (1920, 1740), "#242426")
        board_draw = ImageDraw.Draw(board)
        labels = [
            f"SOURCE BEFORE f{before_frame}", f"SOURCE CURRENT f{frame}",
            f"SELECTED KLEE BEFORE f{before_frame}", f"SELECTED KLEE CURRENT f{frame}",
            "SOURCE CONTOURS blue before / red current", "KLEE CONTOURS blue before / red current",
        ]
        for i, (panel, label) in enumerate(zip(panels, labels)):
            x, y = i % 2 * 960, i // 2 * 580
            board_draw.text((x + 8, y + 8), label, fill="white")
            board.paste(panel.resize((960, 540)), (x, y + 30))
        output = QA / f"f{frame:04d}-preferred-v2-neighbor-static-contact.jpg"
        board.save(output, quality=94)
        source_path = ROOT / current["source_reference"]
        source = Image.open(source_path).convert("RGB")
        offset_y = group_row * 780
        group_draw.text((column * 600 + 8, offset_y + 8), f"SOURCE f{frame}", fill="white")
        group_draw.text((column * 600 + 8, offset_y + 398), f"PREFERRED KLEE DRAFT f{frame}", fill="white")
        group.paste(source.resize((600, 338)), (column * 600, offset_y + 30))
        group.paste(drafts[1].resize((600, 338)), (column * 600, offset_y + 420))
        evidence.append({
            "frame": frame,
            "source_before_frame": before_frame,
            "source_before": str(ROOT / before["source_reference"]),
            "source_current": str(source_path),
            "draft_before": str(draft_paths[0]),
            "draft_current": str(draft_paths[1]),
            "draft_sha256": [sha256(path.read_bytes()).hexdigest() for path in draft_paths],
            "explicit_neighbor_board": str(output),
            "current_selection_review": current["selected_asset"].get("selection_review"),
            "current_selection_known_issues": current["selected_asset"].get("selection_known_issues"),
            "drafts_resolved_from_latest_manifest_selections": True,
            "accepted": False,
        })
    group_path = QA / "f0827-f0856-preferred-v2-source-and-draft-group.jpg"
    group.save(group_path, quality=95)
    report = {
        "scope": "Static source and generated-draft neighbors only",
        "shared_selections_modified": False,
        "core_files_modified": False,
        "artistically_accepted": False,
        "actual_speed_playback_performed": False,
        "manifest_snapshot_utc": manifest["snapshot_utc"],
        "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        "selection_file_sha256": sha256((ROOT / "asset_selections.json").read_bytes()).hexdigest(),
        "limitation": "Static source/current preferred-draft comparisons only. Current and preceding draft assets resolve from the latest progress manifest; no exposure changes, selected asset edits or artistic acceptance are made here.",
        "group_contact": str(group_path),
        "evidence": evidence,
    }
    path = QA / "f0827-f0856-preferred-v2-static-evidence.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "group": str(group_path), "boards": [item["explicit_neighbor_board"] for item in evidence]}))


if __name__ == "__main__":
    main()
