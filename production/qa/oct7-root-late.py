"""Balance the unscheduled late tail without changing sealed batches."""

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa/oct7-bulk-root-late"
sys.path.insert(0, str(ROOT))


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def prepare():
    base = ROOT / "qa/full-draft-one-pass-2026-10-07/ownership-queue-v2.json"
    master = read(base)
    rows = master["owners"]["late_action"]["rows"]
    tail = [r for r in rows if r["canonical_source_frame"] >= 3235]
    assert len(tail) == 14
    late = ROOT / "qa/oct7-bulk-late_action"
    assert not any((late / f'job-f{r["canonical_source_frame"]}-v1.json').exists() for r in tail), "Check tail jobs before reassignment"
    master["owners"]["late_action"] = {"count": 44, "rows": rows[:44]}
    master["owners"]["root_late"] = {"count": 14, "rows": tail}
    master["amendment_v3"] = "After root sealed 34 ending cels, transfer unscheduled late tail >=3235 to root; worker confirmed cutoff3234. Earlier ownership snapshots retained."
    destination = base.with_name("ownership-queue-v3.json")
    if destination.exists() or OUT.exists():
        raise FileExistsError("Resume existing tail queue")
    evidence = late / "source-evidence-queue-original58.json"
    if not evidence.exists():
        evidence = late / "source-evidence-queue.json"
    queue = [r for r in read(evidence)["queue"] if r["source_frame"] >= 3235]
    assert len(queue) == 14
    wanted = {Path(r[k]) for r in queue for k in ("before_source", "current_source")}
    frame_paths = {int(p.stem.split("-f")[-1]): p for p in wanted}
    source = read(ROOT / "source_meta.json")["source"]
    cap = cv2.VideoCapture(source)
    for f in range(max(frame_paths) + 1):
        ok, image = cap.read()
        if not ok:
            raise ValueError(f"Source ended at {f}")
        if f in frame_paths and not np.array_equal(image, cv2.imread(str(frame_paths[f]))):
            raise ValueError(f"Reference differs from sequential source at {f}")
    cap.release()
    OUT.mkdir()
    for row in queue:
        row["sequential_original_exact"] = True
        row["current_source_sha256"] = sha256(Path(row["current_source"]).read_bytes()).hexdigest()
    write(destination, master)
    write(OUT / "source-evidence-queue.json", {"owner": "root_late", "queue": queue, "accepted": False})
    print(json.dumps({"ownership": str(destination), "queue": str(OUT), "count": 14, "sequential_original_exact": True}))


def load_helper():
    spec = importlib.util.spec_from_file_location("root_bulk", ROOT / "qa/oct7-root-bulk.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.OUT = OUT
    return helper


def job(frame, notes, no_prior=False):
    helper = load_helper()
    row = next(r for r in read(OUT / "source-evidence-queue.json")["queue"] if r["source_frame"] == frame)
    row.setdefault("source_candidate", row["cel"])
    refs = [(row["current_source"], "CURRENT original; sole crop, pose, visible anatomy, expression and occlusion authority"),
            (ROOT / "qa/standing-open-eye-identity-crop.png", "Klee head identity only, ignore reference pose and expression"),
            (ROOT / "qa/standing-costume-crop.png", "Klee costume colors and construction only, NOT crop or pose"),
            (row["actual_delta"], "Actual source AB RGB x4 and blue-before/red-current contours; not final art")]
    previous = ROOT / f'generated/oct7-bulk-root-late-f{row["before_source_frame"]:04d}-v1.png'
    if previous.exists() and not no_prior:
        refs.append((previous, "Adjacent unaccepted Klee colors/lineweight only; current source overrides pose/crop; ignore defects"))
    else:
        refs.append((row["native_local_delta"], "Native source critical local AB RGB and contours; follow current panels"))
    data = read(OUT / "source-evidence-queue.json")
    target = next(r for r in data["queue"] if r["source_frame"] == frame)
    target["source_candidate"] = row["source_candidate"]
    write(OUT / "source-evidence-queue.json", data)
    record = helper.job(frame, notes, refs)
    record["output"] = f"generated/oct7-bulk-root-late-f{frame:04d}-v1.png"
    record["owner"] = "root_late"
    record["references_inspected_before_prepare"] = True
    write(OUT / f"job-f{frame}-v1.json", record)
    print(json.dumps(record))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--job", type=int)
    parser.add_argument("--save", type=int)
    parser.add_argument("--origin")
    parser.add_argument("--notes")
    parser.add_argument("--no-prior", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.job:
        job(args.job, args.notes, args.no_prior)
    elif args.save:
        spec = importlib.util.spec_from_file_location("draft_archive", ROOT / "qa/late-oct6-worker.py")
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        helper.OUT = OUT
        helper.save(args.save, args.origin, args.notes)
