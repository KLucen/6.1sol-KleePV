"""Private original-source microcel evidence; no mapping or art edits."""

from hashlib import sha256
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PAIRS = [(1097, 1100), (1117, 1118), (1133, 1134), (1216, 1217),
         (1113, 1117), (1129, 1133), (1211, 1216)]
WINDOWS = [(1091, 1106), (1113, 1125), (1129, 1144), (1211, 1225)]
STANDING_REGIONS = [
    ("eyes-mouth", (875, 195, 1055, 325)),
    ("hat-hair-collar", (825, 80, 1170, 380)),
    ("left-hand-sleeve", (650, 285, 980, 585)),
    ("right-hand-sleeve", (960, 280, 1260, 595)),
    ("folds-hem-pockets", (825, 465, 1180, 685)),
    ("legs-cuffs-boots", (775, 675, 1150, 1055)),
]
CLOSE_REGIONS = [
    ("eyes-mouth", (800, 300, 1140, 650)),
    ("hat-hair", (655, 65, 1285, 325)),
    ("left-hand-cuff", (165, 95, 625, 580)),
    ("right-hand-cuff", (1390, 80, 1840, 535)),
    ("collar-coat", (670, 620, 1260, 950)),
    ("left-sleeve-fold", (405, 475, 755, 1030)),
    ("right-sleeve-fold", (1230, 440, 1510, 1035)),
    ("lower-coat-caption", (690, 935, 1230, 1080)),
]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def panels(a, b):
    diff = np.minimum(cv2.absdiff(a, b).astype(np.uint16) * 4, 255).astype(np.uint8)
    ea, eb = [cv2.Canny(im, 80, 160) for im in (a, b)]
    contour = np.full_like(a, 245)
    contour[ea != 0] = (235, 110, 30)
    contour[eb != 0] = (30, 80, 235)
    contour[(ea != 0) & (eb != 0)] = (50, 50, 50)
    return a, b, diff, contour


def board(a, b, earlier, current, box, path, kinds=(0, 1)):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    canvas = Image.new("RGB", (w * len(kinds), h + 32), "#242428")
    draw = ImageDraw.Draw(canvas)
    labels = [f"Original f{earlier} native", f"Original f{current} native",
              "Actual RGB delta x4", "Blue earlier / red current contours"]
    for col, index in enumerate(kinds):
        draw.text((col * w + 8, 10), labels[index], fill="white")
        crop = panels(a, b)[index][y0:y1, x0:x1]
        canvas.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)), (col * w, 32))
    canvas.save(path)


