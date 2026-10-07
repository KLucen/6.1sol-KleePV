"""Decode actual source drawings and create source-only prompt evidence."""

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

TARGETS = (887, 889, 903, 907, 908, 909)
DANCE_BOXES = [
    ("small-head-eyes-mouth", (900, 180, 1200, 540)),
    ("raised-hand-cuff", (680, 70, 960, 400)),
    ("lower-hand-cuff", (1090, 470, 1340, 730)),
    ("legs-boots-caption", (650, 620, 1270, 1080)),
    ("foreground-face-crop", (1040, 0, 1920, 850)),
]
TRANSITION_BOXES = [
    ("foreground-head-hat-crop", (0, 0, 1300, 1080)),
    ("foreground-eyes-mouth", (0, 240, 1000, 960)),
    ("rear-night-profile-head", (850, 0, 1510, 930)),
    ("coat-hair-caption-occlusion", (0, 730, 1370, 1080)),
    ("left-edge-previous-background", (0, 0, 280, 1080)),
]


def local_board(before, current, output, boxes):
    arrays = [cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB) for p in (before, current)]
    difference = np.abs(arrays[0].astype(np.int16) - arrays[1].astype(np.int16))
    edges = [cv2.Canny(a, 80, 160) for a in arrays]
    overlay = np.full_like(arrays[0], 245)
    overlay[edges[0] != 0] = (30, 110, 235)
    overlay[edges[1] != 0] = (235, 80, 30)
    overlay[(edges[0] != 0) & (edges[1] != 0)] = (50, 50, 50)
    panels = [Image.fromarray(a) for a in arrays]
    panels += [Image.fromarray(np.minimum(difference * 4, 255).astype(np.uint8)), Image.fromarray(overlay)]
    board = Image.new("RGB", (2000, len(boxes) * 400), "#242426")
    draw = ImageDraw.Draw(board)
    for row, (label, box) in enumerate(boxes):
        for col, (panel, role) in enumerate(zip(panels, ("SOURCE A", "CURRENT B", "ACTUAL RGB x4", "BLUE A / RED B"))):
            crop = panel.crop(box)
            crop.thumbnail((480, 350))
            x, y = col * 500, row * 400
            draw.text((x + 8, y + 8), label + " " + role, fill="white")
            board.paste(crop, (x + (500 - crop.width) // 2, y + 36))
    board.save(output)
    return {
        "path": str(output),
        "sha256": sha256(output.read_bytes()).hexdigest(),
        "actual_pixels_max_rgb_gt_28": int((difference.max(axis=2) > 28).sum()),
        "box_roles": [{"role": role, "xyxy": list(box)} for role, box in boxes],
    }


def main():
    manifest_path = ROOT / "full-pv-progress-manifest.json"
    map_path = ROOT / "source_map.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_map = json.loads(map_path.read_text(encoding="utf-8"))
    rows = manifest["cels"]
    pairs = {}
    for frame in TARGETS:
        index = next(i for i, row in enumerate(rows) if row["canonical_source_frame"] == frame)
        pairs[frame] = (rows[index - 1], rows[index])
    needed = {r["canonical_source_frame"] for pair in pairs.values() for r in pair}
    needed.update((880, 891, 900, 905, 911))
    cap = cv2.VideoCapture(source_map["source"])
    decoded = {}
    for frame in range(max(needed) + 1):
        ok, bgr = cap.read()
        if not ok:
            raise RuntimeError(f"Source decode failed at frame {frame}")
        if frame in needed:
            path = QA / f"f{frame:04d}-source-actual.png"
            if not cv2.imwrite(str(path), bgr):
                raise RuntimeError(f"PNG save failed: {path}")
            decoded[frame] = {
                "path": str(path), "shape_bgr": list(bgr.shape),
                "decoded_bgr_sha256": sha256(bgr.tobytes()).hexdigest(),
                "png_sha256": sha256(path.read_bytes()).hexdigest(),
            }
    cap.release()
    queue = []
    for frame, (before, target) in pairs.items():
        before_frame = before["canonical_source_frame"]
        before_path, current_path = (Path(decoded[f]["path"]) for f in (before_frame, frame))
        expected_ref = ROOT / target["source_reference"]
        current = cv2.imread(str(current_path))
        equal = bool(np.array_equal(current, cv2.imread(str(expected_ref))))
        if not equal:
            raise RuntimeError(f"Actual sequential frame differs from canonical source reference f{frame}")
        delta_path = QA / f"f{before_frame:04d}-f{frame:04d}-source-ab-rgb-contours.png"
        make_delta(before_path, current_path, delta_path)
        boxes = DANCE_BOXES if frame < 900 else TRANSITION_BOXES
        local = local_board(before_path, current_path, QA / f"f{frame:04d}-source-local-ab.png", boxes)
        crops = []
        rgb = Image.fromarray(cv2.cvtColor(current, cv2.COLOR_BGR2RGB))
        for role, box in boxes:
            crop_path = QA / f"f{frame:04d}-source-{role}.png"
            rgb.crop(box).save(crop_path)
            crops.append({"role": role, "xyxy": list(box), "path": str(crop_path), "sha256": sha256(crop_path.read_bytes()).hexdigest()})
        candidates = [c for c in source_map["candidates"] if c["cel"] == target["cel"]]
        queue.append({
            "source_frame": frame, "cel": target["cel"],
            "current_source": decoded[frame],
            "canonical_reference": str(expected_ref),
            "actual_frame_equals_canonical_reference": equal,
            "actual_preceding_cel_frame": before_frame,
            "actual_preceding_source": decoded[before_frame],
            "source_exposures": target["source_exposures"],
            "source_candidate_ids": [c["id"] for c in candidates],
            "selected_asset_at_snapshot": target["selected_asset"],
            "delta_path": str(delta_path), "delta_sha256": sha256(delta_path.read_bytes()).hexdigest(),
            "local_board": local, "current_source_crops": crops,
            "alias_created": False, "artwork_generated": False,
        })
        output = {
            "scope": "Six missing strict-source dance cels, source references only",
            "source": source_map["source"],
            "source_map_sha256": sha256(map_path.read_bytes()).hexdigest(),
            "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
            "source_sequential_decode_range": [0, max(needed) + 1],
            "source_decoded_frames": decoded,
            "queue": queue,
            "exposure_changed": False, "global_selection_changed": False,
            "artwork_generated": False, "manual_source_review": "pending",
        }
        (QA / "missing-source-reference-queue.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(json.dumps({"ready_frame": frame, "before": before_frame, "source": str(current_path), "delta": str(delta_path)}), flush=True)


if __name__ == "__main__":
    main()
