"""Private exact-source standing-cel evidence. No alias, map, or art mutation."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ROI = (600, 80, 1300, 1055)
REGIONS = [
    ("face-hat-eyelids", (845, 80, 1155, 365)),
    ("hair-collar", (830, 145, 1170, 445)),
    ("left-glove-cuff", (655, 390, 915, 625)),
    ("right-glove-cuff", (1020, 390, 1300, 650)),
    ("hem-pockets-seam", (825, 490, 1130, 720)),
    ("boots-caption-occlusion", (790, 925, 1150, 1055)),
]
PAIRS = [(1043, 1075), (1048, 1080), (1053, 1085), (1059, 1091),
         (1064, 1097), (1064, 1100), (1097, 1100), (1069, 1102),
         (1069, 1106), (1102, 1106)]
EXPOSURES = [(1043, 1075, 1080), (1048, 1080, 1085), (1053, 1085, 1091),
             (1059, 1091, 1097), (1064, 1097, 1100), (1064, 1100, 1102),
             (1069, 1102, 1106), (1069, 1106, 1113)]


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


def write_board(a, b, before, current, box, path):
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    canvas = Image.new("RGB", (width * 2, height * 2 + 64), "#242428")
    draw = ImageDraw.Draw(canvas)
    labels = [f"ORIGINAL f{before} / native", f"ORIGINAL f{current} / native",
              "Actual RGB difference x4", "Contours blue earlier / red current"]
    for idx, (panel, label) in enumerate(zip(panels(a, b), labels)):
        px, py = (idx % 2) * width, (idx // 2) * (height + 32)
        draw.text((px + 8, py + 10), label, fill="white")
        crop = panel[y0:y1, x0:x1]
        canvas.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)), (px, py + 32))
    canvas.save(path)


def write_locals(a, b, before, current, path):
    heights = [box[3] - box[1] + 32 for _, box in REGIONS]
    canvas = Image.new("RGB", (1440, sum(heights)), "#242428")
    draw = ImageDraw.Draw(canvas)
    all_panels = panels(a, b)
    row_y = 0
    for (name, (x0, y0, x1, y1)), height in zip(REGIONS, heights):
        labels = [f"f{before}", f"f{current}", "RGB difference x4", "dual contours"]
        for col, (panel, label) in enumerate(zip(all_panels, labels)):
            draw.text((col * 360 + 8, row_y + 10), f"{name} {label}", fill="white")
            crop = panel[y0:y1, x0:x1]
            canvas.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)),
                         (col * 360, row_y + 32))
        row_y += height
    canvas.save(path)


def outline_mask(image):
    # Diagnostic only: external dark-outline contours isolate the person from pale stars.
    dark = ((image.max(axis=2) < 100) * 255).astype(np.uint8)
    dark[:80] = 0
    dark[:, :600] = 0
    dark[:, 1300:] = 0
    dark[1055:] = 0
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(dark)
    for contour in contours:
        if cv2.contourArea(contour) > 150:
            cv2.drawContours(mask, [contour], -1, 255, cv2.FILLED)
    return mask != 0


def stats(a, b, masks=None):
    mask = (outline_mask(a) | outline_mask(b)) if masks is None else masks
    # Caption pixels are occluded; their outlines are examined in untouched boards.
    mask[950:1044, 680:1225] = False
    diff = cv2.absdiff(a, b).max(axis=2)
    binary = ((diff >= 28) & mask).astype(np.uint8)
    n, labels, components, _ = cv2.connectedComponentsWithStats(binary, 8)
    largest = int(components[1:, cv2.CC_STAT_AREA].max()) if n > 1 else 0
    components_rows = []
    for comp in components[1:]:
        x, y, w, h, area = map(int, comp)
        if area >= 8:
            components_rows.append({"box": [x, y, x + w, y + h], "area": area})
    components_rows.sort(key=lambda row: row["area"], reverse=True)
    return {"masked_mean_max_rgb_delta": float(diff[mask].mean()),
            "pixels_delta_28": int(binary.sum()), "largest_component": largest,
            "components_area_ge8": components_rows[:24],
            "mask_pixels": int(mask.sum()),
            "caveat": "Numbers screen only; captions occlude boots, untouched boards required."}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    shared_names = ["source_map.json", "source_aliases.json", "asset_selections.json",
                    "full-pv-progress-manifest.json"]
    shared_before = {name: digest(ROOT / name) for name in shared_names}
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    candidates = {row["frame"]: row for row in source_map["candidates"]}
    by_frame = {row["canonical_source_frame"]: row for row in manifest["cels"]}
    decoded = {}
    hashes = {}
    capture = cv2.VideoCapture(manifest["source"])
    for frame in range(1113):
        ok, bgr = capture.read()
        if not ok:
            raise ValueError(f"Source decode stopped at f{frame}")
        if frame < 1043:
            continue
        reference = ROOT / candidates[frame]["reference"]
        if not np.array_equal(bgr, cv2.imread(str(reference))):
            raise ValueError(f"Sequential source disagrees with saved reference f{frame}")
        path = OUT / f"f{frame:04d}-source-actual.png"
        cv2.imwrite(str(path), bgr)
        decoded[frame] = bgr
        hashes[str(frame)] = {"path": str(path), "png_sha256": digest(path),
                              "decoded_bgr_sha256": sha256(bgr.tobytes()).hexdigest(),
                              "saved_reference": str(reference), "saved_reference_sha256": digest(reference),
                              "saved_reference_exact_bgr": True, "pts": meta["pts"][frame]}
    capture.release()
    pair_rows = []
    for before, current in PAIRS:
        a, b = decoded[before], decoded[current]
        prefix = OUT / f"f{before:04d}-f{current:04d}"
        full = prefix.with_name(prefix.name + "-full-ab-rgb-contours.png")
        char = prefix.with_name(prefix.name + "-character-native-ab-rgb-contours.png")
        local = prefix.with_name(prefix.name + "-locals-native-ab-rgb-contours.png")
        write_board(a, b, before, current, (0, 0, 1920, 1080), full)
        write_board(a, b, before, current, ROI, char)
        write_locals(a, b, before, current, local)
        pair_rows.append({"before": before, "current": current,
                          "transform": {"kind": "identity", "matrix": [[1, 0, 0], [0, 1, 0]]},
                          "proof_full": str(full), "proof_character_native": str(char),
                          "proof_locals_native": str(local), "numeric_screen": stats(a, b),
                          "visual_disposition": "pending", "alias_created": False, "accepted": False})
    exposure_rows = []
    for anchor, start, end in EXPOSURES:
        metrics = []
        width, height = ROI[2] - ROI[0], ROI[3] - ROI[1]
        contact = Image.new("RGB", (width * (end - start), height + 32), "#242428")
        draw = ImageDraw.Draw(contact)
        for col, frame in enumerate(range(start, end)):
            draw.text((col * width + 8, 10), f"f{frame} actual native", fill="white")
            crop = decoded[frame][ROI[1]:ROI[3], ROI[0]:ROI[2]]
            contact.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)), (col * width, 32))
            metrics.append({"frame": frame, "anchor": anchor, "screen": stats(decoded[anchor], decoded[frame])})
        path = OUT / f"exposure-f{start:04d}-f{end - 1:04d}-all-native.png"
        contact.save(path)
        exposure_rows.append({"anchor_frame_candidate": anchor, "start": start, "end": end,
                              "pts": meta["pts"][start], "end_pts": meta["pts"][end],
                              "existing_manifest_row": by_frame[start] if start in by_frame else None,
                              "all_actual_native_contact": str(path), "per_frame_metrics": metrics,
                              "manual_visual_review": "pending"})
    report = {"source": manifest["source"], "source_sha256": digest(Path(manifest["source"])),
              "source_meta_sha256": digest(ROOT / "source_meta.json"),
              "sequential_decode": {"start": 0, "end_exclusive": 1113, "checked_frames": [1043, 1113]},
              "saved_reference_checks": hashes, "known_verified_repeat": [1043, 1075],
              "pairs": pair_rows, "exposure_candidates": exposure_rows,
              "shared_hashes_before": shared_before,
              "shared_hashes_after": {name: digest(ROOT / name) for name in shared_names},
              "artwork_generated": False, "source_holds_added": False, "alias_created": False,
              "accepted": False, "status": "private_numeric_evidence_pending_visual_review"}
    path = OUT / "exact-source-evidence.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "source_exact_checks": len(hashes),
                      "pairs": [{"before": row["before"], "current": row["current"],
                                 "screen": row["numeric_screen"]} for row in pair_rows]}, indent=2))


if __name__ == "__main__":
    main()
