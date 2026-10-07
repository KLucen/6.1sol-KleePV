"""Persist late recovery assets and honest reviews; does not alter shared selections."""

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("frame", type=int)
    parser.add_argument("--generator", type=Path)
    parser.add_argument("--add-prompt", default="")
    parser.add_argument("--replace-notes", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--issue", action="append", default=[])
    parser.add_argument("--blocked", default="")
    parser.add_argument("--contacts", action="store_true")
    args = parser.parse_args()
    job_path = ROOT / "jobs" / f"fine-f{args.frame:04d}.json"
    job = json.loads(job_path.read_text(encoding="utf-8"))
    if args.replace_notes:
        marker = f"CURRENT SOURCE f{args.frame}: "
        job["prompt"] = job["prompt"].split(marker)[0] + marker + args.replace_notes
    if args.add_prompt:
        job["prompt"] += args.add_prompt
    if args.generator:
        destination = ROOT / job["output"]
        if destination.exists():
            raise ValueError(f"Do not overwrite {destination}")
        shutil.copy2(args.generator, destination)
        job["generator_output"] = str(args.generator)
        job["status"] = "generated_draft"
    if args.notes or args.issue:
        job["static_review"] = {
            "performed": True,
            "pass": not args.issue,
            "notes": [args.notes] if args.notes else [],
            "issues": args.issue,
            "scope": "single-cel and adjacent static comparison only",
        }
    if args.blocked:
        job["status"] = "blocked_builtin_imagegen"
        job["blocker"] = args.blocked
    job["accepted"] = False
    job["temporal_review"] = {"performed": False, "accepted": False}
    job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    suggestions_path = Path(__file__).parent / "recovery-selected-suggestions.json"
    suggestions = json.loads(suggestions_path.read_text(encoding="utf-8")) if suggestions_path.exists() else {
        "scope": "late recovery worker only; root must review before shared selection",
        "accepted": False,
        "cels": [],
    }
    if (ROOT / job["output"]).exists():
        record = {
            "source_frame": args.frame,
            "source_cel": job["source_cel"],
            "path": job["output"],
            "source_reference": job["references"][0]["path"],
            "job": str(job_path.relative_to(ROOT)),
            "review": job["static_review"],
            "actual_speed_reviewed": False,
        }
        suggestions["cels"] = [c for c in suggestions["cels"] if c["source_frame"] != args.frame] + [record]
        suggestions["cels"].sort(key=lambda c: c["source_frame"])
    suggestions_path.write_text(json.dumps(suggestions, indent=2), encoding="utf-8")
    if args.contacts:
        pages = []
        for start in range(0, len(suggestions["cels"]), 4):
            page = Image.new("RGB", (1280, 1568), "#25252a")
            draw = ImageDraw.Draw(page)
            for row, cel in enumerate(suggestions["cels"][start:start + 4]):
                y = row * 392
                draw.text((12, y + 10), f"SOURCE f{cel['source_frame']} / {cel['source_cel']}", fill="white")
                draw.text((652, y + 10), f"KLEE DRAFT / issues: {len(cel['review'].get('issues', []))}", fill="white")
                for x, path in [(0, Path(cel["source_reference"])), (640, ROOT / cel["path"])]:
                    with Image.open(path) as im:
                        page.paste(im.convert("RGB").resize((640, 360)), (x, y + 32))
            contact_path = Path(__file__).parent / f"recovery-static-{start // 4 + 1:02d}.jpg"
            page.save(contact_path, quality=95)
            pages.append(str(contact_path.relative_to(ROOT)))
        suggestions["static_comparison_pages"] = pages
        suggestions_path.write_text(json.dumps(suggestions, indent=2), encoding="utf-8")
    print(json.dumps({"job": str(job_path), "output": job["output"], "status": job["status"]}))


if __name__ == "__main__":
    main()
