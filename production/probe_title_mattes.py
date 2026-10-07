"""Inspect scene-scoped line mattes before enabling title compositing."""

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from compose import read_image
from review_fullpv_root_repairs import REPAIRS
from title_layers import title_character_mask

ROOT = Path(__file__).resolve().parent


def main():
    source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    by_frame = {c["frame"]: c for c in source_map["cels"]}
    target = ROOT / "qa/title-mattes-probe"
    target.mkdir(exist_ok=True)
    panels = []
    records = []
    for frame, name in REPAIRS.items():
        if frame < 1300:
            continue
        pair = []
        for role, path in [("source", ROOT / by_frame[frame]["reference"]),
                           ("generated", ROOT / "generated" / name)]:
            image = read_image(path)
            mask = title_character_mask(image)
            points = cv2.findNonZero(mask)
            x, y, w, h = cv2.boundingRect(points)
            records.append({"frame": frame, "role": role, "bbox": [x, y, x+w, y+h]})
            preview = image.copy()
            preview[mask == 0] = preview[mask == 0] // 3
            cv2.imwrite(str(target / f"f{frame:04d}-{role}-mask.png"), mask)
            pair.append(preview)
        panels.append(Image.fromarray(cv2.cvtColor(np.concatenate(pair, axis=1), cv2.COLOR_BGR2RGB)).resize((1280, 360)))
    sheet = Image.new("RGB", (1280, len(panels)*392), "#222226")
    draw = ImageDraw.Draw(sheet)
    for index, panel in enumerate(panels):
        draw.text((12, index*392+8), f"f{records[index*2]['frame']:04d} SOURCE / GENERATED SEMANTIC MATTE PROBE", fill="white")
        sheet.paste(panel, (0, index*392+32))
    sheet.save(target / "contacts.jpg", quality=94)
    (target / "report.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(records))


if __name__ == "__main__":
    main()
