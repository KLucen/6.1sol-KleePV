"""Shot-specific two-actor source evidence; builtin outputs archived unchanged."""

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
FRAMES = [2132, 2135, 2136, 2138, 2141, 2143]
BOXES = {"foreground-eyes-mouth-cheeks": (1070, 270, 1920, 1080),
         "foreground-hat-bangs": (820, 0, 1720, 460),
         "background-visible-hand-coat-legs": (650, 80, 1180, 1080)}
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta

spec = importlib.util.spec_from_file_location("private_late_archive_helper", ROOT / "qa/late-oct6-worker.py")
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)
archive.OUT, archive.FRAMES = QA, FRAMES


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def prepare():
    queue_path = QA / "missing-source-reference-queue.json"
    if queue_path.exists():
        raise FileExistsError("Preserve existing source evidence")
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    rows = manifest["cels"]
    lookup = {r["canonical_source_frame"]: r for r in rows}
    previous = {f: rows[rows.index(lookup[f]) - 1]["canonical_source_frame"] for f in FRAMES}
    wanted = set(FRAMES) | set(previous.values()) | {2115, 2121, 2145}
    decoded = {}
    cap = cv2.VideoCapture(manifest["source"])
    for f in range(max(wanted) + 1):
        ok, image = cap.read()
        if not ok:
            raise RuntimeError(f"Source decode failed f{f}")
        if f in wanted:
            canonical = ROOT / lookup[f]["source_reference"]
            assert np.array_equal(image, cv2.imread(str(canonical))), f"Source reference mismatch f{f}"
            decoded[f] = image
            cv2.imwrite(str(QA / f"f{f}-source-actual.png"), image)
    cap.release()
    queue = []
    for f in [*FRAMES, 2121]:
        row = lookup[f]
        assert row["selected_asset"] is None, f"Already selected f{f}"
        p = previous[f] if f != 2121 else 2115
        a, b = decoded[p], decoded[f]
        source = QA / f"f{f}-source-actual.png"
        delta = QA / f"f{p}-f{f}-source-ab-rgb-contours.png"
        make_delta(QA / f"f{p}-source-actual.png", source, delta)
        foreground = QA / f"f{f}-foreground-native.png"
        background = QA / f"f{f}-background-visible-native.png"
        cv2.imwrite(str(foreground), b[0:1080, 800:1920])
        cv2.imwrite(str(background), b[80:1080, 650:1180])
        local_paths = []
        for name, (x1, y1, x2, y2) in BOXES.items():
            if f == 2121:
                x1, y1, x2, y2 = ({"foreground-eyes-mouth-cheeks": (460, 60, 920, 480),
                                   "foreground-hat-bangs": (190, 120, 1450, 570),
                                   "background-visible-hand-coat-legs": (440, 470, 1370, 1080)})[name]
                if x2 - x1 > 1000:
                    x2 = x1 + 1000
            aa, bb = a[y1:y2, x1:x2], b[y1:y2, x1:x2]
            h, w = bb.shape[:2]
            diff = np.minimum(cv2.absdiff(aa, bb).astype(np.uint16) * 4, 255).astype(np.uint8)
            ea, eb = cv2.Canny(aa, 80, 160), cv2.Canny(bb, 80, 160)
            contours = np.full_like(aa, 245)
            contours[ea != 0], contours[eb != 0] = (235, 110, 30), (30, 80, 235)
            contours[(ea != 0) & (eb != 0)] = (50, 50, 50)
            canvas = Image.new("RGB", (w * 2, (h + 28) * 2), "#202024")
            draw = ImageDraw.Draw(canvas)
            for i, (arr, title) in enumerate(zip((aa, bb, diff, contours),
                                (f"f{p} BEFORE", f"f{f} CURRENT", "RGB x4", "blue BEFORE/red CURRENT"))):
                x, y = i % 2 * w, i // 2 * (h + 28)
                draw.text((x + 6, y + 6), name + ": " + title + " native pixels", fill="white")
                canvas.paste(Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)), (x, y + 28))
            local = QA / f"f{f}-{name}-native-ab-rgb-contours.png"
            canvas.save(local)
            local_paths.append(str(local))
        queue.append({"source_frame": f, "cel": row["cel"], "source_candidate": row["source_candidate"],
                      "current_source": str(source), "source_reference": row["source_reference"],
                      "source_sha256": digest(source), "sequential_original_exact": True,
                      "before_source_frame": p, "actual_delta": str(delta),
                      "foreground_native": str(foreground), "background_visible_native": str(background),
                      "native_delta_files": local_paths, "source_exposures": row["source_exposures"],
                      "generation_target": f in FRAMES, "source_only_alias_review": f == 2121, "accepted": False})
    queue_path.write_text(json.dumps({"queue": queue, "sequential_decode": [0, max(wanted) + 1],
                                      "exact_source_frames": sorted(wanted), "source_boxes": BOXES,
                                      "artwork_generated": False, "aliases_created": False}, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(queue_path), "targets": FRAMES, "source_only_repeat_test": [2115, 2121],
                      "exact_source_checks": len(wanted)}))


