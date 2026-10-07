"""Same-canvas source/generated inspection, not synthesis or interpolation."""

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from audit_late_source import title_mask
from compose import read_image, subject_mask

ROOT = Path(__file__).resolve().parent
FRAMES = [1286, 1296, 1301, 1309, 1314, 1319, 1329, 1335, 1342, 1347]


def bounds(mask):
    y, x = np.nonzero(mask)
    return [int(x.min()), int(y.min()), int(x.max() + 1), int(y.max() + 1)]


def main():
    source = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    refs = {c["frame"]: ROOT / c["reference"] for c in source["cels"]}
    canvas = Image.new("RGB", (600 * 5, 850 * 2), "#25252a")
    draw = ImageDraw.Draw(canvas)
    records = []
    for index, frame in enumerate(FRAMES):
        src = read_image(refs[frame])
        filename = f"fine-f{frame:04d}.png"
        if frame == 1314:
            filename = "fine-f1314-v1.png"
        generated = ROOT / "generated" / filename
        gen = read_image(generated)
        sb = bounds(title_mask(src))
        gb = bounds(subject_mask(gen))
        record = {
            "frame": frame,
            "source": str(refs[frame]),
            "generated": str(generated),
            "normalized_canvas": [1920, 1080],
            "source_character_bbox": sb,
            "generated_character_bbox": gb,
            "floor_delta_pixels": gb[3] - sb[3],
            "note": "Bounding boxes are diagnostics, not an artistic pass; hats differ by character design.",
        }
        records.append(record)
        x, y = (index % 5) * 600, (index // 5) * 850
        draw.text((x + 12, y + 8), f"f{frame:04d}: SOURCE / KLEE CANDIDATE", fill="white")
        for offset, img in [(35, src), (440, gen)]:
            crop = img[190:835, 665:1260]
            preview = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            preview.thumbnail((580, 390))
            canvas.paste(preview, (x + 10, y + offset))
        draw.text((x + 12, y + 831), f"floor delta {record['floor_delta_pixels']:+d}px", fill="white")
    (ROOT / "qa" / "title-completion-static.jpg").parent.mkdir(exist_ok=True)
    canvas.save(ROOT / "qa" / "title-completion-static.jpg", quality=94)
    (ROOT / "qa" / "title-completion-static.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
