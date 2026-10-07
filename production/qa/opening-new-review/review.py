"""Bounded static diagnostics; no production assets or acceptance states are edited."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT))
from opening_layers import read_image

ASSETS = {
    129: "fine-f0129-geometry-repair.png",
    133: "fine-f0133-geometry-repair.png",
    157: "fine-f0157-glove-repair.png",
    **{f: f"fine-f{f:04d}.png" for f in (162, 167, 172, 176, 180, 185, 190, 194)},
    176: "fine-f0176-hair-cuff-repair.png",
}
SEQUENCE = (172, 176, 180, 185, 190, 194)
ROIS = {129: (850, 460, 965, 608), 133: (850, 460, 965, 608)}
FLOATING_ROI = (870, 465, 1006, 585)


def display_mask(image, roi):
    # Only the largest purple component is the display; aggregating every purple
    # component incorrectly expands the source hull to include the clock handle.
    x0, y0, x1, y1 = roi
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    mask = np.zeros((1080, 1920), np.uint8)
    mask[y0:y1, x0:x1] = (((h[y0:y1,x0:x1] >= 130) & (h[y0:y1,x0:x1] <= 155)
                         & (s[y0:y1,x0:x1] >= 25) & (s[y0:y1,x0:x1] <= 110)
                         & (v[y0:y1,x0:x1] >= 140)).astype(np.uint8) * 255)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if count < 2:
        raise ValueError("No purple display")
    label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    ys, xs = np.nonzero(labels == label)
    hull = cv2.convexHull(np.column_stack((xs, ys)).astype(np.int32))
    filled = np.zeros_like(mask)
    cv2.fillConvexPoly(filled, hull, 255)
    ys, xs = np.nonzero(filled)
    return filled, {"bbox": [int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)],
                    "center": [float(xs.mean()), float(ys.mean())], "pixels": int(len(xs))}


def localized_delta(parent_path, repair_path, rois, name):
    parent, repaired = read_image(parent_path), read_image(repair_path)
    allowed = np.zeros((1080, 1920), bool)
    for x0,y0,x1,y1 in rois:
        allowed[y0:y1,x0:x1] = True
    delta = np.max(np.abs(parent.astype(np.int16)-repaired.astype(np.int16)), axis=2)
    changed = delta > 8
    heat = np.zeros_like(parent)
    heat[:, :, 2] = np.minimum(delta * 4, 255).astype(np.uint8)
    heat[allowed, 1] = np.maximum(heat[allowed, 1], 50)
    cv2.imwrite(str(OUT / f"{name}-difference-x4.png"), heat)
    return {"parent": str(parent_path.relative_to(ROOT)), "repair": str(repair_path.relative_to(ROOT)),
            "manual_edit_rois": [list(r) for r in rois], "channel_difference_threshold": 8,
            "inside_roi_changed_pixels": int(np.count_nonzero(changed & allowed)),
            "outside_roi_changed_pixels": int(np.count_nonzero(changed & ~allowed)),
            "outside_mean_abs_channel_delta": round(float(np.abs(parent.astype(np.int16)-repaired.astype(np.int16))[~allowed].mean()), 5),
            "outside_max_channel_delta": int(delta[~allowed].max()),
            "pixel_locked": False, "heatmap": f"qa/opening-new-review/{name}-difference-x4.png"}


def labeled(image, label, size=(768, 432)):
    small = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
    value = Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
    ImageDraw.Draw(value).text((10, 10), label, fill="white", stroke_fill="black", stroke_width=2)
    return value


def clock_component(image, roi=(850, 450, 1030, 638)):
    x0, y0, x1, y1 = roi
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    background = (h >= 119) & (h <= 131) & (s > 70) & (v > 215)
    mask = np.zeros((1080, 1920), np.uint8)
    mask[y0:y1, x0:x1] = (~background[y0:y1, x0:x1]).astype(np.uint8) * 255
    count, labels, stats, centers = cv2.connectedComponentsWithStats(mask, 8)
    parts = []
    for i in range(1, count):
        x, y, w, h, n = stats[i]
        if n > 70:
            parts.append({"bbox": [int(x), int(y), int(x+w), int(y+h)], "pixels": int(n),
                          "center": [float(q) for q in centers[i]]})
    return sorted(parts, key=lambda p: p["pixels"], reverse=True)


def review():
    OUT.mkdir(parents=True, exist_ok=True)
    mapping = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    candidates = {c["frame"]: c for c in mapping["candidates"]}
    manifest = {"version": 1, "canvas": [1920, 1080],
                "review_scope": "single-frame and adjacent static inspection only",
                "acceptance": "no artistic or actual-speed acceptance granted", "assets": []}
    sources, generated = {}, {}
    for frame, filename in ASSETS.items():
        path = ROOT / "generated" / filename
        if not path.exists():
            manifest["assets"].append({"frame": frame, "asset": str(path), "status": "not_yet_saved"})
            continue
        src = read_image(ROOT / candidates[frame]["reference"])
        gen = read_image(path)
        sources[frame], generated[frame] = src, gen
        roi = ROIS.get(frame, FLOATING_ROI)
        sm, s = display_mask(src, roi)
        gm, g = display_mask(gen, roi)
        delta = np.asarray(g["center"]) - np.asarray(s["center"])
        union = np.count_nonzero((sm != 0) | (gm != 0))
        overlap = np.count_nonzero((sm != 0) & (gm != 0))
        entry = {"frame": frame, "asset": f"generated/{filename}",
                 "asset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                 "source": candidates[frame]["reference"], "display_roi": list(roi),
                 "source_display": s, "generated_display": g,
                 "display_delta_xy": [round(float(q), 3) for q in delta],
                 "display_distance": round(float(np.linalg.norm(delta)), 3),
                 "display_iou": round(float(overlap/union), 5),
                 "clock_source_components": clock_component(src),
                 "clock_generated_components": clock_component(gen)}
        if frame >= 157:
            entry["proposed_copy_rectangle"] = [866, 464, 1018, 624]
            entry["rectangle_supported"] = frame != 157
            entry["rectangle_scope"] = "same asset source frame, identity source canvas only"
            entry["rectangle_reason"] = (
                "Released open hand enters upper-right corner of full clock bounding rectangle; use a clock silhouette mask, not whole rectangle."
                if frame == 157 else
                "Clock is isolated from source and generated hands/character; source and generated full clock fall within rectangle.")
        overlay = src.copy()
        for mask, color in ((sm, (255, 150, 30)), (gm, (30, 40, 255))):
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, contours, -1, color, 3)
        cv2.rectangle(overlay, (roi[0], roi[1]), (roi[2], roi[3]), (40, 255, 40), 1)
        crop = overlay[440:650, 830:1050]
        Image.fromarray(cv2.cvtColor(cv2.resize(crop, (880, 840), interpolation=cv2.INTER_NEAREST), cv2.COLOR_BGR2RGB)).save(OUT / f"f{frame:04d}-display-contours.png")
        pair = Image.new("RGB", (1536, 432))
        pair.paste(labeled(src, f"f{frame:04d} SOURCE"), (0, 0))
        pair.paste(labeled(gen, f"f{frame:04d} GENERATED DRAFT"), (768, 0))
        pair.save(OUT / f"f{frame:04d}-source-generated.jpg", quality=94)
        if frame >= 157:
            three = Image.new("RGB", (1440, 640))
            for index, (value, label) in enumerate(((src, "SOURCE"), (gen, "GENERATED"))):
                focused = value[450:642, 850:1066]
                three.paste(labeled(focused, label, (720, 640)), (index*720, 0))
            three.save(OUT / f"f{frame:04d}-clock-and-nearest-hand.jpg", quality=96)
        manifest["assets"].append(entry)
    for values, label in ((sources, "SOURCE"), (generated, "GENERATED DRAFT")):
        contact = Image.new("RGB", (1296, 1208))
        for i, frame in enumerate(SEQUENCE):
            focused = values[frame][85:1080, 1020:1760]
            contact.paste(labeled(focused, f"f{frame:04d} {label}", (432, 604)), ((i % 3)*432, (i//3)*604))
        contact.save(OUT / f"sequence-{label.split()[0].lower()}.jpg", quality=96)
    manifest["glove_repair_comparison"] = localized_delta(
        ROOT / "generated/fine-f0157-geometry-repair.png", ROOT / "generated/fine-f0157-glove-repair.png",
        ((985,450,1078,570), (1625,345,1772,438)), "f0157-glove-repair")
    manifest["hair_cuff_repair_comparison"] = localized_delta(
        ROOT / "generated/fine-f0176.png", ROOT / "generated/fine-f0176-hair-cuff-repair.png",
        ((1370,375,1475,512), (1542,482,1672,591)), "f0176-hair-cuff-repair")
    hsv = cv2.cvtColor(sources[162], cv2.COLOR_BGR2HSV)
    h,s,v = cv2.split(hsv)
    foreground = ~((h >= 119) & (h <= 131) & (s > 70) & (v > 215))
    bounded = np.zeros((1080,1920), np.uint8)
    bounded[464:624,866:1018] = foreground[464:624,866:1018].astype(np.uint8)*255
    count, labels, stats, _ = cv2.connectedComponentsWithStats(bounded, 8)
    label = 1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
    clock = (labels == label).astype(np.uint8)*255
    contours, _ = cv2.findContours(clock, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(clock, contours, -1, 255, cv2.FILLED)
    clock = cv2.dilate(clock,np.ones((3,3),np.uint8))
    cv2.imwrite(str(OUT / "f0157-clock-mask-from-source-f0162.png"),clock)
    hsv_gen = cv2.cvtColor(generated[157],cv2.COLOR_BGR2HSV)
    h,s,v = cv2.split(hsv_gen)
    brown = (h < 27) & (s > 75) & (v > 80) & (v < 190)
    glove = np.zeros(clock.shape,np.uint8)
    glove[450:570,985:1080] = brown[450:570,985:1080].astype(np.uint8)*255
    raw_overlap = int(np.count_nonzero((clock != 0) & (glove != 0)))
    glove = cv2.dilate(glove,np.ones((5,5),np.uint8))
    guarded = clock.copy()
    guarded[glove != 0] = 0
    cv2.imwrite(str(OUT / "f0157-clock-mask-glove-guarded.png"),guarded)
    copied = generated[157].copy()
    copied[guarded != 0] = sources[157][guarded != 0]
    cv2.imwrite(str(OUT / "f0157-source-clock-copy-diagnostic.png"),copied)
    manifest["released_clock_mask_recommendation"] = {
        "mask": "qa/opening-new-review/f0157-clock-mask-from-source-f0162.png",
        "asset_specific_guarded_mask": "qa/opening-new-review/f0157-clock-mask-glove-guarded.png",
        "raw_mask_overlap_with_brown_glove_pixels": raw_overlap,
        "guarded_mask_overlap_with_glove_guard_pixels": int(np.count_nonzero((guarded != 0) & (glove != 0))),
        "geometry_reference_frame": 162, "pixels_to_copy_reference_frame": 157,
        "basis": "Same stationary source clock drawing verified in full-resolution source frames; mask excludes open hand.",
        "limits": "Mask is for source-frame identity geometry only; generated glove guard and composed boundary check remain required."}
    (OUT / "metrics.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"assets": len(manifest["assets"]),
                      "display_metrics": [{k: e[k] for k in ("frame", "display_delta_xy", "display_distance", "display_iou")} for e in manifest["assets"] if "display_delta_xy" in e],
                      "glove_repair_comparison": manifest["glove_repair_comparison"],
                      "hair_cuff_repair_comparison": manifest["hair_cuff_repair_comparison"]}, indent=2))


if __name__ == "__main__":
    review()