def seal():
    jobs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(QA.glob("job-f*-v*.json"))]
    proposal = json.loads((QA / "draft-proposal.json").read_text(encoding="utf-8"))
    selected = {r["path"] for r in proposal["selections"]}
    checks = []
    for job in jobs:
        output, origin = ROOT / job["output"], Path(job["tool_output"])
        refs = [{"path": r["path"], "role": r["role"], "sha256_at_final_archive": digest(Path(r["path"]))}
                for r in job["reference_roles"]]
        checks.append({"output": job["output"], "source_frame": job["source_frame"],
                       "sha256": digest(output), "recorded_sha_exact": digest(output) == job["output_sha256"],
                       "builtin_origin_byte_exact": output.read_bytes() == origin.read_bytes(), "references": refs,
                       "dimensions": list(Image.open(output).size), "selected_private": job["output"] in selected})
    q = json.loads((QA / "missing-source-reference-queue.json").read_text(encoding="utf-8"))["queue"]
    coverage = sum(e["end"] - e["start"] for r in q if r["generation_target"] for e in r["source_exposures"])
    for start in range(0, len(FRAMES), 3):
        page = Image.new("RGB", (1280, 3 * 384), "#202024")
        draw = ImageDraw.Draw(page)
        for i, f in enumerate(FRAMES[start:start + 3]):
            row = next(r for r in proposal["selections"] if r["source_frame"] == f)
            current = next(r for r in q if r["source_frame"] == f)
            draw.text((8, i * 384 + 6), f"f{f} SOURCE left / UNACCEPTED DRAFT right", fill="white")
            for k, p in enumerate((Path(current["current_source"]), ROOT / row["path"])):
                page.paste(Image.open(p).convert("RGB").resize((640, 360), Image.Resampling.LANCZOS), (k * 640, i * 384 + 24))
        page.save(QA / f"source-new-consecutive-page-{start // 3 + 1:02d}.png")
    path = QA / "full-builtin-promptset.json"
    if path.exists():
        raise FileExistsError("Preserve old archive")
    report = {"snapshot_utc": datetime.now(timezone.utc).isoformat(), "jobs": jobs, "integrity": checks,
              "successful_builtin_outputs": len(jobs), "unique_missing_true_source_cels": len(FRAMES),
              "selected_private_drafts": len(selected), "source_exposure_frames": coverage,
              "source_only_alias2121_not_adopted": True, "accepted": False,
              "compositor_and_actual_speed_review": "not_performed", "shared_files_written": []}
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"archive": str(path), "sha256": digest(path), "outputs": len(jobs),
                      "unique_cels": len(FRAMES), "selected_drafts": len(selected), "source_frames": coverage,
                      "integrity_ok": all(c["recorded_sha_exact"] and c["builtin_origin_byte_exact"] for c in checks)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "save", "seal"])
    parser.add_argument("--frame", type=int)
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--origin")
    parser.add_argument("--notes")
    parser.add_argument("--unselected", action="store_true")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "save":
        archive.save(args.frame, args.origin, args.notes, args.version, args.unselected)
    else:
        seal()
