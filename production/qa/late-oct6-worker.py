"""Prepare verified source evidence and archive private late-cel builtin jobs."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa/late-missing-2026-10-06"
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta

FRAMES = [2829, 2834, 2838, 2843, 2847, 2906]
REGIONS = [("face_hat_hair", (1070, 170, 1440, 400)),
           ("both_hands_cuffs_pillow", (1070, 330, 1470, 565)),
           ("legs_ankles_boot_overlap", (1120, 535, 1580, 940))]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def prepare():
    queue_path = OUT / "missing-source-reference-queue.json"
    if queue_path.exists():
        raise FileExistsError("Preserve saved evidence, do not overwrite")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    rows = manifest["cels"]
    lookup = {r["canonical_source_frame"]: r for r in rows}
    previous = {f: rows[rows.index(lookup[f]) - 1]["canonical_source_frame"] for f in FRAMES}
    wanted = set(FRAMES) | set(previous.values())
    decoded = {}
    cap = cv2.VideoCapture(manifest["source"])
    for f in range(max(wanted) + 1):
        ok, image = cap.read()
        if not ok:
            raise ValueError(f"Source failed at f{f}")
        if f in wanted:
            canonical = ROOT / lookup[f]["source_reference"]
            assert np.array_equal(image, cv2.imread(str(canonical))), f"Canonical mismatch f{f}"
            path = OUT / f"f{f}-source-actual.png"
            cv2.imwrite(str(path), image)
            decoded[f] = image
    cap.release()
    queue = []
    for f in FRAMES:
        row = lookup[f]
        assert row["selected_asset"] is None, f"Already mapped f{f}"
        p = previous[f]
        a, b = decoded[p], decoded[f]
        source = OUT / f"f{f}-source-actual.png"
        delta = OUT / f"f{p}-f{f}-source-ab-rgb-contours.png"
        make_delta(OUT / f"f{p}-source-actual.png", source, delta)
        total_h = sum((box[3] - box[1]) * 2 + 64 for _, box in REGIONS)
        locals_image = Image.new("RGB", (1000, total_h), "#202024")
        draw = ImageDraw.Draw(locals_image)
        y = 0
        for name, (x1, y1, x2, y2) in REGIONS:
            aa, bb = a[y1:y2, x1:x2], b[y1:y2, x1:x2]
            h, w = aa.shape[:2]
            diff = np.minimum(cv2.absdiff(aa, bb).astype(np.uint16) * 4, 255).astype(np.uint8)
            ea, eb = cv2.Canny(aa, 80, 160), cv2.Canny(bb, 80, 160)
            contours = np.full_like(aa, 245)
            contours[ea != 0] = (235, 110, 30)
            contours[eb != 0] = (30, 80, 235)
            contours[(ea != 0) & (eb != 0)] = (50, 50, 50)
            draw.text((8, y + 6), f"{name}: f{p} BEFORE / f{f} CURRENT; native pixels", fill="white")
            for arr, x, yy in [(aa, 0, y + 28), (bb, 500, y + 28),
                               (diff, 0, y + h + 52), (contours, 500, y + h + 52)]:
                locals_image.paste(Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)), (x, yy))
            y += h * 2 + 64
        local = OUT / f"f{p}-f{f}-source-locals-native.png"
        locals_image.save(local)
        face = OUT / f"f{f}-source-face-native.png"
        pose = OUT / f"f{f}-source-pose-native.png"
        cv2.imwrite(str(face), b[170:400, 1070:1440])
        cv2.imwrite(str(pose), b[170:940, 1070:1580])
        queue.append({"source_frame": f, "cel": row["cel"], "source_candidate": row["source_candidate"],
                      "current_source": str(source), "source_sha256": digest(source),
                      "sequential_original_exact": True, "before_source_frame": p,
                      "actual_delta": str(delta), "native_local_delta": str(local),
                      "native_face_crop": str(face), "native_pose_crop": str(pose),
                      "source_exposures": row["source_exposures"], "accepted": False})
    queue_path.write_text(json.dumps({"queue": queue, "sequential_decode": [0, max(wanted) + 1],
                                      "artwork_generated": False, "aliases_created": False}, indent=2), encoding="utf-8")
    print(queue_path)


def save(frame, origin, notes, version=1, unselected=False):
    jobpath = OUT / f"job-f{frame}-v{version}.json"
    job = json.loads(jobpath.read_text(encoding="utf-8"))
    origin = Path(origin)
    target = ROOT / job["output"]
    if target.exists():
        raise FileExistsError("Never overwrite generated artwork")
    target.write_bytes(origin.read_bytes())
    shape = list(cv2.imread(str(target)).shape[:2][::-1])
    job.update({"status": "blocked_static_unselected" if unselected else "reviewed_static_temporal_pending", "tool_output": str(origin),
                "output_sha256": digest(target), "dimensions": shape,
                "static_review": {"performed": True, "scope": "single cel and adjacent source/Klee static only",
                                  "notes": notes, "accepted": False},
                "temporal_review": {"performed": False, "accepted": False}})
    jobpath.write_text(json.dumps(job, indent=2), encoding="utf-8")
    if unselected:
        print(json.dumps({"frame": frame, "path": str(target), "sha256": digest(target),
                          "dimensions": shape, "selected": False}))
        return
    proposalpath = OUT / "draft-proposal.json"
    proposal = json.loads(proposalpath.read_text(encoding="utf-8")) if proposalpath.exists() else {"accepted": False, "selections": []}
    proposal["selections"].append({"source_frame": frame, "path": job["output"], "accepted": False,
                                   "review": "draft_static_only; " + notes,
                                   "known_issues": [notes], "job": str(jobpath.relative_to(ROOT)),
                                   "sha256": digest(target)})
    proposalpath.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    print(json.dumps({"frame": frame, "path": str(target), "sha256": digest(target), "dimensions": shape}))


def seal():
    jobs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(OUT.glob("job-f*-v*.json"))]
    proposal = json.loads((OUT / "draft-proposal.json").read_text(encoding="utf-8"))
    selected_paths = {x["path"] for x in proposal["selections"]}
    checks = []
    for job in jobs:
        target, origin = ROOT / job["output"], Path(job["tool_output"])
        refs = [{"path": r["path"], "role": r["role"], "sha256_at_final_archive": digest(Path(r["path"]))}
                for r in job["reference_roles"]]
        checks.append({"source_frame": job["source_frame"], "output": job["output"],
                       "sha256": digest(target), "job_output_sha_exact": digest(target) == job["output_sha256"],
                       "builtin_origin_byte_exact": target.read_bytes() == origin.read_bytes(),
                       "dimensions": list(cv2.imread(str(target)).shape[:2][::-1]),
                       "selected_in_private_proposal": job["output"] in selected_paths,
                       "accepted": job["accepted"], "references": refs})
        image = cv2.imread(str(target))
        cv2.imwrite(str(OUT / f"{target.stem}-native-figure.png"), image[120:835, 900:1430])
    queue = json.loads((OUT / "missing-source-reference-queue.json").read_text(encoding="utf-8"))["queue"]
    coverage = sum(e["end"] - e["start"] for r in queue for e in r["source_exposures"])
    archive = {"date": "2026-10-06", "tool": "builtin_imagegen", "successful_output_count": len(jobs),
               "unique_true_source_cels": len(queue), "private_selected_drafts": len(selected_paths),
               "rejected_generated_variants": len(jobs) - len(selected_paths),
               "argument_validation_attempts_with_no_generated_output": 1,
               "source_frame_coverage_if_parent_adopts_existing_source_exposures": coverage,
               "jobs": jobs, "integrity": checks, "accepted": False,
               "art_acceptance": "Not performed; individual and adjacent static reviews only",
               "temporal_speed_review": "Not performed", "shared_selection_edited": False}
    archive_path = OUT / "full-builtin-promptset-and-integrity.json"
    if archive_path.exists():
        raise FileExistsError("Never overwrite sealed promptset")
    archive_path.write_text(json.dumps(archive, indent=2), encoding="utf-8")
    print(json.dumps({"archive": str(archive_path), "sha256": digest(archive_path),
                      "successful_outputs": len(jobs), "unique_cels": len(queue), "private_drafts": len(selected_paths),
                      "source_frames": coverage,
                      "technical_assets_ok": all(c["job_output_sha_exact"] and c["builtin_origin_byte_exact"]
                                                 and not c["accepted"] for c in checks)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", type=int)
    parser.add_argument("--origin")
    parser.add_argument("--notes")
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--unselected", action="store_true")
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    if args.seal:
        seal()
    elif args.save:
        save(args.save, args.origin, args.notes, args.version, args.unselected)
    else:
        prepare()
