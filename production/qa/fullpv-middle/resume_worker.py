"""Private source evidence and unaccepted proposals for the resumed middle queue."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")


def rows():
    return [r for r in read(ROOT / "full-pv-progress-manifest.json")["cels"]
            if 1500 <= r["canonical_source_frame"] < 2400]


def prepare():
    manifest = read(ROOT / "full-pv-progress-manifest.json")
    missing = [r for r in rows() if not r["selected_asset"]]
    private = read(QA / "selections-proposed.json")["proposals"]
    generated = []
    for r in missing:
        frame = r["canonical_source_frame"]
        matches = list((ROOT / "jobs").glob(f"fullpv-middle-f{frame}*.json"))
        saved = [p for p in matches if (ROOT / read(p).get("output", "none")).is_file()]
        if saved:
            generated.append(frame)
    data = {"scope": [1500, 2399], "snapshot_utc": datetime.now(timezone.utc).isoformat(),
            "manifest_snapshot_utc": manifest["snapshot_utc"], "assigned_cels": len(rows()),
            "manifest_missing_cels": len(missing), "private_proposals": len(private),
            "saved_but_manifest_missing": generated, "queue": missing,
            "artistic_accepted": False}
    write(QA / "resume-queue.json", data)
    print(json.dumps({k: v for k, v in data.items() if k != "queue"}))


def evidence(frame, boxes):
    all_rows = rows()
    index = next(i for i, r in enumerate(all_rows) if r["canonical_source_frame"] == frame)
    current = all_rows[index]
    previous = all_rows[max(0, index - 1)]
    before = ROOT / previous["source_reference"]
    target = ROOT / current["source_reference"]
    directory = QA / current["canonical_family"]
    prefix = directory / f"resume-delta-f{previous['canonical_source_frame']:04d}-f{frame:04d}"
    if not prefix.with_suffix(".png").exists():
        make_delta(before, target, prefix.with_suffix(".png"))
    a, b = (cv2.imread(str(path)) for path in (before, target))
    items = []
    for name, box in boxes.items():
        x1, y1, x2, y2 = box
        aa, bb = a[y1:y2, x1:x2], b[y1:y2, x1:x2]
        diff = np.minimum(cv2.absdiff(aa, bb).astype(np.uint16) * 4, 255).astype(np.uint8)
        ea, eb = cv2.Canny(aa, 80, 160), cv2.Canny(bb, 80, 160)
        overlay = np.full_like(aa, 245)
        overlay[ea != 0] = (235, 110, 30)
        overlay[eb != 0] = (30, 80, 235)
        overlay[(ea != 0) & (eb != 0)] = (50, 50, 50)
        cell_w = 700
        cell_h = max(180, round((y2-y1) * cell_w/(x2-x1)))
        page = Image.new("RGB", (cell_w * 4, cell_h + 32), "#202024")
        draw = ImageDraw.Draw(page)
        for i, (panel, label) in enumerate(zip((aa, bb, diff, overlay),
                                             ("BEFORE", "CURRENT", "RGB diff x4", "Blue before / red current"))):
            draw.text((i*cell_w + 8, 8), f"{name}: {label}", fill="white")
            image = Image.fromarray(cv2.cvtColor(panel, cv2.COLOR_BGR2RGB))
            page.paste(image.resize((cell_w, cell_h)), (i*cell_w, 32))
        items.append(page)
    crop_page = Image.new("RGB", (2800, sum(p.height for p in items)), "#202024")
    y = 0
    for page in items:
        crop_page.paste(page, (0, y))
        y += page.height
    crop_path = prefix.with_name(prefix.name + "-head-eye-hands.png")
    crop_page.save(crop_path)
    write(prefix.with_name(prefix.name + "-crops.json"), {"source_frame": frame,
          "before_frame": previous["canonical_source_frame"], "boxes": boxes,
          "source_reference": str(target), "source_delta": str(prefix.with_suffix(".png")),
          "local_delta": str(crop_path), "role": "Source spatial evidence only; current is pose authority"})
    print(json.dumps({"frame": frame, "source": str(target), "delta": str(prefix.with_suffix(".png")),
                      "local_delta": str(crop_path)}))


def save(frame, original, output):
    target = ROOT / "generated" / output
    if target.exists():
        raise FileExistsError(target)
    shutil.copy2(original, target)
    with Image.open(target) as image:
        tool_canvas = list(image.size)
        if image.size != (1920, 1080):
            normalized = image.convert("RGB").resize((1920, 1080), Image.Resampling.LANCZOS)
            normalized.save(target)
    job_path = ROOT / "jobs" / f"fullpv-middle-f{frame}.json"
    job = read(job_path)
    job.update({"status": "generated_draft_unaccepted", "original_tool_output": str(original),
                "output_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "tool_canvas": tool_canvas, "output_canvas": [1920, 1080],
                "accepted": False, "artistic_accepted": False,
                "actual_speed_review": "not_performed"})
    write(job_path, job)
    print(json.dumps({"path": str(target), "tool_canvas": tool_canvas,
                      "sha256": job["output_sha256"]}))


def review(frame, findings):
    job_path = ROOT / "jobs" / f"fullpv-middle-f{frame}.json"
    job = read(job_path)
    output = ROOT / job["output"]
    source = Path(job["source_reference"])
    a, b = (cv2.imread(str(path)) for path in (source, output))
    delta = cv2.absdiff(a, b)
    prefix = QA / f"resume-output-review-f{frame:04d}"
    make_delta(source, output, prefix.with_suffix(".png"))
    review_data = {"source_frame": frame, "canonical_frames": [frame],
                   "findings": findings, "artistic_accepted": False,
                   "actual_speed_review": "not_performed", "static_inspection": "completed",
                   "full_canvas_difference": str(prefix.with_suffix(".png")),
                   "changed_pixels_gt28": int((delta.max(axis=2) > 28).sum()),
                   "checks": {"source_current_geometry": "visually_compared",
                              "head_eye_hands": "visually_compared",
                              "source_background_caption_props": "compositor_review_required",
                              "sequence_continuity": "pending", "actual_speed": "pending"}}
    review_path = prefix.with_suffix(".json")
    write(review_path, review_data)
    job.update({"static_review": str(review_path.relative_to(ROOT)).replace("\\", "/"),
                "known_issues": findings, "artistic_accepted": False, "accepted": False})
    write(job_path, job)
    proposal_path = QA / "selections-proposed.json"
    proposals = read(proposal_path)
    proposals["proposals"] = [p for p in proposals["proposals"] if p["source_frame"] != frame]
    proposals["proposals"].append({"source_frame": frame, "path": job["output"],
                                   "job": str(job_path.relative_to(ROOT)).replace("\\", "/"),
                                   "review": str(review_path.relative_to(ROOT)).replace("\\", "/"),
                                   "known_issues": findings, "artistic_accepted": False,
                                   "actual_speed_watch": "not_performed"})
    proposals["proposals"].sort(key=lambda p: p["source_frame"])
    proposals["artistic_accepted"] = False
    write(proposal_path, proposals)
    print(json.dumps({"frame": frame, "proposals": len(proposals["proposals"]),
                      "review": str(review_path), "artistic_accepted": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("prepare")
    p = sub.add_parser("evidence")
    p.add_argument("frame", type=int)
    p.add_argument("boxes", type=json.loads)
    p = sub.add_parser("save")
    p.add_argument("frame", type=int)
    p.add_argument("original", type=Path)
    p.add_argument("output")
    p = sub.add_parser("review")
    p.add_argument("frame", type=int)
    p.add_argument("findings", type=json.loads)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "evidence":
        evidence(args.frame, args.boxes)
    elif args.mode == "save":
        save(args.frame, args.original, args.output)
    elif args.mode == "review":
        review(args.frame, args.findings)
