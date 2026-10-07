"""Private sequential-original closeup evidence; no character art or shared edits."""

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta

spec = importlib.util.spec_from_file_location(
    "source_native_panels", ROOT / "qa/standing-repeat-audit-2026-10-05/audit_source_repeats.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)

TARGETS = [1162, 1164, 1172, 1187, 1195, 1199, 1203, 1211, 1216, 1221]
WIDE = (180, 0, 1750, 1080)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def layout(frame):
    if frame <= 1164:
        return {
            "face": (775, 325, 1135, 675),
            "left-hand-cuff": (300, 450, 660, 1040),
            "right-hand-cuff": (1290, 410, 1650, 1000),
            "hat-left": (630, 35, 990, 335),
            "hat-right": (990, 35, 1350, 335),
            "collar-hair": (785, 600, 1145, 950),
        }
    if frame <= 1172:
        return {
            "face": (650, 320, 1010, 690),
            "left-hand-cuff": (200, 610, 560, 1080),
            "right-hand-cuff": (1040, 50, 1400, 460),
            "hat-left": (485, 35, 845, 335),
            "hat-right": (845, 35, 1205, 335),
            "collar-hair": (730, 585, 1090, 940),
        }
    if frame <= 1187:
        return {
            "face": (990, 310, 1350, 690),
            "left-hand-cuff": (720, 0, 1080, 400),
            "right-hand-cuff": (1330, 25, 1690, 460),
            "hat-left": (900, 35, 1260, 335),
            "hat-right": (1260, 35, 1620, 335),
            "collar-hair": (990, 560, 1350, 930),
        }
    return {
        "face": (825, 480, 1185, 830),
        "left-hand-cuff": (580, 415, 940, 825),
        "right-hand-cuff": (1050, 415, 1410, 825),
        "hat-left": (685, 140, 1045, 475),
        "hat-right": (1045, 140, 1405, 475),
        "collar-hair": (825, 710, 1185, 1080),
    }


def local_page(a, b, earlier, frame, entries, path):
    width = 360
    heights = [box[3] - box[1] + 32 for _, box in entries]
    canvas = Image.new("RGB", (width * 4, sum(heights)), "#242428")
    draw = ImageDraw.Draw(canvas)
    panels = native.panels(a, b)
    labels = [f"original f{earlier}", f"original f{frame}", "actual RGB diff x4", "blue before / red current"]
    y = 0
    for (name, (x0, y0, x1, y1)), height in zip(entries, heights):
        assert x1 - x0 <= width
        for col, (panel, label) in enumerate(zip(panels, labels)):
            draw.text((col * width + 6, y + 9), f"{name}: {label}", fill="white")
            crop = cv2.cvtColor(panel[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
            canvas.paste(Image.fromarray(crop), (col * width, y + 32))
        y += height
    canvas.save(path)


def crop(image, box, path):
    x0, y0, x1, y1 = box
    cv2.imwrite(str(path), image[y0:y1, x0:x1])
    return {"path": str(path), "sha256": digest(path), "native_box": list(box), "resized": False}


def main():
    report_path = OUT / "closeup-source-reference-queue.json"
    if report_path.exists():
        raise FileExistsError("Private queue already saved; do not replace frozen proof.")
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    rows = manifest["cels"]
    by_frame = {row["canonical_source_frame"]: row for row in rows}
    candidates = {row["frame"]: row for row in source_map["candidates"]}
    previous = {frame: rows[rows.index(by_frame[frame]) - 1]["canonical_source_frame"] for frame in TARGETS}
    wanted = set(TARGETS) | set(previous.values()) | {1161, 1162, 1163}
    saved = {}
    decoded = {}
    capture = cv2.VideoCapture(manifest["source"])
    for frame in range(max(wanted) + 1):
        ok, bgr = capture.read()
        if not ok:
            raise ValueError(f"Original sequential decode failed f{frame}")
        if frame not in wanted:
            continue
        reference = ROOT / candidates[frame]["reference"]
        assert np.array_equal(bgr, cv2.imread(str(reference))), f"Canonical source mismatch f{frame}"
        path = OUT / f"f{frame:04d}-source-actual.png"
        cv2.imwrite(str(path), bgr)
        decoded[frame] = bgr
        saved[str(frame)] = {"path": str(path), "png_sha256": digest(path),
            "decoded_bgr_sha256": sha256(bgr.tobytes()).hexdigest(),
            "source_id": candidates[frame]["id"], "source_reference": str(reference),
            "source_reference_sha256": digest(reference), "exact_canonical_source": True,
            "pts": meta["pts"][frame]}
    capture.release()
    queue = []
    for frame in TARGETS:
        earlier = previous[frame]
        a, b = decoded[earlier], decoded[frame]
        prefix = OUT / f"f{earlier:04d}-f{frame:04d}"
        full = prefix.with_name(prefix.name + "-full-ab-rgb-contours.png")
        native.write_board(a, b, earlier, frame, (0, 0, 1920, 1080), full)
        delta = prefix.with_name(prefix.name + "-source-ab-rgb-contours.png")
        make_delta(Path(saved[str(earlier)]["path"]), Path(saved[str(frame)]["path"]), delta)
        crops = {}
        for name, panel in zip(["before-wide", "current-wide", "actual-rgb-x4-wide", "dual-contours-wide"], native.panels(a, b)):
            path = prefix.with_name(prefix.name + f"-{name}-native.png")
            crops[name] = crop(panel, WIDE, path)
        regions = list(layout(frame).items())
        pages = []
        for idx, entries in enumerate([regions[:3], regions[3:]], 1):
            path = prefix.with_name(prefix.name + f"-locals-{idx}-native.png")
            local_page(a, b, earlier, frame, entries, path)
            pages.append({"path": str(path), "sha256": digest(path), "regions": dict(entries), "resized": False})
        face = crop(b, layout(frame)["face"], OUT / f"f{frame:04d}-source-face-native.png")
        body = crop(b, WIDE, OUT / f"f{frame:04d}-source-hands-body-native.png")
        queue.append({"source_frame": frame, "cel": by_frame[frame]["cel"],
            "current_source": saved[str(frame)], "before_source_frame": earlier,
            "before_source": saved[str(earlier)], "source_exposures": by_frame[frame]["source_exposures"],
            "actual_delta": str(delta), "actual_delta_sha256": digest(delta),
            "proof_full_native": str(full), "proof_full_native_sha256": digest(full),
            "wide_native_panels": crops, "native_local_pages": pages,
            "native_face_crop": face, "native_body_crop": body,
            "manual_source_delta_review": "pending", "accepted": False})
    for frame in [1161, 1162, 1163]:
        crop(decoded[frame], WIDE, OUT / f"f{frame:04d}-repeat-exposure-actual-native.png")
    repeat_pairs = []
    for frame in [1162, 1163]:
        a, b = decoded[1161], decoded[frame]
        pages = []
        for idx, entries in enumerate([list(layout(1162).items())[:3], list(layout(1162).items())[3:]], 1):
            path = OUT / f"f1161-f{frame:04d}-repeat-locals-{idx}-native.png"
            local_page(a, b, 1161, frame, entries, path)
            pages.append({"path": str(path), "sha256": digest(path)})
        for name, panel in zip(["before-wide", "current-wide", "actual-rgb-x4-wide", "dual-contours-wide"], native.panels(a, b)):
            path = OUT / f"f1161-f{frame:04d}-repeat-{name}-native.png"
            crop(panel, WIDE, path)
        repeat_pairs.append({"before": 1161, "current": frame, "locals": pages,
            "manual_review": "pending", "alias_created": False})
    report = {"source": manifest["source"], "source_sha256": digest(Path(manifest["source"])),
        "source_map_sha256": digest(ROOT / "source_map.json"), "source_meta_sha256": digest(ROOT / "source_meta.json"),
        "sequential_decode": [0, max(wanted) + 1], "exact_source_checks": len(saved),
        "saved_sources": saved, "queue": queue, "repeat_pairs": repeat_pairs,
        "crop_disposition": "New shot-specific closeup proof; old standing crops preserved untouched.",
        "artwork_generated": False, "aliases_created": False, "exposures_changed": False, "accepted": False}
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "exact_source_checks": len(saved), "targets": TARGETS}))


if __name__ == "__main__":
    main()
