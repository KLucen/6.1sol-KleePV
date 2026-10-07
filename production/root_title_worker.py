"""Traceable references and save records for the remaining seated title cels."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

from delta_reference import make_delta

ROOT = Path(__file__).resolve().parent
QA = ROOT / "qa/root-title-worker"
FRAMES = [1352, 1375, 1380, 1403, 1404, 1409, 1414, 1424, 1429, 1437, 1442, 1447, 1457, 1463, 1497]


def prepare():
    QA.mkdir(exist_ok=True)
    costume = Image.open(ROOT / "generated/fine-f1314-arms-eyes-v7.png").convert("RGB").resize((1920, 1080))
    costume.crop((720, 520, 1140, 795)).save(QA / "costume-hidden-hands.png")
    mapping = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    by_frame = {c["frame"]: c for c in mapping["cels"]}
    prior = 1347
    for frame in FRAMES:
        image = Image.open(ROOT / by_frame[frame]["reference"]).convert("RGB")
        image.crop((740, 235, 1180, 510)).save(QA / f"source-head-f{frame:04d}.png")
        make_delta(ROOT / by_frame[prior]["reference"], ROOT / by_frame[frame]["reference"],
                   QA / f"source-delta-f{prior:04d}-f{frame:04d}.png")
        prior = frame
    for offset in range(0, len(FRAMES), 6):
        batch = FRAMES[offset:offset+6]
        board = Image.new("RGB", (1200, len(batch)*320), "#222226")
        draw = ImageDraw.Draw(board)
        for index, frame in enumerate(batch):
            source = Image.open(ROOT / by_frame[frame]["reference"]).convert("RGB")
            draw.text((12, index*320+8), f"SOURCE CURRENT f{frame:04d}", fill="white")
            board.paste(source.resize((540, 304)), (0, index*320+16))
            board.paste(source.crop((730, 230, 1180, 800)).resize((240, 304)), (620, index*320+16))
        board.save(QA / f"source-page-{offset//6+1:02d}.jpg", quality=94)


def save(frame, original, name, prompt, references):
    target = ROOT / "generated" / name
    if target.exists():
        raise FileExistsError(target)
    shutil.copy2(original, target)
    mapping = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    cel = next(c for c in mapping["cels"] if c["frame"] == frame)
    row = {"source_frame": frame, "cel": cel["cel"], "family": cel["family"],
           "tool": "builtin_imagegen", "prompt": prompt, "references": references,
           "output": f"generated/{name}", "original_tool_output": original,
           "output_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
           "status": "generated_draft_unaccepted", "accepted": False,
           "review": "single_cel_static_inspected_source_background_layer_and_temporal_pending",
           "original_speed_watch": "not_performed"}
    (ROOT / "jobs" / f"{target.stem}.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare"])
    args = parser.parse_args()
    prepare()
