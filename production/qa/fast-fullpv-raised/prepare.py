"""Private source evidence for shot 13; does not alter shared selections."""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta

HERE = Path(__file__).resolve().parent
FRAMES = [1225, 1229, 1234, 1241, 1248, 1256, 1261, 1264, 1267,
          1270, 1274, 1278, 1282]
MISSING = [f for f in FRAMES if f not in (1261, 1270)]


def source(frame):
    return next((ROOT / "source_refs").glob(f"*-f{frame:04d}.png"))


def main():
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    plan = []
    for index, frame in enumerate(FRAMES):
        cel = next(x for x in manifest["cels"] if x["canonical_source_frame"] == frame)
        previous = FRAMES[index - 1] if index else 1221
        delta = HERE / f"source-delta-f{previous:04d}-f{frame:04d}.png"
        if frame in MISSING:
            make_delta(source(previous), source(frame), delta)
        plan.append({"source_frame": frame, "cel": cel["cel"],
                     "source_reference": str(source(frame)), "previous_source_frame": previous,
                     "source_exposures": cel["source_exposures"],
                     "source_delta_reference": str(delta) if frame in MISSING else None,
                     "existing_asset": cel["selected_asset"], "missing": frame in MISSING})
    canvas = Image.new("RGB", (1920, 4 * 410), "#202024")
    draw = ImageDraw.Draw(canvas)
    for i, frame in enumerate(FRAMES):
        x, y = (i % 4) * 480, (i // 4) * 410
        draw.text((x + 12, y + 10), f"source f{frame:04d}", fill="white")
        im = Image.open(source(frame)).convert("RGB")
        im.thumbnail((480, 270))
        canvas.paste(im, (x, y + 35))
        detail = Image.open(source(frame)).crop((650, 200, 1300, 750))
        detail.thumbnail((130, 105))
        canvas.paste(detail, (x + 175, y + 307))
    canvas.save(HERE / "canonical-source-board.jpg")
    (HERE / "source-plan.json").write_text(json.dumps({
        "owner": "raised_closeup_batch", "mode": "strict_source", "accepted": False,
        "generation_order": [1225, 1256, 1282, 1229, 1234, 1241, 1248, 1264, 1267, 1274, 1278],
        "cels": plan}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