def local_page(a, b, earlier, current, rows, path):
    widths = [box[2] - box[0] for _, box in rows]
    col_w = max(widths)
    heights = [box[3] - box[1] + 32 for _, box in rows]
    canvas = Image.new("RGB", (col_w * 4, sum(heights)), "#242428")
    draw = ImageDraw.Draw(canvas)
    y = 0
    data = panels(a, b)
    for (name, (x0, y0, x1, y1)), height in zip(rows, heights):
        for col, (panel, label) in enumerate(zip(data, [f"f{earlier}", f"f{current}", "RGB x4", "Contours"])):
            draw.text((col * col_w + 8, y + 10), f"{name}: {label}", fill="white")
            canvas.paste(Image.fromarray(cv2.cvtColor(panel[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)),
                         (col * col_w, y + 32))
        y += height
    canvas.save(path)


def numeric_screen(a, b, regions):
    results = {}
    for name, (x0, y0, x1, y1) in regions:
        delta = cv2.absdiff(a[y0:y1, x0:x1], b[y0:y1, x0:x1]).max(axis=2)
        binary = (delta >= 28).astype(np.uint8)
        _, _, rows, _ = cv2.connectedComponentsWithStats(binary, 8)
        components = []
        for x, y, w, h, area in rows[1:]:
            if area >= 8:
                components.append({"box": [int(x + x0), int(y + y0), int(x + x0 + w), int(y + y0 + h)],
                                   "area": int(area)})
        results[name] = {"box": [x0, y0, x1, y1], "max_rgb_delta_mean": float(delta.mean()),
                         "delta_ge28_pixels": int(binary.sum()),
                         "coherent_components_ge8": sorted(components, key=lambda r: -r["area"])[:12]}
    return results


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    candidates = {row["frame"]: row for row in source_map["candidates"]}
    cels = {row["canonical_source_frame"]: row for row in manifest["cels"]}
    shared_names = ["source_map.json", "source_aliases.json", "asset_selections.json"]
    before = {name: digest(ROOT / name) for name in shared_names}
    required = {frame for start, end in WINDOWS for frame in range(start, end)}
    frames, hashes = {}, {}
    cap = cv2.VideoCapture(source_map["source"])
    for frame in range(max(required) + 1):
        ok, image = cap.read()
        if not ok:
            raise RuntimeError(f"Source ended before f{frame}")
        if frame not in required:
            continue
        path = OUT / f"f{frame:04d}-source-actual.png"
        cv2.imwrite(str(path), image)
        frames[frame] = image
        reference = ROOT / candidates[frame]["reference"] if frame in candidates else None
        exact = bool(reference is not None and np.array_equal(image, cv2.imread(str(reference))))
        if reference is not None and not exact:
            raise ValueError(f"Saved original reference not exact f{frame}")
        hashes[str(frame)] = {"path": str(path), "png_sha256": digest(path),
                             "decoded_bgr_sha256": sha256(image.tobytes()).hexdigest(),
                             "pts": meta["pts"][frame],
                             "saved_reference": str(reference) if reference else None,
                             "saved_reference_exact_bgr": exact}
    cap.release()
    pairs = []
    for earlier, current in PAIRS:
        a, b = frames[earlier], frames[current]
        close = earlier >= 1200
        roi = (140, 65, 1850, 1080) if close else (600, 80, 1300, 1055)
        prefix = OUT / f"f{earlier:04d}-f{current:04d}"
        files = {}
        for label, box, kinds in [("full-native-ab", (0, 0, 1920, 1080), (0, 1)),
                                  ("full-rgb-contours", (0, 0, 1920, 1080), (2, 3)),
                                  ("character-native-ab", roi, (0, 1)),
                                  ("character-rgb-contours", roi, (2, 3))]:
            path = prefix.with_name(prefix.name + "-" + label + ".png")
            board(a, b, earlier, current, box, path, kinds)
            files[label] = str(path)
        regions = CLOSE_REGIONS if close else STANDING_REGIONS
        for start in range(0, len(regions), 2):
            path = prefix.with_name(prefix.name + f"-locals-native-page-{start // 2 + 1:02d}.png")
            local_page(a, b, earlier, current, regions[start:start + 2], path)
            files[f"locals-page-{start // 2 + 1:02d}"] = str(path)
        pairs.append({"earlier": earlier, "current": current,
                      "earlier_cel": cels[earlier]["cel"], "current_cel": cels[current]["cel"],
                      "earlier_exposures": cels[earlier]["source_exposures"],
                      "current_exposures": cels[current]["source_exposures"],
                      "files": files, "numeric_screen_not_approval": numeric_screen(a, b, regions),
                      "source_semantic_review": "pending", "alias_created": False})
    exposure_pages = []
    for start, end in WINDOWS:
        close = start >= 1200
        if close:
            for frame in range(start, end):
                exposure_pages.append({"frames": [frame], "path": hashes[str(frame)]["path"],
                                       "review": "pending"})
            continue
        roi = (600, 80, 1300, 1055)
        x0, y0, x1, y1 = roi
        w, h = x1 - x0, y1 - y0
        for page_start in range(start, end, 2):
            group = list(range(page_start, min(page_start + 2, end)))
            canvas = Image.new("RGB", (w * len(group), h + 32), "#242428")
            draw = ImageDraw.Draw(canvas)
            for col, frame in enumerate(group):
                draw.text((col * w + 8, 10), f"Original f{frame} / actual native", fill="white")
                canvas.paste(Image.fromarray(cv2.cvtColor(frames[frame][y0:y1, x0:x1], cv2.COLOR_BGR2RGB)),
                             (col * w, 32))
            path = OUT / f"exposure-native-f{group[0]:04d}-f{group[-1]:04d}.png"
            canvas.save(path)
            exposure_pages.append({"frames": group, "path": str(path), "review": "pending"})
    report = {"source": source_map["source"], "source_sha256": digest(Path(source_map["source"])),
              "source_map_sha256": digest(ROOT / "source_map.json"),
              "source_meta_sha256": digest(ROOT / "source_meta.json"),
              "sequential_decode": {"start": 0, "end_exclusive": max(required) + 1,
                                    "exact_checked_frame_count": len(hashes), "windows": WINDOWS},
              "all_saved_reference_exact": all(v["saved_reference_exact_bgr"] for v in hashes.values()),
              "frames": hashes, "pairs": pairs, "exposure_review_pages": exposure_pages,
              "shared_hashes_before": before,
              "shared_hashes_after": {name: digest(ROOT / name) for name in shared_names},
              "shared_files_changed_by_worker": False,
              "status": "private_evidence_pending_source_semantic_visual_review"}
    path = OUT / "source-evidence.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "checked_frames": len(hashes),
                      "all_saved_reference_exact": report["all_saved_reference_exact"],
                      "pair_count": len(pairs)}, indent=2))


if __name__ == "__main__":
    main()
