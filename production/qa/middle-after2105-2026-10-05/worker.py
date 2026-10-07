"""Private source evidence and draft handoff; never edit shared selections."""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

QA = Path(__file__).resolve().parent
ROOT = QA.parents[1]
spec = importlib.util.spec_from_file_location("previous_private_worker", ROOT / "qa/middle-next-missing-2026-10-05/worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
FRAMES = [2105, 2110, 2115, 2121, 2122, 2129, 2130, 2132]
BOXES = {"head-face-hair": [430, 70, 1220, 570],
         "hands-cuffs": [220, 90, 1430, 660],
         "legs-hem-boots": [430, 540, 1450, 1080]}
worker.QA, worker.ROOT, worker.FRAMES, worker.BOXES = QA, ROOT, FRAMES, BOXES
worker.job_path = lambda frame: ROOT / "jobs" / f"middle-after-f{frame}-2026-10-05-source-v1.json"


def prepare():
    manifest = worker.read(ROOT / "full-pv-progress-manifest.json")
    rows = {r["canonical_source_frame"]: r for r in manifest["cels"]}
    wanted = [2098, *FRAMES, 2135]
    originals = {}
    cap = cv2.VideoCapture(manifest["source"])
    for frame in range(max(wanted) + 1):
        ok, actual = cap.read()
        if not ok:
            raise RuntimeError(f"Sequential decode failed {frame}")
        if frame in wanted:
            reference = cv2.imread(str(ROOT / rows[frame]["source_reference"]))
            if not np.array_equal(actual, reference):
                raise RuntimeError(f"Canonical RGB mismatch {frame}")
            originals[frame] = actual
    cap.release()
    queue = []
    for frame in FRAMES:
        row = rows[frame]
        if row["selected_asset"]:
            raise RuntimeError(f"Already mapped {frame}")
        i = wanted.index(frame)
        previous, after = wanted[i - 1], wanted[i + 1]
        a, b = originals[previous], originals[frame]
        worker.make_delta(ROOT / rows[previous]["source_reference"], ROOT / row["source_reference"],
                          QA / f"f{previous}-f{frame}-source-AB-RGB-contours.png")
        worker.make_delta(ROOT / row["source_reference"], ROOT / rows[after]["source_reference"],
                          QA / f"f{frame}-f{after}-source-AB-RGB-contours.png")
        native = Image.new("RGB", (1210, 1694), "#202024")
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
            overlay[ea != 0], overlay[eb != 0] = (235, 110, 30), (30, 80, 235)
            overlay[(ea != 0) & (eb != 0)] = (50, 50, 50)
            page = Image.new("RGB", (bb.shape[1] * 2, (bb.shape[0] + 28) * 2), "#202024")
            pd = ImageDraw.Draw(page)
            for k, (array, title) in enumerate(zip((aa, bb, diff, overlay),
                    ("SOURCE BEFORE", "SOURCE CURRENT", "ACTUAL RGB x4", "blue before / red current"))):
                x, yy = k % 2 * bb.shape[1], k // 2 * (bb.shape[0] + 28)
                pd.text((x + 8, yy + 8), name + ": " + title, fill="white")
                page.paste(Image.fromarray(cv2.cvtColor(array, cv2.COLOR_BGR2RGB)), (x, yy + 28))
            page.save(QA / f"f{frame}-{name}-native-AB-RGB-contours.png")
        native.save(QA / f"f{frame}-source-native-keyparts.png")
        queue.append({**row, "previous_frame": previous, "next_frame": after,
                      "actual_sequential_decode_reference_equal": True})
    worker.write(QA / "source-queue.json", {"snapshot_utc": datetime.now(timezone.utc).isoformat(),
          "manifest_sha256": worker.sha(ROOT / "full-pv-progress-manifest.json"), "queue": queue,
          "source_sha256": worker.sha(Path(manifest["source"])), "source_decode_equal": wanted,
          "native_boxes": BOXES, "accepted": False})
    contact = Image.new("RGB", (1280, 4 * 384), "#202024")
    draw = ImageDraw.Draw(contact)
    for i, frame in enumerate(FRAMES):
        x, y = i % 2 * 640, i // 2 * 384
        draw.text((x + 8, y + 8), f"SOURCE f{frame}", fill="white")
        im = Image.fromarray(cv2.cvtColor(originals[frame], cv2.COLOR_BGR2RGB))
        contact.paste(im.resize((640, 360), Image.Resampling.LANCZOS), (x, y + 24))
    contact.save(QA / "source-candidates-contact.png")
    print(json.dumps({"candidates": FRAMES, "sequential_equal": wanted}))


def seal():
    data = worker.read(QA / "draft-proposal.json")
    frames = [r["source_frame"] for r in data["proposals"]]
    records, failures = [], []
    for frame in frames:
        path = worker.job_path(frame)
        job = worker.read(path)
        for reference in job["ordered_reference_metadata"]:
            if reference["sha256"] != worker.sha(Path(reference["path"])):
                failures.append("Reference changed: " + reference["path"])
        if worker.sha(Path(job["original_tool_output"])) != worker.sha(ROOT / job["output"]):
            failures.append("Workspace differs: " + str(path))
        records.append({"job": str(path), "job_sha256": worker.sha(path), "full_saved_job": job})
    data.update({"successful_builtin_calls": len(records), "unique_missing_cels_generated": len(frames),
                 "source_frames_addable_draft_only": sum(e["end"] - e["start"] for row in data["proposals"] for e in row["source_exposures"]),
                 "actual_speed_review": "not_performed", "final_composition_review": "not_performed"})
    worker.write(QA / "draft-proposal.json", data)
    for offset in range(0, len(frames), 3):
        page = Image.new("RGB", (1280, 3 * 384), "#202024")
        draw = ImageDraw.Draw(page)
        for i, frame in enumerate(frames[offset:offset + 3]):
            row = next(r for r in data["proposals"] if r["source_frame"] == frame)
            job = worker.read(worker.job_path(frame))
            draw.text((8, i * 384 + 8), f"f{frame} SOURCE left / UNACCEPTED DRAFT right", fill="white")
            for k, path in enumerate((Path(job["source_reference"]), ROOT / row["path"])):
                page.paste(Image.open(path).convert("RGB").resize((640, 360), Image.Resampling.LANCZOS), (k * 640, i * 384 + 24))
        page.save(QA / f"source-new-consecutive-page-{offset // 3 + 1:02d}.png")
    archive = QA / "full-builtin-promptset.json"
    if archive.exists():
        raise FileExistsError(archive)
    worker.write(archive, {"snapshot_utc": datetime.now(timezone.utc).isoformat(), "records": records,
                "successful_builtin_calls": len(records), "accepted": False, "proposal_sha256": worker.sha(QA / "draft-proposal.json"),
                "validation_failures": failures, "actual_speed_review": "not_performed"})
    print(json.dumps({"archive": str(archive), "sha256": worker.sha(archive), "proposals": len(frames),
                     "frames": data["source_frames_addable_draft_only"], "failures": failures}))
    if failures:
        raise RuntimeError(failures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("prepare")
    sub.add_parser("seal")
    q = sub.add_parser("reference-crop")
    q.add_argument("input")
    q.add_argument("output")
    q.add_argument("box", type=int, nargs=4)
    for mode in ("save", "metadata", "record"):
        q = sub.add_parser(mode)
        q.add_argument("frame", type=int)
        if mode == "save":
            q.add_argument("original")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "seal":
        seal()
    elif args.mode == "save":
        worker.save(args.frame, args.original)
    elif args.mode == "reference-crop":
        target = QA / args.output
        if target.exists():
            raise FileExistsError(target)
        Image.open(ROOT / args.input).crop(args.box).save(target)
        print(json.dumps(worker.info(target)))
    else:
        getattr(worker, args.mode)(args.frame)
