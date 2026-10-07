"""Source evidence and prompt archiving for root's final 34 one-pass cels."""

import argparse
import contextlib
from hashlib import sha256
import io
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa/oct7-bulk-root"
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def prepare():
    master = ROOT / "qa/full-draft-one-pass-2026-10-07/ownership-queue.json"
    frozen = json.loads(master.read_text(encoding="utf-8"))
    ending = frozen["owners"]["ending"]["rows"]
    root_rows = [r for r in ending if r["canonical_source_frame"] >= 3470]
    assert len(root_rows) == 34
    v2 = master.with_name("ownership-queue-v2.json")
    if v2.exists():
        raise FileExistsError("Resume existing root evidence")
    frozen["owners"]["ending"] = {"count": 49, "rows": ending[:49]}
    frozen["owners"]["root"] = {"count": 34, "rows": root_rows}
    frozen["amendment"] = "Before calls, transfer ending tail >=3470 to root to balance builtin generation. Original queue retained."
    v2.write_text(json.dumps(frozen, indent=2), encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    lookup = {r["canonical_source_frame"]: r for r in manifest["cels"]}
    previous = {r["canonical_source_frame"]: manifest["cels"][manifest["cels"].index(r)-1]["canonical_source_frame"]
                for r in root_rows}
    wanted = set(previous) | set(previous.values())
    cap = cv2.VideoCapture(manifest["source"])
    for frame in range(max(wanted)+1):
        ok, image = cap.read()
        if not ok:
            raise ValueError(f"Source decode failed f{frame}")
        if frame in wanted:
            assert np.array_equal(image, cv2.imread(str(ROOT / lookup[frame]["source_reference"]))), frame
    cap.release()
    queue = []
    for row in root_rows:
        f = row["canonical_source_frame"]
        before = ROOT / lookup[previous[f]]["source_reference"]
        current = ROOT / row["source_reference"]
        delta = OUT / f"f{previous[f]}-f{f}-source-ab-rgb-contours.png"
        with contextlib.redirect_stdout(io.StringIO()):
            make_delta(before, current, delta)
        queue.append({**row, "source_frame": f, "before_source_frame": previous[f],
                      "current_source": str(current), "current_source_sha256": digest(current),
                      "before_source": str(before), "actual_delta": str(delta),
                      "sequential_original_exact": True, "accepted": False})
    (OUT / "source-evidence-queue.json").write_text(json.dumps({"owner": "root", "queue": queue}, indent=2), encoding="utf-8")
    for page in range(0, len(queue), 8):
        sheet = Image.new("RGB", (1280, 4*386), "#202024")
        draw = ImageDraw.Draw(sheet)
        for i, row in enumerate(queue[page:page+8]):
            x, y = (i%2)*640, (i//2)*386
            draw.text((x+8,y+4), f'f{row["source_frame"]} / {row["canonical_family"]}', fill="white")
            sheet.paste(Image.open(row["current_source"]).resize((640,360)), (x,y+26))
        sheet.save(OUT / f"source-contact-{page//8+1}.jpg")
    print(json.dumps({"queue": str(OUT / "source-evidence-queue.json"), "count": len(queue), "sequential_verified": True}))


def job(frame, notes, references):
    queue = json.loads((OUT / "source-evidence-queue.json").read_text(encoding="utf-8"))["queue"]
    row = next(r for r in queue if r["source_frame"] == frame)
    refs = [{"path": str(Path(p).resolve()), "role": role, "actually_viewed": True,
             "sha256_at_prepare": digest(Path(p))} for p, role in references]
    assert 1 <= len(refs) <= 5 and Path(refs[0]["path"]) == Path(row["current_source"])
    path = OUT / f"job-f{frame}-v1.json"
    if path.exists():
        raise FileExistsError(path)
    prompt = ("Use case: identity-preserve. Asset: one complete replacement cel for the user's Klee PV draft. "
              "Redraw the FIRST image in the original simple hand-drawn PV style, replacing ALL visible original characters/fragments with Klee from Genshin Impact. "
              "The FIRST image alone determines camera, crop, body/head/hand pose, expression, visible extent and front/back overlap. "
              "Maintain the original blue backdrop and props. Keep any existing pillow and hand contact at source size/position. "
              "Use a red Klee cap with light feather, pale blonde short twin ponytails (exactly two, no long original hair), "
              "red simplified coat, plain cream cuffs, brown gloves/boots where visible, red eyes when source eyes are open. "
              "Preserve the source's closed eye/wink states and visible hands. Do not add hidden anatomy or extra hands. "
              "Identity/style references must NOT freeze the previous expression or pose. The source delta describes actual drawing changes, "
              "not a motion warp. Keep flat original-PV color blocks and line weight, no elaborate render, no new background decoration. "
              "Remove all source lettering from this generated cel: original Chinese/Japanese subtitles and credits are restored independently in composition. "
              "Do not generate text, labels, watermark, collage or reference panels. Produce exactly one complete 16:9 frame. "
              f"Current source observation and required changes for f{frame}: {notes} "
              "Ordered input roles: " + "; ".join(f"Image {i+1}: {r['role']}" for i,r in enumerate(refs)))
    record = {"source_frame": frame, "source_candidate": row["source_candidate"], "source_exposures": row["source_exposures"],
              "output": f"generated/oct7-bulk-root-f{frame:04d}-v1.png", "prompt": prompt,
              "reference_roles": refs, "tool": "builtin_imagegen", "status": "prepared", "accepted": False,
              "policy": "one_pass_no_artistic_repairs_before_user_full_draft_feedback"}
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


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
        queue = json.loads((OUT / "source-evidence-queue.json").read_text(encoding="utf-8"))["queue"]
        row = next(r for r in queue if r["source_frame"] == args.job)
        refs = [(row["current_source"], "CURRENT ORIGINAL target; sole composition, crop, pose, expression, anatomy and occlusion authority"),
                (ROOT / "qa/standing-open-eye-identity-crop.png", "Klee head identity only; ignore pose and expression, use source eyes and mouth"),
                (ROOT / "qa/standing-costume-crop.png", "Klee costume colors only; not framing or pose authority"),
                (row["actual_delta"], "Actual source AB RGB x4 and blue-before/red-current contours; apply real current changes, not interpolation")]
        prior = ROOT / f'generated/oct7-bulk-root-f{row["before_source_frame"]:04d}-v1.png'
        if prior.exists() and not args.no_prior:
            refs.append((prior, "Adjacent unaccepted Klee cel: palette, line weight and persistent two short ponytails only; NOT pose/expression/framing authority, do not copy collar/button drift"))
        print(json.dumps(job(args.job, args.notes, refs)))
    elif args.save:
        import importlib.util
        spec = importlib.util.spec_from_file_location("draft_archive", ROOT / "qa/late-oct6-worker.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.OUT = OUT
        module.save(args.save, args.origin, args.notes)
