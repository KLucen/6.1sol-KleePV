"""Source-only geometry evidence for the two initial title pose repairs."""

import json
from pathlib import Path

from PIL import Image
from delta_reference import make_delta

ROOT = Path(__file__).resolve().parent
refs = {c["frame"]: ROOT/c["reference"] for c in json.loads((ROOT/"source_map.json").read_text(encoding="utf-8"))["cels"]}
target = ROOT/"qa/root-title-worker"
for previous, frame in [(1286, 1296), (1296, 1301)]:
    Image.open(refs[frame]).convert("RGB").crop((740, 235, 1180, 510)).save(target/f"source-head-f{frame:04d}.png")
    make_delta(refs[previous], refs[frame], target/f"source-delta-f{previous:04d}-f{frame:04d}.png")
