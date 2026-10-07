"""Full-resolution spatial proof for specific candidate source-copy pairs."""

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from title_layers import title_character_mask

ROOT = Path(__file__).resolve().parent
PAIRS = [(1309, 1375), (1314, 1380)]


def main():
    mapping = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    refs = {c["frame"]: ROOT/c["reference"] for c in mapping["cels"]}
    target = ROOT / "qa/title-source-copy-audit"
    target.mkdir(exist_ok=True)
    records = []
    for before, after in PAIRS:
        a, b = cv2.imread(str(refs[before])), cv2.imread(str(refs[after]))
        ma, mb = title_character_mask(a), title_character_mask(b)
        interior = cv2.erode(ma & mb, np.ones((13, 13), np.uint8))
        d = cv2.absdiff(a, b)
        coherent = ((d.max(axis=2) > 28) & (interior != 0)).astype(np.uint8)
        _, _, stats, _ = cv2.connectedComponentsWithStats(coherent, 8)
        amplified = cv2.convertScaleAbs(d, alpha=4)
        amplified[interior == 0] = 0
        overlay = np.full_like(a, 255)
        for image, color in [(a, (255, 100, 30)), (b, (30, 60, 255))]:
            lines = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) < 130
            overlay[lines & ((ma|mb) != 0)] = color
        crop = (slice(235, 800), slice(730, 1180))
        panels = [a[crop], b[crop], amplified[crop], overlay[crop]]
        board = Image.new("RGB", (900, 1190), "#222226")
        draw = ImageDraw.Draw(board)
        for index, image in enumerate(panels):
            x, y = index%2*450, index//2*595
            draw.text((x+8, y+8), [f"SOURCE f{before}", f"SOURCE f{after}", "INTERIOR RGB DIFFERENCE x4", "DARK LINE OVERLAY NO TRANSFORM"][index], fill="white")
            board.paste(Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)), (x, y+30))
        board.save(target / f"f{before}-f{after}.png")
        entry = {"before": before, "after": after,
                 "interior_pixels_delta_28": int(coherent.sum()),
                 "largest_interior_difference_component": int(stats[1:, 4].max(initial=0)),
                 "interior_mean_rgb_max_delta": float(d.max(axis=2)[interior != 0].mean()),
                 "proof": f"qa/title-source-copy-audit/f{before}-f{after}.png",
                 "review": "pending_manual_source_character_details"}
        records.append(entry)
        for role, box in [("eyes", (slice(350, 450), slice(805, 1005))),
                          ("sleeves", (slice(465, 590), slice(785, 1075))),
                          ("boots", (slice(680, 795), slice(740, 1070)))]:
            pair = np.concatenate([a[box], b[box], amplified[box]], axis=1)
            cv2.imwrite(str(target / f"f{before}-f{after}-{role}.png"), cv2.resize(pair, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST))
    (target / "report.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(records))


if __name__ == "__main__":
    main()
