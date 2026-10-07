"""Prepare late-owner source references and per-cel jobs, never synthesize artwork."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw
from delta_reference import make_delta

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "qa" / "late-worker"


def records():
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    return [c for c in manifest["cels"] if c["canonical_source_frame"] >= 2400]


def contacts(family):
    items = [c for c in records() if c["canonical_family"] == family]
    OUT.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(items), 12):
        page = items[start:start + 12]
        canvas = Image.new("RGB", (1920, 4 * 392), "#25252a")
        draw = ImageDraw.Draw(canvas)
        for i, c in enumerate(page):
            x, y = (i % 3) * 640, (i // 3) * 392
            draw.text((x + 8, y + 8), f"{c['cel']} SOURCE f{c['canonical_source_frame']}", fill="white")
            im = Image.open(ROOT / c["source_reference"]).convert("RGB").resize((640, 360))
            canvas.paste(im, (x, y + 32))
        path = OUT / f"{family}-source-{start // 12 + 1:02d}.jpg"
        canvas.save(path, quality=95)
        print(path)


def delta(frame):
    all_items = records()
    current = next(c for c in all_items if c["canonical_source_frame"] == frame)
    previous = [c for c in all_items if c["canonical_source_frame"] < frame]
    if not previous:
        return
    previous = previous[-1]
    make_delta(ROOT / previous["source_reference"], ROOT / current["source_reference"],
               OUT / f"source-f{previous['canonical_source_frame']:04d}-f{frame:04d}-delta.png")


def queue():
    current = []
    for c in records():
        f = c["canonical_source_frame"]
        files = sorted((ROOT / "generated").glob(f"fine-f{f:04d}*.png"))
        c["current_saved_siblings"] = [str(p.relative_to(ROOT)) for p in files]
        if files or c.get("selected_asset"):
            c["worker_status"] = "saved_draft_review_required"
        else:
            c["worker_status"] = "missing"
        current.append(c)
    path = OUT / "late-owner-queue.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"scope": "canonical late-owner cels only", "accepted": False,
                               "cels": current}, indent=2), encoding="utf-8")
    print(json.dumps({"canonical_cels": len(current), "missing": sum(c["worker_status"] == "missing" for c in current), "path": str(path)}))


def prepare(frame, notes, prior):
    current = next(c for c in records() if c["canonical_source_frame"] == frame)
    target = ROOT / "generated" / f"fine-f{frame:04d}.png"
    jobpath = ROOT / "jobs" / f"fine-f{frame:04d}.json"
    if target.exists() or jobpath.exists():
        raise ValueError("Existing generated output or job must not be overwritten")
    candidates = [c for c in records() if c["canonical_source_frame"] < frame]
    refs = [{"path": str(ROOT / current["source_reference"]), "role": "current_source_pose_crop_and_occlusion"},
            {"path": str(ROOT / "qa" / "standing-open-eye-identity-crop.png"), "role": "klee_identity_only_not_pose_or_eye_state"},
            {"path": str(ROOT / "qa" / "standing-costume-crop.png"), "role": "klee_costume_only_not_pose"}]
    if candidates:
        before = candidates[-1]
        diff = OUT / f"source-f{before['canonical_source_frame']:04d}-f{frame:04d}-delta.png"
        if not diff.exists():
            make_delta(ROOT / before["source_reference"], ROOT / current["source_reference"], diff)
        refs.append({"path": str(diff), "role": "actual_source_spatial_delta_after_red_contours"})
    if prior:
        refs.append({"path": str(ROOT / prior), "role": "adjacent_klee_topology_line_color_only_not_frozen_pose"})
    prompt = (
        "Use case: identity-preserve. EDIT ORIGINAL IMAGE1 IN PLACE as ONE independent full-frame 16:9 cel for a strict source-exposure hand-drawn PV. "
        "Keep image1 exact spatial layout and enormous empty margins. Replace the visible human only inside its original bounds; do not enlarge or recenter the figure. "
        "Preserve all source props at identical image1 size and positions, especially the lavender pillow; do not expand the pillow. "
        "Image1 is CURRENT original target and sole authority for framing, head/body size, pose, expression, eye state, limb positions, "
        "cropping, all visible people and occlusion. Images2/3 are cropped Klee IDENTITY and COSTUME only; do not copy their poses or eye state. "
        "The source difference diagram, when present, controls actual local contour change: follow AFTER/red current, not BEFORE/blue. "
        "Any final adjacent Klee drawing only maintains short-ponytail topology, costume cut, palette and loose source-like lines, never freezes pose. "
        "Replace EVERY visible person/partial person with Genshin Klee, keeping exact original screen size and proportions, not smaller chibi. "
        "Pale blonde bangs, exactly TWO SHORT ear-root side ponytails, pointed ears, RED iris with BLACK pupil and WHITE highlight when open, red beret with cream clover white feather and side badge, "
        "red coat/capelet cream trim and skirt hem, PLAIN cream cuffs without scallops/frills, brown gloves and boots, small brown backpack where visible. "
        "Replace original rabbit sleep mask rather than adding it on Klee; no old pink long hair, gray pajamas or bare original hands. No long ponytails, added clovers on cuffs/hem/coat, cuff labels or extra exposed hands. "
        "Loose black hand-drawn contours, flat areas, orange source-like cheek ovals, restrained simple shading, not polished game splash art. "
        "Keep original background and all independent props/stars/effects in original positions and depth. Only source-visible body exists; "
        "never add missing feet/face/hands outside crop or reveal anatomy behind an opaque object. "
        "No text, captions, Japanese/Chinese/English letters, credits, numbers, logos, watermark or diagram. "
        "Remove source caption glyphs to matching field; compositor restores exact current-source graphics later. "
        "CURRENT SOURCE f" + str(frame) + ": " + notes)
    job = {"source_frame": frame, "source_cel": current["cel"], "source_candidate": current["source_candidate"],
           "output": str(target.relative_to(ROOT)), "status": "prepared", "accepted": False, "tool": "builtin_imagegen", 
           "prompt": prompt, "references": refs, "static_review": {"performed": False},
           "temporal_review": {"performed": False, "accepted": False}, "source_exposure_strategy": "strict_source"}
    jobpath.write_text(json.dumps(job, indent=2), encoding="utf-8")
    print(json.dumps({"job_path": str(jobpath), "job": job}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--contacts")
    parser.add_argument("--delta", type=int)
    parser.add_argument("--prepare", type=int)
    parser.add_argument("--notes", default="")
    parser.add_argument("--prior")
    args = parser.parse_args()
    if args.prepare is not None:
        prepare(args.prepare, args.notes, args.prior)
    elif args.contacts:
        contacts(args.contacts)
    elif args.delta is not None:
        delta(args.delta)
    else:
        queue()
