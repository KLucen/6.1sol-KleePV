"""Visual source-cel differences for drawing prompts, never animation interpolation."""

from pathlib import Path
import argparse
import json

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent


def make_delta(before, after, output):
    a, b = (cv2.imread(str(path)) for path in (before, after))
    if a is None or b is None or a.shape != b.shape:
        raise ValueError("Source references must decode to the same canvas")
    h, w = a.shape[:2]
    diff = cv2.absdiff(a, b)
    contrast = np.minimum(diff.astype(np.uint16) * 4, 255).astype(np.uint8)
    ea = cv2.Canny(a, 80, 160)
    eb = cv2.Canny(b, 80, 160)
    overlay = np.full_like(a, 245)
    overlay[ea != 0] = (235, 110, 30)
    overlay[eb != 0] = (30, 80, 235)
    overlay[(ea != 0) & (eb != 0)] = (50, 50, 50)
    canvas = Image.new("RGB", (w * 2, h * 2 + 80), "#202024")
    draw = ImageDraw.Draw(canvas)
    panels = [(a, "BEFORE source cel", 0, 0), (b, "CURRENT TARGET source cel", w, 0),
              (contrast, "Actual RGB difference x4", 0, h + 40),
              (overlay, "Contours: blue before / red current", w, h + 40)]
    for panel, title, x, y in panels:
        draw.text((x + 15, y + 12), title, fill="white")
        canvas.paste(Image.fromarray(cv2.cvtColor(panel, cv2.COLOR_BGR2RGB)), (x, y + 40))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    metric = {"before": str(before), "current": str(after), "reference": str(output),
              "role": "Source spatial differences only; not artwork or motion synthesis",
              "max_delta": int(diff.max()), "pixels_delta_28": int((diff.max(axis=2) >= 28).sum())}
    output.with_suffix(".json").write_text(json.dumps(metric, indent=2), encoding="utf-8")
    print(json.dumps(metric))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    make_delta(args.before, args.current, args.output)
