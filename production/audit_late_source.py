"""Inspect late source drawings without counting title lettering as character motion."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".python_deps"))
import cv2
import numpy as np
from PIL import Image, ImageDraw
from group_source import measure
from rigid_source import similarity


def title_mask(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hue, sat, val = cv2.split(hsv)
    warm = ((hue <= 19) & (sat >= 40) & (val >= 50)) | (val < 150)
    roi = np.zeros(warm.shape, np.uint8)
    roi[200:835, 700:1240] = warm[200:835, 700:1240]
    roi = cv2.morphologyEx(roi, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(roi)
    if contours:
        cv2.drawContours(mask, [max(contours, key=cv2.contourArea)], -1, 1, -1)
    return cv2.dilate(mask, np.ones((5, 5), np.uint8))


def main():
    data = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    cels = [c for c in data["cels"] if c["family"] == "seated_title_credits"]
    items = []
    prior = None
    proof = []
    for cel in cels:
        frame = cel["frame"]
        current = cv2.imread(str(ROOT / cel["reference"]))
        mask = title_mask(current)
        crop = current[215:805, 725:1195]
        items.append((frame, Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))))
        if prior:
            pcel, previous, pmask = prior
            rigid = similarity(previous, current, pmask, mask)
            proof.append({"before": pcel["frame"], "after": frame,
                          "direct": measure(previous, current, pmask, mask),
                          "similarity": rigid,
                          "note": "Character-only source mask; excludes pale title and credits."})
        prior = cel, current, mask
    canvas = Image.new("RGB", (470 * 5, 620 * 6), "#25252a")
    draw = ImageDraw.Draw(canvas)
    for index, (frame, crop) in enumerate(items):
        x, y = (index % 5) * 470, (index // 5) * 620
        draw.text((x + 10, y + 8), f"SOURCE f{frame:04d}", fill="white")
        canvas.paste(crop, (x, y + 30))
    out = ROOT / "qa" / "late-title-source-audit.jpg"
    canvas.save(out, quality=93)
    (ROOT / "qa" / "late-title-source-audit.json").write_text(
        json.dumps(proof, indent=2), encoding="utf-8")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
