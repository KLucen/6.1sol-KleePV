"""Static source/composite checks for the root's explicitly selected repairs."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from compose import compose, read_image, subject_mask
from title_layers import checked_layers, registry

ROOT = Path(__file__).resolve().parent
REPAIRS = {
    129: "fine-f0129-hair-repair-v2.png",
    133: "fine-f0133-hair-repair-v2.png",
    167: "fine-f0167-sleeve-repair-v2.png",
    1314: "fine-f1314-arms-eyes-v7.png",
    1319: "fine-f1319-source-native-v2.png",
    1329: "fine-f1329-source-native-v2.png",
    1335: "fine-f1335-source-native-v2.png",
    1342: "fine-f1342-source-native-v2.png",
    1347: "fine-f1347-source-native-v2.png",
}


def bbox(mask):
    points = cv2.findNonZero(mask)
    if points is None:
        return None
    x, y, w, h = cv2.boundingRect(points)
    return [x, y, x + w, y + h]


def main():
    target = ROOT / "qa/fullpv-root-repairs"
    target.mkdir(exist_ok=True)
    source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    by_frame = {c["frame"]: c for c in source_map["cels"]}
    report = {"scope": "single cel plus chronological static source/composite review",
              "artistic_acceptance": False, "original_speed_watch": "not_performed",
              "warning": "Color-based bounding boxes are diagnostics, not semantic or artistic passes.",
              "assets": []}
    panels = []
    for frame, filename in REPAIRS.items():
        row = by_frame[frame]
        source_path, asset_path = ROOT / row["reference"], ROOT / "generated" / filename
        src, gen = read_image(source_path), read_image(asset_path)
        old, new = subject_mask(src), subject_mask(gen)
        if filename in registry()["assets"]:
            _, old, new, _, _ = checked_layers(filename)
        out, comparison, diagnostic = compose(src, src, gen, asset_source_frame=frame,
                                               asset_name=filename, current_frame=frame)
        outside = (old | new) == 0
        old_bbox, new_bbox = bbox(old), bbox(new)
        entry = {"frame": frame, "cel": row["cel"], "source": row["reference"],
                 "asset": f"generated/{filename}", "sha256": hashlib.sha256(asset_path.read_bytes()).hexdigest(),
                 "source_mask_bbox": old_bbox, "generated_mask_bbox": new_bbox,
                 "mask_kind": "registered_title" if filename in registry()["assets"] else "color_heuristic",
                 "floor_delta_pixels": new_bbox[3] - old_bbox[3] if old_bbox and new_bbox else None,
                 "outside_subject_union_changed_pixels": int(np.count_nonzero(np.any(out != src, axis=2) & outside)),
                 "accepted": False, "review": "static_inspected_temporal_pending"}
        report["assets"].append(entry)
        cv2.imwrite(str(target / f"f{frame:04d}-comparison.jpg"), comparison)
        cv2.imwrite(str(target / f"f{frame:04d}-masks.png"), diagnostic)
        cv2.imwrite(str(target / f"f{frame:04d}-composite.png"), out)
        image = Image.fromarray(cv2.cvtColor(comparison, cv2.COLOR_BGR2RGB)).resize((1280, 360))
        panels.append((frame, filename, image))
    for page, start in enumerate(range(0, len(panels), 4), 1):
        rows = panels[start:start + 4]
        sheet = Image.new("RGB", (1280, len(rows) * 392), "#202024")
        draw = ImageDraw.Draw(sheet)
        for index, (frame, filename, image) in enumerate(rows):
            y = index * 392
            draw.text((12, y + 8), f"SOURCE / COMPOSITE f{frame:04d} | {filename} | STATIC DRAFT", fill="white")
            sheet.paste(image, (0, y + 32))
        sheet.save(target / f"contacts-{page:02d}.jpg", quality=92)
    (target / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"assets": len(panels), "report": str(target / "report.json"),
                      "floor_deltas": {str(a["frame"]): a["floor_delta_pixels"] for a in report["assets"]}}))


if __name__ == "__main__":
    main()
