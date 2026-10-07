"""Prepare original-only reference crops and source-delta evidence for clock cels."""

import json
from pathlib import Path

import cv2

from compose import read_image
from delta_reference import make_delta


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "qa/root-held-clock-worker"
FRAMES = [58, 63, 68, 75, 79, 83, 87, 91, 95, 99, 117, 121, 125, 129, 133]


def main():
    OUT.mkdir(exist_ok=True)
    mapping = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    sources = {c["frame"]: c["reference"] for c in mapping["cels"]}
    rows = []
    previous = 54
    for frame in FRAMES:
        source = read_image(ROOT / sources[frame])
        bounds = (845, 160, 1620, 660)
        x0, y0, x1, y1 = bounds
        crop_path = OUT / f"f{frame:04d}-source-clock-hands-face.png"
        cv2.imwrite(str(crop_path), source[y0:y1, x0:x1])
        delta_path = OUT / f"f{previous:04d}-f{frame:04d}-source-delta.png"
        make_delta(ROOT / sources[previous], ROOT / sources[frame], delta_path)
        rows.append({"frame": frame, "source": sources[frame], "crop": crop_path.relative_to(ROOT).as_posix(),
                     "delta": delta_path.relative_to(ROOT).as_posix(), "accepted": False})
        previous = frame
    (OUT / "source-reference-queue.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps({"frames": FRAMES, "output": str(OUT)}))


if __name__ == "__main__":
    main()
