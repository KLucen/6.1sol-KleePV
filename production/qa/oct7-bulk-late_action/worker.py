"""Private evidence/job persistence for the Oct7 full-draft production pass."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from hashlib import sha256
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def prepare():
    queue_path = OUT / "source-evidence-queue.json"
    data = read(queue_path)
    all_rows = read(ROOT / "full-pv-progress-manifest.json")["cels"]
    indices = {r["canonical_source_frame"]: i for i, r in enumerate(all_rows)}
    for row in data["queue"]:
        f = row["canonical_source_frame"]
        previous = all_rows[indices[f] - 1]
        before, current = ROOT / previous["source_reference"], ROOT / row["source_reference"]
        delta = OUT / f"f{previous['canonical_source_frame']}-f{f}-ab-rgb-contours.png"
        if not delta.exists():
            make_delta(before, current, delta)
        a, b = cv2.imread(str(before)), cv2.imread(str(current))
        if f == 2944:
            boxes = [("eyes_hair", (1080, 170, 1450, 400)), ("hands_pillow", (1090, 300, 1500, 555)),
                     ("legs_boots", (1150, 550, 1510, 940))]
        elif f < 3087:
            boxes = [("head_turn_and_hair", (650, 190, 1280, 710)), ("shoulders_hair_ends", (640, 690, 1290, 1080))]
        elif f < 3219:
            boxes = [("face_hair_hands", (600, 160, 1340, 730)), ("torso_legs", (600, 700, 1340, 1080))]
        else:
            boxes = [("feet_and_clothing", (400, 120, 1500, 920))]
        width = max((box[2] - box[0]) * 2 for _, box in boxes)
        height = sum((box[3] - box[1]) * 2 + 50 for _, box in boxes)
        canvas = Image.new("RGB", (width, height), "#202024")
        draw = ImageDraw.Draw(canvas)
        y = 0
        for label, (x1, y1, x2, y2) in boxes:
            aa, bb = a[y1:y2, x1:x2], b[y1:y2, x1:x2]
            h, w = aa.shape[:2]
            diff = np.minimum(cv2.absdiff(aa, bb).astype(np.uint16) * 4, 255).astype(np.uint8)
            ea, eb = cv2.Canny(aa, 80, 160), cv2.Canny(bb, 80, 160)
            contours = np.full_like(aa, 245)
            contours[ea != 0] = (235, 110, 30)
            contours[eb != 0] = (30, 80, 235)
            contours[(ea != 0) & (eb != 0)] = (50, 50, 50)
            draw.text((8, y + 5), f"{label}: BEFORE / CURRENT / RGB x4 / blue-before red-current; native pixels", fill="white")
            for arr, x, yy in [(aa, 0, y + 25), (bb, w, y + 25), (diff, 0, y + 25 + h), (contours, w, y + 25 + h)]:
                canvas.paste(Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)), (x, yy))
            y += h * 2 + 50
        local = OUT / f"f{f}-source-local-ab-rgb-contours.png"
        if not local.exists():
            canvas.save(local)
        row.update({"source_frame": f, "current_source": str(current), "source_sha256": digest(current),
                    "before_source_frame": previous["canonical_source_frame"], "before_source": str(before),
                    "actual_delta": str(delta), "native_local_delta": str(local), "accepted": False})
    write(queue_path, data)
    print(json.dumps({"queue": str(queue_path), "count": len(data["queue"])}))


def job(frame, notes, prior, omit_prior=False):
    row = next(r for r in read(OUT / "source-evidence-queue.json")["queue"] if r["source_frame"] == frame)
    refs = [
        {"path": row["current_source"], "role": "CURRENT original PV target; sole authority for pose, facial expression, crop, visible parts and occlusion"},
        {"path": str(ROOT / "qa/standing-open-eye-identity-crop.png"), "role": "Klee identity only: red clover hat, feather, short blond twin ponytails, ears; NOT pose or expression"},
        {"path": str(ROOT / prior), "role": "Adjacent Klee draft simplification, costume colors and short hair connections only; do NOT freeze its pose"},
        {"path": row["actual_delta"], "role": "Original BEFORE/CURRENT, actual RGB x4, blue-before/red-current contours; diagnostic not final art"},
        {"path": row["native_local_delta"], "role": "Native local eyes/hands/hair/clothing changes and occlusion diagnostic; follow CURRENT panels"},
    ]
    prompt = """Use case: identity-preserve. Asset type: one entire 16:9 cel of a hand-drawn music PV, not a contact sheet.
