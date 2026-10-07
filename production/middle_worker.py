"""Source references and traceable draft records for the middle PV batch."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

from delta_reference import make_delta

ROOT = Path(__file__).resolve().parent
QA = ROOT / "qa" / "fullpv-middle"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory():
    data = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    return [cel for cel in data["cels"] if 1500 <= cel["canonical_source_frame"] < 2400]


def prepare():
    QA.mkdir(parents=True, exist_ok=True)
    rows = inventory()
    by_family = {}
    for row in rows:
        by_family.setdefault(row["canonical_family"], []).append(row)
    for family, group in by_family.items():
        directory = QA / family
        directory.mkdir(exist_ok=True)
        for offset in range(0, len(group), 8):
            page = group[offset:offset + 8]
            board = Image.new("RGB", (1280, 392 * len(page)), "#202024")
            draw = ImageDraw.Draw(board)
            for i, row in enumerate(page):
                source = ROOT / row["source_reference"]
                frame = row["canonical_source_frame"]
                draw.text((12, i * 392 + 8), f"f{frame:04d} {row['cel']} {family}", fill="white")
                board.paste(Image.open(source).convert("RGB").resize((640, 360)), (0, i * 392 + 32))
                selected = row["selected_asset"]
                if selected:
                    board.paste(Image.open(ROOT / selected["path"]).convert("RGB").resize((640, 360)), (640, i * 392 + 32))
            board.save(directory / f"source-page-{offset // 8 + 1:02d}.jpg")
        for previous, current in zip(group, group[1:]):
            a, b = previous["canonical_source_frame"], current["canonical_source_frame"]
            out = directory / f"source-delta-f{a:04d}-f{b:04d}.png"
            if not out.exists():
                make_delta(ROOT / previous["source_reference"], ROOT / current["source_reference"], out)
    (QA / "queue.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


def save(frame, original, output):
    target = ROOT / "generated" / output
    if target.exists():
        raise FileExistsError(target)
    shutil.copy2(original, target)
    image = Image.open(target).convert("RGB")
    if image.size != (1920, 1080):
        image.resize((1920, 1080), Image.Resampling.LANCZOS).save(target)
    for path in (ROOT / "jobs").glob(f"fullpv-middle-f{frame}*.json"):
        job = json.loads(path.read_text(encoding="utf-8"))
        if Path(job["output"]).name == output:
            job.update({"status": "generated_draft_unaccepted", "original_tool_output": str(original),
                        "output_sha256": sha(target), "output_canvas": [1920, 1080],
                        "tool_canvas": list(image.size), "artistic_accepted": False,
                        "actual_speed_review": "not_performed"})
            path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(target), "sha256": sha(target), "original_canvas": image.size}))


def board(frames):
    rows = {row["canonical_source_frame"]: row for row in inventory()}
    page = Image.new("RGB", (1920, len(frames) * 564), "#202024")
    draw = ImageDraw.Draw(page)
    for i, frame in enumerate(frames):
        row = rows[frame]
        draw.text((12, i * 564 + 8), f"f{frame:04d} source left / draft right; static only", fill="white")
        page.paste(Image.open(ROOT / row["source_reference"]).resize((960, 540)), (0, i * 564 + 24))
        candidates = [p for p in (ROOT / "generated").glob(f"fine-f{frame:04d}*.png") if "rejected" not in p.name]
        if candidates:
            latest = max(candidates, key=lambda p: p.stat().st_mtime_ns)
            page.paste(Image.open(latest).resize((960, 540)), (960, i * 564 + 24))
    out = QA / ("review-" + "-".join(str(frame) for frame in frames) + ".jpg")
    page.save(out)
    print(out)


def publish():
    rows = {row["canonical_source_frame"]: row for row in inventory()}
    jobs = {}
    for path in (ROOT / "jobs").glob("fullpv-middle-f*.json"):
        job = json.loads(path.read_text(encoding="utf-8"))
        frame = job.get("source_frame")
        output = ROOT / job.get("output", "missing")
        if frame in rows and output.is_file() and "rejected" not in output.name:
            if frame not in jobs or output.stat().st_mtime_ns > jobs[frame][1].stat().st_mtime_ns:
                jobs[frame] = (path, output)
    reviews = {}
    for path in QA.glob("*-review.json"):
        review = json.loads(path.read_text(encoding="utf-8"))
        for frame in review.get("canonical_frames", []):
            reviews[frame] = (path, review.get("findings", []))
        for entry in review.get("suggested_draft_assets", []):
            reviews[entry["frame"]] = (path, entry.get("findings", []))
    proposals = []
    for frame, (job, output) in sorted(jobs.items()):
        path, findings = reviews.get(frame, (None, ["No completed group review yet; do not promote automatically."]))
        proposals.append({"source_frame": frame, "path": output.relative_to(ROOT).as_posix(),
                          "review": path.relative_to(ROOT).as_posix() if path else None,
                          "job": job.relative_to(ROOT).as_posix(), "known_issues": findings,
                          "artistic_accepted": False, "actual_speed_watch": "not_performed"})
    data = {"scope": [1500, 2399], "status": "draft_suggestions_for_root_review_only",
            "artistic_accepted": False, "actual_speed_watch": "not_performed", "proposals": proposals}
    target = QA / "selections-proposed.json"
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(target), "draft_cel_count": len(proposals)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("prepare")
    sub.add_parser("publish")
    save_parser = sub.add_parser("save")
    save_parser.add_argument("frame", type=int)
    save_parser.add_argument("original", type=Path)
    save_parser.add_argument("output")
    board_parser = sub.add_parser("board")
    board_parser.add_argument("frames", type=int, nargs="+")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "publish":
        publish()
    elif args.mode == "save":
        save(args.frame, args.original, args.output)
    elif args.mode == "board":
        board(args.frames)
