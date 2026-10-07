"""Private next-missing whole-cel source evidence and unchanged builtin archival."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
FRAMES = [2145, 2146, 2149, 2151, 2152, 2154]
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta

spec = importlib.util.spec_from_file_location("cold_next_archive_helper", ROOT / "qa/late-oct6-worker.py")
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)
archive.OUT, archive.FRAMES = QA, FRAMES


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def local_page(a, b, name, before, current, path):
    h, w = b.shape[:2]
    rgb = np.minimum(cv2.absdiff(a, b).astype(np.uint16) * 4, 255).astype(np.uint8)
    ae, be = cv2.Canny(a, 80, 160) != 0, cv2.Canny(b, 80, 160) != 0
    contours = np.full_like(b, 245)
    contours[ae], contours[be] = (235, 110, 30), (30, 80, 235)
    contours[ae & be] = (50, 50, 50)
    page = Image.new("RGB", (w * 2, (h + 28) * 2), "#202024")
    draw = ImageDraw.Draw(page)
    for i, (array, title) in enumerate(zip((a, b, rgb, contours),
            (f"f{before} BEFORE", f"f{current} CURRENT", "Actual RGB x4", "blue BEFORE/red CURRENT"))):
        x, y = i % 2 * w, i // 2 * (h + 28)
        draw.text((x + 5, y + 5), name + ": " + title + " native", fill="white")
        page.paste(Image.fromarray(cv2.cvtColor(array, cv2.COLOR_BGR2RGB)), (x, y + 28))
    page.save(path)


def prepare():
    queue_path = QA / "missing-source-reference-queue.json"
    if queue_path.exists():
        raise FileExistsError("Preserve existing prepared source evidence")
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    rows = manifest["cels"]
    lookup = {r["canonical_source_frame"]: r for r in rows}
    actual_targets = [r["canonical_source_frame"] for r in rows
                     if 2145 <= r["canonical_source_frame"] < 2400 and r["selected_asset"] is None][:6]
    assert actual_targets == FRAMES, actual_targets
    previous = {f: rows[rows.index(lookup[f]) - 1]["canonical_source_frame"] for f in FRAMES}
    wanted = set(range(2143, 2155))
    decoded = {}
    cap = cv2.VideoCapture(manifest["source"])
    for f in range(max(wanted) + 1):
        ok, pixels = cap.read()
        if not ok:
            raise RuntimeError(f"Failed source f{f}")
        if f in wanted:
            if f in lookup:
                assert np.array_equal(pixels, cv2.imread(str(ROOT / lookup[f]["source_reference"]))), f
            decoded[f] = pixels
            assert cv2.imwrite(str(QA / f"f{f}-source-actual.png"), pixels)
    cap.release()
    queue = []
    for f in FRAMES:
        row = lookup[f]
        p = previous[f]
        a, b = decoded[p], decoded[f]
        source = QA / f"f{f}-source-actual.png"
        delta = QA / f"f{p}-f{f}-source-ab-rgb-contours.png"
        make_delta(QA / f"f{p}-source-actual.png", source, delta)
        boxes = {"warm-face-eye-mouth": (280, 280, 940, 850),
                 "warm-hat-hair": (260, 0, 1220, 340),
                 "cold-eye-bangs-profile-hat": (1010, 0, 1520, 780)}
        if f == 2154:
            boxes = {"warm-remaining-fragment": (0, 0, 780, 780),
                     "cold-eyes-bangs-mouth-cheek": (830, 215, 1480, 820),
                     "cold-hat-hair-neck-collar": (580, 0, 1510, 1040)}
        locals_list = []
        for name, (x0, y0, x1, y1) in boxes.items():
            path = QA / f"f{f}-{name}-native-ab-rgb-contours.png"
            local_page(a[y0:y1, x0:x1], b[y0:y1, x0:x1], name, p, f, path)
            locals_list.append({"name": name, "box_xyxy": [x0, y0, x1, y1], "path": str(path)})
        # A native current cold face is useful as a pose authority, not an identity donor.
        crop = QA / f"f{f}-current-cold-face-native.png"
        assert cv2.imwrite(str(crop), b[150:800, 970:1530])
        queue.append({"source_frame": f, "cel": row["cel"], "source_candidate": row["source_candidate"],
                      "current_source": str(source), "source_reference": row["source_reference"],
                      "source_sha256": digest(source), "sequential_original_exact": True,
                      "before_source_frame": p, "actual_delta": str(delta), "native_delta_files": locals_list,
                      "native_current_cold_face": str(crop), "source_exposures": row["source_exposures"],
                      "accepted": False})
    queue_path.write_text(json.dumps({"queue": queue, "sequential_decode": [0, 2155],
                                    "decoded_actual_consecutive": [2143, 2155],
                                    "manifest_snapshot_utc": manifest["snapshot_utc"],
                                    "artwork_generated": False, "aliases_created": False}, indent=2), encoding="utf-8")
    print(json.dumps({"queue": str(queue_path), "frames": FRAMES, "source_frames_if_adopted": 10}))


def seal():
    jobs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(QA.glob("job-f*-v*.json"))]
    proposal = json.loads((QA / "draft-proposal.json").read_text(encoding="utf-8"))
    selected = {r["path"] for r in proposal["selections"]}
    checks = []
    for job in jobs:
        output, origin = ROOT / job["output"], Path(job["tool_output"])
        checks.append({"source_frame": job["source_frame"], "output": job["output"], "sha256": digest(output),
                       "recorded_sha_exact": digest(output) == job["output_sha256"],
                       "builtin_origin_byte_exact": output.read_bytes() == origin.read_bytes(),
                       "dimensions": list(Image.open(output).size), "selected_private": job["output"] in selected,
                       "references": [{"path": r["path"], "role": r["role"], "sha256_at_archive": digest(Path(r["path"]))}
                                      for r in job["reference_roles"]]})
    queue = json.loads((QA / "missing-source-reference-queue.json").read_text(encoding="utf-8"))["queue"]
    for start in range(0, len(FRAMES), 3):
        page = Image.new("RGB", (1280, 1152), "#202024")
        draw = ImageDraw.Draw(page)
        for i, f in enumerate(FRAMES[start:start + 3]):
            q = next(r for r in queue if r["source_frame"] == f)
            r = next(r for r in proposal["selections"] if r["source_frame"] == f)
            draw.text((8, i * 384 + 6), f"f{f} SOURCE left / UNACCEPTED DRAFT right", fill="white")
            for j, path in enumerate((Path(q["current_source"]), ROOT / r["path"])):
                page.paste(Image.open(path).convert("RGB").resize((640, 360), Image.Resampling.LANCZOS), (j * 640, i * 384 + 24))
        page.save(QA / f"source-new-consecutive-page-{start // 3 + 1:02d}.png")
    report = {"snapshot_utc": datetime.now(timezone.utc).isoformat(), "tool": "builtin_imagegen", "jobs": jobs,
              "integrity": checks, "successful_builtin_outputs": len(jobs), "unique_missing_true_source_cels": len(FRAMES),
              "private_selected_drafts": len(selected), "source_exposure_frames": 10, "accepted": False,
              "shared_files_modified": [], "compositor_and_actual_speed_review": "not_performed"}
    path = QA / "full-builtin-promptset-and-integrity.json"
    if path.exists():
        raise FileExistsError("Preserve sealed archives")
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"archive": str(path), "sha256": digest(path), "outputs": len(jobs), "drafts": len(selected),
                      "technical_assets_ok": all(c["recorded_sha_exact"] and c["builtin_origin_byte_exact"] for c in checks)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "save", "seal"])
    parser.add_argument("--frame", type=int)
    parser.add_argument("--origin")
    parser.add_argument("--notes")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "save":
        archive.save(args.frame, args.origin, args.notes)
    else:
        seal()
