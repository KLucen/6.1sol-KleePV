"""Private Oct7 source diagnostics and full-cel builtin draft archive."""

import argparse
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


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def evidence():
    queuepath = OUT / "source-evidence-queue.json"
    document = read(queuepath)
    rows = read(ROOT / "full-pv-progress-manifest.json")["cels"]
    lookup = {r["canonical_source_frame"]: r for r in rows}
    for row in document["queue"]:
        f = row["canonical_source_frame"]
        p = rows[rows.index(lookup[f]) - 1]["canonical_source_frame"]
        before, current = ROOT / lookup[p]["source_reference"], ROOT / row["source_reference"]
        delta = OUT / f"f{p}-f{f}-source-ab-rgb-contours.png"
        if not delta.exists():
            make_delta(before, current, delta)
        a, b = cv2.imread(str(before)), cv2.imread(str(current))
        if row["canonical_family"] == "cyan_profile":
            regions = [("eye-mouth-bangs", (1160, 290, 1450, 690)),
                       ("rear-hair-tip", (100, 650, 750, 1080)),
                       ("collar-near-hair", (960, 680, 1330, 950)),
                       ("visible-hands", (1460, 650, 1920, 1080)),
                       ("visible-hands-wide", (1250, 450, 1850, 1050))]
        elif row["canonical_family"] == "wink_closeup":
            regions = [("foreground-eye-mouth", (1420, 220, 1920, 780)),
                       ("foreground-hair-rear-actor", (950, 540, 1510, 1040))]
        else:
            regions = [("upper-head-hand", (700, 80, 1200, 530)),
                       ("lower-pose-hair", (920, 550, 1480, 1050))]
        nativepaths = []
        for name, (x1, y1, x2, y2) in regions:
            aa, bb = a[y1:y2, x1:x2], b[y1:y2, x1:x2]
            h, w = aa.shape[:2]
            diff = np.minimum(cv2.absdiff(aa, bb).astype(np.uint16) * 4, 255).astype(np.uint8)
            ea, eb = cv2.Canny(aa, 80, 160), cv2.Canny(bb, 80, 160)
            contours = np.full_like(aa, 245)
            contours[ea != 0] = (235, 110, 30)
            contours[eb != 0] = (30, 80, 235)
            contours[(ea != 0) & (eb != 0)] = (50, 50, 50)
            panel = Image.new("RGB", (w * 2, h * 2 + 48), "#202024")
            draw = ImageDraw.Draw(panel)
            draw.text((8, 5), f"{name}: f{p} BEFORE / f{f} CURRENT; native pixels", fill="white")
            for arr, x, y in [(aa, 0, 24), (bb, w, 24), (diff, 0, h + 48), (contours, w, h + 48)]:
                panel.paste(Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)), (x, y))
            path = OUT / f"f{p}-f{f}-{name}-native.png"
            if not path.exists():
                panel.save(path)
            nativepaths.append(str(path))
        row.update({"source_frame": f, "before_source_frame": p,
                    "current_source": str(current), "source_sha256": digest(current),
                    "actual_delta": str(delta), "native_local_deltas": nativepaths,
                    "accepted": False})
    document.update({"character_artwork_generated_by_diagnostics": False,
                     "source_map_edited": False, "aliases_created": False})
    write(queuepath, document)
    print(json.dumps({"queue": str(queuepath), "cels": len(document["queue"])}))


def prepare(frame, notes, prior):
    row = next(r for r in read(OUT / "source-evidence-queue.json")["queue"] if r["source_frame"] == frame)
    identity = ROOT / "qa/standing-open-eye-identity-crop.png"
    refs = [{"path": row["current_source"], "role": "Current original source: sole pose, expression, crop, visible actor count and occlusion authority."},
            {"path": str(identity), "role": "Klee identity only: red clover beret, white feather, short blonde twin ponytails, pointed ears and red eyes; not a pose template."},
            {"path": row["actual_delta"], "role": "Actual previous/current original A/B, amplified RGB difference and blue-before/red-current contours; follow current state."},
            {"path": row["native_local_deltas"][0], "role": "Native source local changes of eyelid, mouth, bangs or visible contour; preserve current visibility."}]
    if 2231 <= frame < 2253:
        refs[3] = {"path": row["native_local_deltas"][-1], "role": "Native actual source hand A/B, RGB and contours: match the current gesture and edge crop with brown Klee gloves; no extra hands."}
    if prior:
        refs.append({"path": str((ROOT / prior).resolve()), "role": "Adjacent Klee draft: simplified PV ink, palette and persistent hairstyle only; do not freeze its pose or crop."})
    prompt = "\n".join([
        "Use case: identity-preserve. Asset: one complete replacement cel for the existing MIMI hand-drawn music-video animation.",
        "Replace EVERY visible original person in image 1 with Klee from Genshin Impact. Redraw the entire requested cel, not little patches or a contact sheet.",
        "Reference roles in exact order: " + " ".join(f"Image {i + 1}: {r['role']}" for i, r in enumerate(refs)),
        f"Current source frame f{frame}; original predecessor f{row['before_source_frame']}. Actual observed current pose and changes: {notes}",
        "The current original is the only authority for camera position, size, body lean, eye aperture, mouth, visible hands, edge crops and front/back layering. Closely follow its actual delta, not a new pose.",
        "Klee has short blonde two ponytails, never the original long pink hair or animal sleep mask. In cool lighting blonde may be pale bluish, but identity remains blonde. Red clover beret, white feather, pointed ears, red eyes if visible. Red coat with plain cream collar and cuffs, brown gloves and brown boots if visible. No invented ruffles or extra hands.",
        "Keep the same simple flat hand-drawn PV proportions, loose dark contour, restrained shading and warm/cool source lighting. Preserve original sky and independent effects and props where present. Keep prop geometry and correct hand/prop occlusion.",
        "No captions, letters, text or watermark in generated cel; subtitles will be restored independently. Do not add a face, body, hand or second actor that is outside the current source crop. Do not retain any original person.",
        "Output a single full 16:9 composition matching source framing, not a split comparison, collage, diagram or standalone model sheet."
    ])
    job = {"source_frame": frame, "cel": row["cel"], "source_candidate": row["source_candidate"],
           "tool": "builtin_imagegen", "status": "prepared", "accepted": False,
           "output": f"generated/oct7-bulk-middle-f{frame}-v1.png", "prompt": prompt,
           "reference_roles": refs, "referenced_image_paths": [r["path"] for r in refs],
           "source_exposures": row["source_exposures"], "observed_source_notes": notes,
           "reference_inputs_actually_viewed": True, "temporal_review": {"performed": False, "accepted": False}}
    path = OUT / f"job-f{frame}-v1.json"
    if path.exists() or (ROOT / job["output"]).exists():
        raise FileExistsError("Never overwrite jobs or artwork")
    write(path, job)
    print(json.dumps(job, ensure_ascii=False))


def save(frame, origin, notes):
    spec = importlib.util.spec_from_file_location("archive_oct6", ROOT / "qa/late-oct6-worker.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = OUT
    module.save(frame, origin, notes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", action="store_true")
    parser.add_argument("--prepare", type=int)
    parser.add_argument("--prior")
    parser.add_argument("--notes")
    parser.add_argument("--save", type=int)
    parser.add_argument("--origin")
    args = parser.parse_args()
    if args.evidence:
        evidence()
    elif args.prepare:
        prepare(args.prepare, args.notes, args.prior)
    elif args.save:
        save(args.save, args.origin, args.notes)
