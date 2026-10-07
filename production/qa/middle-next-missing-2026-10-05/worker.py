"""Private source evidence, generated-output metadata, and draft handoff."""

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

QA = Path(__file__).resolve().parent
ROOT = QA.parents[1]
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta

FRAMES = [2077, 2081, 2085, 2090, 2094, 2098]
BOXES = {"head-face-hair": [580, 125, 1520, 535],
         "hands-cuffs": [570, 330, 1550, 735],
         "legs-hem-boots": [650, 620, 1640, 1080]}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2), encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def info(path):
    with Image.open(path) as image:
        return {"path": str(path), "sha256": sha(path), "canvas": list(image.size)}


def job_path(frame):
    return ROOT / "jobs" / f"middle-next-f{frame}-2026-10-05-source-v1.json"


def prepare():
    manifest = read(ROOT / "full-pv-progress-manifest.json")
    rows = {row["canonical_source_frame"]: row for row in manifest["cels"]}
    wanted = [2073, *FRAMES, 2105]
    originals = {}
    cap = cv2.VideoCapture(manifest["source"])
    for frame in range(max(wanted) + 1):
        ok, actual = cap.read()
        if not ok:
            raise RuntimeError(f"Sequential source decode failed {frame}")
        if frame in wanted:
            reference = cv2.imread(str(ROOT / rows[frame]["source_reference"]))
            if not np.array_equal(actual, reference):
                raise RuntimeError(f"Canonical source RGB mismatch {frame}")
            originals[frame] = actual
    cap.release()
    queue = []
    for frame in FRAMES:
        row = rows[frame]
        if row["selected_asset"]:
            raise RuntimeError(f"Already selected {frame}")
        index = wanted.index(frame)
        previous, after = wanted[index - 1], wanted[index + 1]
        a, b = originals[previous], originals[frame]
        make_delta(ROOT / rows[previous]["source_reference"], ROOT / row["source_reference"],
                   QA / f"f{previous}-f{frame}-source-AB-RGB-contours.png")
        make_delta(ROOT / row["source_reference"], ROOT / rows[after]["source_reference"],
                   QA / f"f{frame}-f{after}-source-AB-RGB-contours.png")
        native = Image.new("RGB", (max(box[2] - box[0] for box in BOXES.values()),
                                   sum(box[3] - box[1] + 28 for box in BOXES.values())), "#202024")
        draw = ImageDraw.Draw(native)
        y = 0
        for name, (x1, y1, x2, y2) in BOXES.items():
            aa, bb = a[y1:y2, x1:x2], b[y1:y2, x1:x2]
            draw.text((8, y + 8), name + " CURRENT native 1:1", fill="white")
            native.paste(Image.fromarray(cv2.cvtColor(bb, cv2.COLOR_BGR2RGB)), (0, y + 28))
            y += bb.shape[0] + 28
            diff = np.minimum(cv2.absdiff(aa, bb).astype(np.uint16) * 4, 255).astype(np.uint8)
            ea, eb = cv2.Canny(aa, 80, 160), cv2.Canny(bb, 80, 160)
            overlay = np.full_like(aa, 245)
            overlay[ea != 0] = (235, 110, 30)
            overlay[eb != 0] = (30, 80, 235)
            overlay[(ea != 0) & (eb != 0)] = (50, 50, 50)
            page = Image.new("RGB", (bb.shape[1] * 2, (bb.shape[0] + 28) * 2), "#202024")
            pd = ImageDraw.Draw(page)
            for k, (array, title) in enumerate(zip((aa, bb, diff, overlay),
                         ("SOURCE BEFORE", "SOURCE CURRENT", "ACTUAL RGB x4", "blue before / red current"))):
                x, y2p = (k % 2) * bb.shape[1], (k // 2) * (bb.shape[0] + 28)
                pd.text((x + 8, y2p + 8), name + ": " + title, fill="white")
                page.paste(Image.fromarray(cv2.cvtColor(array, cv2.COLOR_BGR2RGB)), (x, y2p + 28))
            page.save(QA / f"f{frame}-{name}-native-AB-RGB-contours.png")
        native.save(QA / f"f{frame}-source-native-keyparts.png")
        queue.append({**row, "previous_frame": previous, "next_frame": after,
                      "actual_sequential_decode_reference_equal": True})
    write(QA / "source-queue.json", {"snapshot_utc": datetime.now(timezone.utc).isoformat(),
          "manifest_sha256": sha(ROOT / "full-pv-progress-manifest.json"), "queue": queue,
          "source_sha256": sha(Path(manifest["source"])), "source_decode_equal": wanted,
          "native_boxes": BOXES, "accepted": False})
    Image.open(ROOT / "generated/middle-continuation-f2073-2026-10-05-v1.png").crop((515, 120, 850, 375)).save(QA / "klee-f2073-head-only-identity.png")
    print(json.dumps({"frames": FRAMES, "source_equal": wanted,
                      "source_frames": sum(row["source_frames_covered"] for row in queue)}))


def save(frame, original):
    job = read(job_path(frame))
    original = Path(original)
    target = ROOT / job["output"]
    if target.exists():
        raise FileExistsError(target)
    shutil.copy2(original, target)
    job.update({"original_tool_output": str(original), "tool_output_metadata": info(original),
                "workspace_output_metadata": info(target), "output_sha256": sha(target),
                "status": "generated_pending_static_review", "actual_builtin_call_submitted": True,
                "accepted": False, "artistic_accepted": False})
    write(job_path(frame), job)
    source = Image.open(Path(job["source_reference"])).convert("RGB")
    draft = Image.open(target).convert("RGB").resize(source.size, Image.Resampling.LANCZOS)
    page = Image.new("RGB", (3840, 1112), "#202024")
    draw = ImageDraw.Draw(page)
    draw.text((12, 8), f"f{frame} SOURCE left / NEW DRAFT right; static review only", fill="white")
    page.paste(source, (0, 32))
    page.paste(draft, (1920, 32))
    page.save(QA / f"f{frame}-source-new-static.png")
    for name, box in BOXES.items():
        a, b = source.crop(box), draft.crop(box)
        page = Image.new("RGB", (a.width * 2, a.height + 28), "#202024")
        draw = ImageDraw.Draw(page)
        draw.text((8, 8), f"SOURCE left / DRAFT right: {name}, normalized review", fill="white")
        page.paste(a, (0, 28))
        page.paste(b, (a.width, 28))
        page.save(QA / f"f{frame}-source-new-{name}.png")
    print(json.dumps({"frame": frame, "metadata": job["workspace_output_metadata"]}))


def record(frame):
    observation = read(QA / f"f{frame}-static-review-input.json")
    job = read(job_path(frame))
    blocked = observation.get("blocking", False)
    job.update({"status": "generated_blocking_unselected" if blocked else "reviewed_static_temporal_pending",
                "accepted": False, "artistic_accepted": False,
                "known_issues": observation["findings"], "source_current_observed": observation["observed"],
                "actual_speed_review": "not_performed", "final_composition_review": "not_performed",
                "static_review": f"qa/{QA.name}/f{frame}-source-new-static.png"})
    write(job_path(frame), job)
    proposal_path = QA / "draft-proposal.json"
    data = read(proposal_path) if proposal_path.exists() else {"accepted": False, "artistic_accepted": False,
                                                            "proposals": [], "blocked_candidates": []}
    for key in ("proposals", "blocked_candidates"):
        data[key] = [row for row in data[key] if row["source_frame"] != frame]
    target = "blocked_candidates" if blocked else "proposals"
    data[target].append({"source_frame": frame, "path": job["output"],
        "job": job_path(frame).relative_to(ROOT).as_posix(), "source_cel": job["source_cel"],
        "source_exposures": job["source_exposures"], "accepted": False, "artistic_accepted": False,
        "review": job["static_review"], "known_issues": observation["findings"],
        "source_current_observed": observation["observed"], "actual_speed_review": "not_performed",
        "output_sha256": job["output_sha256"]})
    data["proposals"].sort(key=lambda row: row["source_frame"])
    write(proposal_path, data)
    print(json.dumps({"reviewed": frame, "blocking": blocked, "proposal_count": len(data["proposals"])}))


def metadata(frame):
    job = read(job_path(frame))
    job["ordered_reference_metadata"] = [{**info(Path(path)), "role": role}
       for path, role in zip(job["references"], job["reference_roles"])]
    job["ordered_reference_metadata_phase"] = "before_builtin_call"
    write(job_path(frame), job)
    print(json.dumps({"frame": frame, "references": len(job["references"])}))


def seal():
    records, failures = [], []
    for frame in FRAMES:
        path = job_path(frame)
        if not path.exists():
            continue
        job = read(path)
        for reference in job["ordered_reference_metadata"]:
            if reference["sha256"] != sha(Path(reference["path"])):
                failures.append("Reference changed: " + reference["path"])
        if job.get("actual_builtin_call_submitted"):
            if sha(Path(job["original_tool_output"])) != sha(ROOT / job["output"]):
                failures.append("Workspace differs: " + str(path))
        records.append({"job": str(path), "job_sha256": sha(path), "full_saved_job": job})
    proposal_path = QA / "draft-proposal.json"
    data = read(proposal_path)
    data["successful_builtin_calls"] = sum(bool(row["full_saved_job"].get("actual_builtin_call_submitted")) for row in records)
    data["unique_missing_cels_generated"] = data["successful_builtin_calls"]
    data["successful_first_missing_cel_calls"] = 5
    data["successful_fresh_source_redraw_calls"] = 1
    data["unique_source_cels_in_batch"] = 6
    data["not_submitted_calls_in_this_batch"] = 0
    data["source_frames_addable_draft_only"] = sum(e["end"] - e["start"] for row in data["proposals"] for e in row["source_exposures"])
    data["actual_speed_review"] = "not_performed"
    data["final_composition_review"] = "not_performed"
    write(proposal_path, data)
    queue = {row["canonical_source_frame"]: row for row in read(QA / "source-queue.json")["queue"]}
    for offset in (0, 3):
        page = Image.new("RGB", (1280, 3 * 384), "#202024")
        draw = ImageDraw.Draw(page)
        for i, frame in enumerate(FRAMES[offset:offset + 3]):
            proposal = next(row for row in data["proposals"] if row["source_frame"] == frame)
            draw.text((8, i * 384 + 8), f"f{frame} SOURCE left / UNACCEPTED DRAFT right", fill="white")
            for k, path in enumerate((ROOT / queue[frame]["source_reference"], ROOT / proposal["path"])):
                page.paste(Image.open(path).convert("RGB").resize((640, 360), Image.Resampling.LANCZOS),
                           (k * 640, i * 384 + 24))
        page.save(QA / f"source-new-consecutive-page-{offset // 3 + 1:02d}.png")
    archive = QA / "full-builtin-promptset.json"
    if archive.exists():
        raise FileExistsError(archive)
    write(archive, {"snapshot_utc": datetime.now(timezone.utc).isoformat(), "records": records,
          "successful_builtin_calls": data["successful_builtin_calls"], "accepted": False,
          "proposal_path": str(proposal_path), "proposal_sha256": sha(proposal_path),
          "validation_failures": failures, "actual_speed_review": "not_performed"})
    print(json.dumps({"archive": str(archive), "sha256": sha(archive), "proposal": str(proposal_path),
                      "calls": data["successful_builtin_calls"], "proposals": len(data["proposals"]),
                      "frames": data["source_frames_addable_draft_only"], "failures": failures}))
    if failures:
        raise RuntimeError(failures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("prepare")
    sub.add_parser("seal")
    q = sub.add_parser("save")
    q.add_argument("frame", type=int)
    q.add_argument("original")
    q = sub.add_parser("metadata")
    q.add_argument("frame", type=int)
    q = sub.add_parser("record")
    q.add_argument("frame", type=int)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "save":
        save(args.frame, args.original)
    elif args.mode == "metadata":
        metadata(args.frame)
    elif args.mode == "record":
        record(args.frame)
    elif args.mode == "seal":
        seal()
