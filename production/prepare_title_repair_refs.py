"""Crop identity-only references and actual source deltas for title repairs."""

import json
from pathlib import Path

from PIL import Image

from delta_reference import make_delta

ROOT = Path(__file__).resolve().parent


def main():
    target = ROOT / "qa/title-repair-v6"
    target.mkdir(exist_ok=True)
    current = Image.open(ROOT / "generated/fine-f1309.png").convert("RGB").resize((1920, 1080))
    current.crop((720, 515, 1140, 795)).save(target / "costume-only.png")
    source = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    lookup = {row["frame"]: row for row in source["cels"]}
    before = 1309
    for frame in (1314, 1319, 1329, 1335, 1342, 1347):
        image = Image.open(ROOT / lookup[frame]["reference"]).convert("RGB")
        image.crop((740, 235, 1180, 510)).save(target / f"source-head-f{frame:04d}.png")
        make_delta(ROOT / lookup[before]["reference"], ROOT / lookup[frame]["reference"],
                   target / f"source-delta-f{before:04d}-f{frame:04d}.png")
        before = frame


if __name__ == "__main__":
    main()