Replace EVERY original person visible in Image 1 with Klee (Genshin Impact) in the same simple flat-color sketch style, same camera, position, scale, crop, pose, expression and occlusion. Image 1 is the CURRENT target and overrides all other references for anatomy, visible parts, gesture and motion. Image 2 sets Klee identity only. Image 3 is continuity of simplified Klee design/color, not a pose template. Images 4 and 5 show actual preceding/current original spatial differences; follow CURRENT panels, no diagnostic panels in the output.
Klee: red clover beret with one white feather and side clover badge, light blond bangs and two SHORT ponytails, pointy ears, plain cream collar and cuffs, red coat dress with cream trim, brown gloves and brown boots. No frilly cuffs, no long original pink hair, no original animal hood, no additional person or body parts. Translate original hair motion into short Klee ponytail motion, preserving roots, overlap and current direction. Preserve the original background colors, camera boundaries and props in their original positions and proportions. Leave all lyrics/text absent: lettering is independently restored during compositing. No logos or watermark. Flat limited palette, slightly irregular dark hand-drawn contours; no gradients, new elaborate illustration or polish escalation.
CURRENT target observations and adjacent-source motion: """ + notes
    if omit_prior:
        refs.pop(2)
        prompt = prompt.replace("Image 3 is continuity of simplified Klee design/color, not a pose template. Images 4 and 5 show actual preceding/current original spatial differences; follow CURRENT panels, no diagnostic panels in the output.", "Images 3 and 4 show actual preceding/current original spatial differences; follow CURRENT panels, no diagnostic panels in the output. No adjacent Klee pose template is supplied because its anatomy was flawed; current original is the sole pose authority.")
    path = OUT / f"job-f{frame}-v1.json"
    if path.exists():
        raise FileExistsError(path)
    value = {"source_frame": frame, "cel": row["cel"], "date": "2026-10-07", "owner": "late_action",
             "tool": "builtin_imagegen", "status": "prepared", "accepted": False, "prompt": prompt,
             "reference_roles": refs, "reference_sha256_at_prepare": [digest(r["path"]) for r in refs],
             "output": f"generated/oct7-bulk-late_action-f{frame}-v1.png",
             "source_exposures": row["source_exposures"], "source_observations": notes,
             "one_pass_draft_policy": True, "temporal_review": {"performed": False, "accepted": False}}
    write(path, value)
    print(json.dumps({"job": str(path), "frame": frame, "references": [r["path"] for r in refs]}))


def save(frame, origin, notes):
    spec = importlib.util.spec_from_file_location("old_worker", ROOT / "qa/late-oct6-worker.py")
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    old.OUT = OUT
    old.save(frame, origin, notes)


def local(frame, box):
    data = read(OUT / "source-evidence-queue.json")
    row = next(r for r in data["queue"] if r["source_frame"] == frame)
    x1, y1, x2, y2 = box
    arrays = [cv2.imread(str(row[key]))[y1:y2, x1:x2] for key in ("before_source", "current_source")]
    paths = []
    for suffix, arr in zip(("before", "current"), arrays):
        path = OUT / f"f{frame}-native-figure-{suffix}.png"
        cv2.imwrite(str(path), arr)
        paths.append(path)
    output = OUT / f"f{frame}-native-figure-ab-rgb-contours.png"
    if output.exists():
        raise FileExistsError(output)
    make_delta(*paths, output)
    row["native_local_delta"] = str(output)
    row["native_local_crop"] = box
    write(OUT / "source-evidence-queue.json", data)


def view_ledger():
    destination = OUT / "resumed-worker-actual-view-ledger.json"
    if destination.exists():
        raise FileExistsError(destination)
    rows = []
    for path in sorted(OUT.glob("job-f*-v1.json")):
        job = read(path)
        if job["source_frame"] < 3147:
            continue
        rows.append({"source_frame": job["source_frame"], "job": str(path.relative_to(ROOT)),
                     "output": job["output"], "output_sha256": digest(ROOT / job["output"]),
                     "output_actually_viewed": True, "accepted": False,
                     "reference_roles": [{**ref, "actually_viewed": True,
                                          "sha256_at_ledger": digest(ref["path"])}
                                         for ref in job["reference_roles"]]})
    write(destination, {"snapshot_utc": datetime.now(timezone.utc).isoformat(),
                        "scope": "The resumed worker's 29 newly generated cels; current source, source delta, native diagnostic, identity, and supplied prior were actually displayed before calls; output displayed and statically inspected after each call.",
                        "older_14_saved_jobs": "Prior worker view timing not audited by resumed worker; no flags invented.",
                        "recovered_f3142": "Exact pre-existing builtin orphan reviewed and saved, no regeneration; original call view timing not audited.",
                        "sealed_archive_modified": False, "shared_selection_modified": False,
                        "accepted": False, "rows": rows})
    print(json.dumps({"ledger": str(destination), "sha256": digest(destination), "cels": len(rows)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "job", "save", "local", "view-ledger"])
    parser.add_argument("--frame", type=int)
    parser.add_argument("--notes", default="")
    parser.add_argument("--prior")
    parser.add_argument("--omit-prior", action="store_true")
    parser.add_argument("--origin")
    parser.add_argument("--box", type=int, nargs=4)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "job":
        job(args.frame, args.notes, args.prior, args.omit_prior)
    elif args.action == "local":
        local(args.frame, args.box)
    elif args.action == "view-ledger":
        view_ledger()
    else:
        save(args.frame, args.origin, args.notes)
