"""Assemble existing source and artwork files for read-only static QA."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
PAIRS = [
    (887, "fast-fullpv-dance-f0887-v1.png", "new"),
    (889, "fast-fullpv-dance-f0889-hair-v2.png", "new"),
    (891, "candidate-025-clean.png", "existing_neighbor"),
    (902, "candidate-029-clean.png", "existing_neighbor"),
    (903, "fast-fullpv-dance-f0903-v1.png", "new"),
    (905, "candidate-030-clean.png", "existing_neighbor"),
    (907, "fast-fullpv-dance-f0907-v1.png", "new"),
    (908, "fast-fullpv-dance-f0908-v1.png", "new"),
    (909, "fast-fullpv-dance-f0909-v1.png", "new"),
]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1")
    parser.add_argument("--frames", type=int, nargs="+")
    parser.add_argument("--source-repairs", action="store_true")
    args = parser.parse_args()
    frames = []
    for frame, filename, ownership in PAIRS:
        if args.frames and frame not in args.frames:
            continue
        if args.source_repairs and frame in (891, 907):
            filename = f"fast-fullpv-dance-f{frame:04d}-source-v2.png"
            ownership = "new_source_led_repair"
        gen = ROOT / "generated" / filename
        if not gen.exists():
            continue
        src = QA / f"f{frame:04d}-source-actual.png"
        if not src.exists():
            raise RuntimeError(f"Actual source missing for {frame}")
        out = QA / f"f{frame:04d}-source-generated-static-{args.version}.png"
        board = Image.new("RGB", (3840, 1120), "#242426")
        draw = ImageDraw.Draw(board)
        for col, path, role in ((0, src, "ACTUAL SOURCE"), (1, gen, "GENERATED DRAFT")):
            image = Image.open(path).convert("RGB")
            image.thumbnail((1920, 1080))
            if path == gen:
                image = image.resize((1920, 1080), Image.Resampling.LANCZOS)
            draw.text((col * 1920 + 12, 10), f"f{frame} {role} {path.name}", fill="white")
            board.paste(image, (col * 1920, 40))
        board.save(out)
        frames.append({
            "source_frame": frame, "ownership": ownership,
            "source_path": str(src), "source_sha256": digest(src),
            "generated_path": str(gen), "generated_sha256": digest(gen),
            "source_size": list(Image.open(src).size),
            "generated_size": list(Image.open(gen).size),
            "pair_board_path": str(out), "pair_board_sha256": digest(out),
        })
    overview = Image.new("RGB", (1920, len(frames) * 575), "#242426")
    for row, record in enumerate(frames):
        board = Image.open(record["pair_board_path"]).convert("RGB")
        board.thumbnail((1920, 560))
        overview.paste(board, (0, row * 575))
    overview_path = QA / f"static-source-generated-contact-{args.version}.png"
    overview.save(overview_path)
    report = {
        "scope": "Reference contact sheets only, not artwork edits or acceptance",
        "normalization": "Generated draft is resized to 1920x1080 for QA side-by-side only; source pixels not edited",
        "manual_review": "not implied by contact construction",
        "global_selection_changed": False, "generation_called": False,
        "artistic_acceptance": False,
        "overview": str(overview_path), "overview_sha256": digest(overview_path),
        "pairs": frames,
    }
    report_path = QA / f"static-contact-evidence-{args.version}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"contact": str(overview_path), "evidence": str(report_path), "pairs": len(frames)}))


if __name__ == "__main__":
    main()
