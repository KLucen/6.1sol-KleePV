"""Conservative observed-source prop restoration and opening geometry audit.

This module does not repair displaced hands or reconstruct hidden pillow pixels.
Only the explicitly recorded source-visible regions are eligible for restoration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
SIZE = (1920, 1080)
ASSETS = {
    0: "opening-f0000.png", 25: "opening-f0025.png",
    28: "opening-f0028.png", 31: "opening-f0031.png",
    38: "candidate-001-clean.png",
    **{f: f"fine-f{f:04d}.png" for f in
       (50, 54, 58, 63, 68, 75, 79, 83, 87, 91, 95, 99, 117)},
    121: "fine-f0121-costume-repair.png",
    **{f: f"fine-f{f:04d}.png" for f in (125, 129, 133, 157, 162, 167)},
}

# ROIs isolate the clock's purple display, not the pillow or the handle opening.
CLOCK_ROIS = {
    38: ((880, 457, 1045, 536), (880, 457, 1045, 536)),
    50: ((880, 457, 1045, 536), (880, 457, 1045, 536)),
    54: ((880, 457, 1045, 536), (880, 457, 1045, 536)),
    58: ((880, 457, 1045, 536), (880, 450, 1045, 536)),
    63: ((885, 490, 1020, 538), (885, 485, 1020, 538)),
    68: ((885, 490, 1020, 538), (885, 485, 1020, 538)),
    75: ((975, 317, 1088, 438), (980, 325, 1088, 445)),
    79: ((1212, 268, 1342, 341), (1215, 350, 1395, 427)),
    83: ((1230, 240, 1400, 327), (1215, 293, 1395, 357)),
    87: ((1310, 231, 1465, 325), (1220, 293, 1400, 357)),
    91: ((1310, 231, 1465, 325), (1220, 293, 1400, 357)),
    95: ((1310, 231, 1465, 325), (1220, 293, 1400, 357)),
    99: ((1310, 231, 1465, 325), (1220, 293, 1400, 357)),
    117: ((1310, 231, 1465, 325), (1220, 293, 1400, 357)),
    121: ((1000, 210, 1132, 313), (1008, 213, 1125, 313)),
    125: ((880, 340, 991, 476), (880, 341, 999, 475)),
    129: ((859, 475, 959, 599), (745, 451, 866, 589)),
    133: ((859, 467, 959, 599), (745, 451, 866, 589)),
    157: ((878, 470, 1000, 581), (702, 479, 824, 597)),
    162: ((878, 470, 1000, 581), (878, 470, 1000, 581)),
    167: ((878, 470, 1000, 581), (878, 470, 1000, 581)),
}

MEDIUM_PILLOW = [(1048, 283), (1100, 256), (1220, 209), (1467, 143),
                 (1508, 146), (1540, 239), (1573, 350), (1603, 412),
                 (1552, 429), (1183, 550), (1150, 574), (1110, 489),
                 (1070, 350)]
OPENING_PILLOW = [(289, 508), (389, 419), (530, 383), (1080, 218),
                  (988, 342), (908, 449), (835, 602), (715, 815),
                  (830, 945), (882, 1080), (478, 1080), (423, 968),
                  (375, 745), (324, 556)]
SAFE_FRINGES_MEDIUM = [
    [(1068, 287), (1097, 275), (1137, 424), (1120, 441), (1090, 365)],
    [(1516, 246), (1534, 272), (1564, 355), (1581, 389),
     (1560, 405), (1545, 354), (1525, 289)],
]
SAFE_FRINGES_OPENING = [
    [(309, 505), (383, 437), (481, 407), (513, 422), (521, 510),
     (549, 653), (589, 824), (664, 1046), (508, 1052),
     (465, 1010), (419, 823), (362, 609), (341, 542)],
]
FRONT_PILLOW_FRINGES = {
    162: [(1084, 232), (1094, 217), (1118, 222), (1132, 253),
          (1143, 329), (1153, 378), (1168, 431), (1180, 476),
          (1178, 489), (1158, 501), (1138, 493), (1124, 466),
          (1111, 405), (1096, 319), (1088, 275)],
    167: [(1123, 211), (1129, 203), (1145, 204), (1161, 215),
          (1179, 247), (1187, 311), (1200, 377), (1214, 429),
          (1216, 464), (1203, 481), (1188, 478), (1176, 465),
          (1172, 435), (1156, 387), (1147, 327), (1137, 280),
          (1127, 258)],
}
FRONT_ARM_POLYGONS = {
    162: [(1140, 318), (1190, 293), (1230, 322), (1285, 356),
          (1330, 414), (1440, 459), (1530, 490), (1530, 550),
          (1450, 590), (1320, 590), (1210, 500), (1170, 434),
          (1160, 374)],
    167: [(1180, 292), (1210, 267), (1260, 310), (1350, 403),
          (1450, 446), (1510, 481), (1500, 540), (1400, 552),
          (1300, 468), (1220, 410), (1170, 363)],
}


def read_image(path):
    value = cv2.imread(str(path))
    if value is None:
        raise ValueError(f"Cannot decode {path}")
    return cv2.resize(value, SIZE, interpolation=cv2.INTER_LANCZOS4)


def polygon_mask(points):
    mask = np.zeros((SIZE[1], SIZE[0]), np.uint8)
    cv2.fillPoly(mask, [np.asarray(points, np.int32)], 255)
    return mask


def observed_pillow_mask(source, frame):
    """Select source-visible material inside annotated prop regions."""
    hsv = cv2.cvtColor(source, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    opening = frame < 38
    if frame in FRONT_PILLOW_FRINGES:
        bounds = polygon_mask([(1080, 205), (1220, 208), (1448, 170),
                               (1510, 242), (1578, 414), (1270, 473),
                               (1140, 505), (1100, 415)])
        cool_material = (h >= 80) & (h <= 153) & (s >= 35) & (s <= 150) & (v < 228) & (v > 120)
        mask = (bounds != 0) & cool_material
        fringe = polygon_mask(FRONT_PILLOW_FRINGES[frame]) != 0
        # Exclude the source's old skin hand and cuff at the fringe contact.
        fringe[260:375, 1180:1275] = False
        mask |= fringe & (v > 155) & (s < 95)
        return mask.astype(np.uint8) * 255
    bounds = polygon_mask(OPENING_PILLOW if opening else MEDIUM_PILLOW)
    cool_material = (h >= 80) & (h <= 153) & (s >= 35) & (s <= 150) & (v < 228) & (v > 120)
    mask = (bounds != 0) & cool_material
    if not opening:
        # The original shoulder overlaps the lower-right pillow at this location.
        mask[470:, 1180:] = False
    for points in (SAFE_FRINGES_OPENING if opening else SAFE_FRINGES_MEDIUM) if frame < 121 else []:
        fringe = polygon_mask(points) != 0
        mask |= fringe & (v > 155) & (s < 95)
    return mask.astype(np.uint8) * 255


def generated_scene_mask(generated):
    """Eligible background colors, scoped later by observed source prop masks."""
    hsv = cv2.cvtColor(generated, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    return (h >= 80) & (h <= 155) & (s >= 20) & (s <= 165) & (v > 125)


def brown_glove_guard(generated, frame):
    guard = np.zeros((1080, 1920), np.uint8)
    if frame not in CLOCK_ROIS or frame <= 50:
        return guard
    hsv = cv2.cvtColor(generated, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    # Local semantic restriction prevents brown costume/shadow colors elsewhere.
    if frame <= 68:
        regions = [(945, 460, 1045, 620)]
    elif frame == 75:
        regions = [(1040, 337, 1170, 502)]
    elif frame == 79:
        regions = [(1190, 365, 1270, 497), (1370, 347, 1443, 470)]
    elif frame == 83:
        regions = [(1190, 310, 1268, 437), (1370, 299, 1445, 413)]
    elif frame == 121:
        regions = [(1010, 254, 1145, 395)]
    elif frame == 125:
        regions = [(890, 365, 1020, 508)]
    elif frame in (129, 133):
        regions = [(740, 490, 940, 632)]
    elif frame == 157:
        regions = [(850, 475, 980, 622)]
    elif frame in (162, 167):
        regions = [(1135, 255, 1275, 390)]
    else:
        regions = [(1200, 312, 1280, 430), (1370, 295, 1440, 407)]
    brown = (h < 27) & (s > 75) & (v > 80) & (v < 190)
    for x0, y0, x1, y1 in regions:
        guard[y0:y1, x0:x1] = brown[y0:y1, x0:x1].astype(np.uint8) * 255
    return cv2.dilate(guard, np.ones((5, 5), np.uint8))


def front_arm_guard(generated, frame):
    guard = np.zeros((1080, 1920), np.uint8)
    hsv = cv2.cvtColor(generated, cv2.COLOR_BGR2HSV)
    foreground = (hsv[:, :, 0] < 50) & (hsv[:, :, 2] > 25)
    if frame in FRONT_ARM_POLYGONS:
        guard = ((polygon_mask(FRONT_ARM_POLYGONS[frame]) != 0) & foreground).astype(np.uint8) * 255
    elif frame == 157:
        guard[460:630, 845:1030] = foreground[460:630, 845:1030].astype(np.uint8) * 255
    return cv2.dilate(guard, np.ones((5, 5), np.uint8))


def isolated_source_clock_mask(source):
    hsv = cv2.cvtColor(source, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    background = (h >= 119) & (h <= 131) & (s > 70) & (v > 215)
    bounded = np.zeros((1080, 1920), np.uint8)
    bounded[450:638, 850:1020] = (~background[450:638, 850:1020]).astype(np.uint8) * 255
    count, labels, stats, _ = cv2.connectedComponentsWithStats(bounded, 8)
    if count < 2:
        raise ValueError("Cannot isolate released source clock")
    label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    clock = (labels == label).astype(np.uint8) * 255
    contours, _ = cv2.findContours(clock, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(clock, contours, -1, 255, cv2.FILLED)
    return cv2.dilate(clock, np.ones((3, 3), np.uint8))


def original_property_masks(source, generated, frame):
    """Return safe source restoration and protected generated glove masks.

    This is deliberately a partial prop mask. Held clocks are never moved by it.
    Inputs must already use the same source canvas coordinates.
    """
    observed = observed_pillow_mask(source, frame)
    eligible = generated_scene_mask(generated)
    pillow = (observed != 0) & eligible
    hsv = cv2.cvtColor(generated, cv2.COLOR_BGR2HSV)
    strong_warm = (hsv[:, :, 0] < 45) & (hsv[:, :, 1] > 85)
    fringes = (SAFE_FRINGES_OPENING if frame < 38 else SAFE_FRINGES_MEDIUM) if frame < 121 else []
    for points in fringes:
        region = polygon_mask(points) != 0
        pillow |= region & (observed != 0) & ~strong_warm
    clock = np.zeros((1080, 1920), np.uint8)
    if frame in (38, 50, 54):
        # This source clock is wholly in front of empty background at these poses.
        clock[375:533, 854:1050] = 255
    clock_erase = np.zeros_like(clock)
    if frame in (157, 162, 167):
        clock[450:638, 854:1020] = 255
    if frame == 157:
        # Copy the source's genuinely empty background over the misplaced clock.
        clock_erase[450:642, 680:846] = 255
        # Its displaced new pillow enters the larger empty-background ROI.
        # Restore only the isolated original clock, not that surrounding rectangle.
        clock = isolated_source_clock_mask(source)
    arm = front_arm_guard(generated, frame)
    if frame in FRONT_PILLOW_FRINGES:
        front_fringe = (polygon_mask(FRONT_PILLOW_FRINGES[frame]) != 0) & (observed != 0)
        pillow |= front_fringe
    glove = brown_glove_guard(generated, frame)
    pillow[glove != 0] = False
    pillow[arm != 0] = False
    if frame == 75:
        # The raised prop and cream cuffs now cross the original left fringe.
        pillow[315:510, 978:1170] = False
    clock[glove != 0] = 0
    clock[arm != 0] = 0
    return {"pillow_observed": observed,
            "pillow_restore": pillow.astype(np.uint8) * 255,
            "clock_restore": clock, "clock_erase_restore": clock_erase,
            "glove_front": glove, "front_arm_guard": arm}


def restore_original_properties(output, source, generated, frame):
    """Post-compose exact source pixels in the explicitly safe prop regions."""
    masks = original_property_masks(source, generated, frame)
    restore = (masks["pillow_restore"] | masks["clock_restore"] | masks["clock_erase_restore"]) != 0
    result = output.copy()
    result[restore] = source[restore]
    return result, masks


def display_mask(image, roi):
    x0, y0, x1, y1 = roi
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    selected = np.zeros((1080, 1920), np.uint8)
    selected[y0:y1, x0:x1] = (((h[y0:y1, x0:x1] >= 130)
                            & (h[y0:y1, x0:x1] <= 155)
                            & (s[y0:y1, x0:x1] >= 25)
                            & (s[y0:y1, x0:x1] <= 110)
                            & (v[y0:y1, x0:x1] >= 140)
                            & (v[y0:y1, x0:x1] <= 255))
                            .astype(np.uint8) * 255)
    count, labels, stats, centers = cv2.connectedComponentsWithStats(selected, 8)
    if count < 2:
        raise ValueError(f"No display in ROI {roi}")
    component = np.zeros_like(selected)
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] >= 50:
            component[labels == label] = 255
    ys, xs = np.nonzero(component)
    if len(xs) < 200:
        raise ValueError(f"Too few coherent display pixels in ROI {roi}: {len(xs)}")
    hull = cv2.convexHull(np.column_stack((xs, ys)).astype(np.int32))
    filled = np.zeros_like(component)
    cv2.fillConvexPoly(filled, hull, 255)
    ys, xs = np.nonzero(filled)
    return filled, {"bbox": [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)],
                    "center": [float(xs.mean()), float(ys.mean())],
                    "pixels": int(len(xs))}


def colored_masks(masks):
    rgb = np.zeros((1080, 1920, 3), np.uint8)
    rgb[masks["pillow_observed"] != 0] = (60, 80, 120)
    rgb[masks["pillow_restore"] != 0] = (40, 180, 90)
    rgb[masks["clock_restore"] != 0] = (240, 180, 30)
    rgb[masks["clock_erase_restore"] != 0] = (230, 140, 50)
    rgb[masks["glove_front"] != 0] = (220, 70, 170)
    rgb[masks["front_arm_guard"] != 0] = (180, 80, 220)
    return rgb


def audit(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    candidates = {value["frame"]: value for value in source_map["candidates"]}
    rows = []
    manifest = {"version": 1, "canvas": [1920, 1080],
                "status": "partial_safe_source_regions_static_review",
                "layer_order": ["source_background_and_observed_pillow", "generated_character",
                                "source_clock_at_original_geometry", "generated_brown_fingers_and_cuffs",
                                "source_text_and_independent_effects"],
                "limits": ["Only already visible source pillow material is restored.",
                           "Pillow boundaries and disoccluded hidden source material need further work.",
                           "Held-clock geometry is diagnostic only; displaced hand poses need redraw.",
                           "The diagnostic uses generated images as the baseline, not the production renderer.",
                           "Clock metrics describe the visible display hull; changed finger occlusion can bias its center."],
                "assets": []}
    for frame, filename in ASSETS.items():
        source = read_image(ROOT / candidates[frame]["reference"])
        generated = read_image(ROOT / "generated" / filename)
        restored, masks = restore_original_properties(generated, source, generated, frame)
        restore = (masks["pillow_restore"] | masks["clock_restore"] | masks["clock_erase_restore"]) != 0
        changed_before = np.any(generated != source, axis=2) & restore
        changed_after = np.any(restored != source, axis=2) & restore
        changed = np.any(restored != generated, axis=2)
        entry = {"frame": frame, "source_reference": candidates[frame]["reference"],
                 "asset": f"generated/{filename}", "review": "partial_source_restore_diagnostic",
                 "restored_pixels": int(np.count_nonzero(restore)),
                 "source_mismatch_before": int(np.count_nonzero(changed_before)),
                 "source_mismatch_after": int(np.count_nonzero(changed_after)),
                 "outside_mask_pixels_changed": int(np.count_nonzero(changed & ~restore)),
                 "glove_overwritten_pixels": int(np.count_nonzero(changed & (masks["glove_front"] != 0))),
                 "front_arm_overwritten_pixels": int(np.count_nonzero(changed & (masks["front_arm_guard"] != 0))),
                 "clock_erase_restore_pixels": int(np.count_nonzero(masks["clock_erase_restore"])),
                 "generated_sha256": hashlib.sha256((ROOT / "generated" / filename).read_bytes()).hexdigest(),
                 "source_reference_sha256": hashlib.sha256((ROOT / candidates[frame]["reference"]).read_bytes()).hexdigest(),
                 "pillow_observed_pixels": int(np.count_nonzero(masks["pillow_observed"])),
                 "pillow_restore_pixels": int(np.count_nonzero(masks["pillow_restore"])),
                 "glove_guard_pixels": int(np.count_nonzero(masks["glove_front"]))}
        if frame in (162, 167):
            entry["layer_order"] = ["source_background", "Klee_body_and_rear_arm",
                                    "original_observed_front_pillow", "Klee_crossed_arm_cuff_and_visible_glove",
                                    "independent_original_clock", "source_captions_and_effects"]
        else:
            entry["layer_order"] = manifest["layer_order"]
        if frame in (129, 133):
            entry["geometry_status"] = "clock_and_pillow_displaced_pose_redraw_needed"
        elif frame == 157:
            entry["geometry_status"] = "wrong_clock_erased_but_released_hand_overlaps_original_clock_redraw_needed"
        else:
            entry["geometry_status"] = "partial_props_only_art_review_pending"
        if frame in CLOCK_ROIS:
            sm, sg = display_mask(source, CLOCK_ROIS[frame][0])
            gm, gg = display_mask(generated, CLOCK_ROIS[frame][1])
            delta = np.asarray(gg["center"]) - np.asarray(sg["center"])
            union = np.count_nonzero((sm != 0) | (gm != 0))
            entry["clock_display"] = {"source": sg, "generated": gg,
                                      "center_delta_xy": [round(float(v), 3) for v in delta],
                                      "center_distance": round(float(np.linalg.norm(delta)), 3),
                                      "overlap_iou": round(float(np.count_nonzero((sm != 0) & (gm != 0)) / union), 5),
                                      "restoration": ("full_source_clock" if frame in (38, 50, 54, 162, 167)
                                                      else "wrong_clock_erased_source_clock_partial_hand_overlap_pending" if frame == 157
                                                      else "blocked_pending_hand_geometry_review")}
            entry["clock_display"]["foreground_guard_overlap_source_display"] = int(np.count_nonzero(
                (sm != 0) & ((masks["glove_front"] | masks["front_arm_guard"]) != 0)))
            if frame == 157:
                erase = masks["clock_erase_restore"] != 0
                samples = source[erase]
                entry["clock_erase_source_background"] = {
                    "pixels": int(len(samples)),
                    "bgr_mean": [round(float(v), 3) for v in samples.mean(axis=0)],
                    "bgr_std": [round(float(v), 3) for v in samples.std(axis=0)],
                    "pixel_source_mismatch_after": int(np.count_nonzero(np.any(restored[erase] != samples, axis=1))),
                }
            contour_overlay = source.copy()
            for mask, color in ((sm, (20, 40, 250)), (gm, (250, 210, 20))):
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(contour_overlay, contours, -1, color, 3)
            cv2.imwrite(str(output_dir / f"f{frame:04d}-clock-contours.png"), contour_overlay)
        for name, mask in masks.items():
            path = output_dir / f"f{frame:04d}-{name}.png"
            cv2.imwrite(str(path), mask)
        diagnostic_path = output_dir / f"f{frame:04d}-safe-props-diagnostic.jpg"
        columns = []
        for image, label in ((source, "SOURCE"), (generated, "GENERATED"),
                             (restored, "PARTIAL SOURCE PROPS"), (colored_masks(masks), "MASKS")):
            small = cv2.resize(image, (768, 432), interpolation=cv2.INTER_AREA)
            tile = Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
            ImageDraw.Draw(tile).text((12, 10), label, fill="white", stroke_width=1, stroke_fill="black")
            columns.append(np.asarray(tile))
        Image.fromarray(np.concatenate(columns, axis=1)).save(diagnostic_path, quality=92)
        if frame == 157:
            for value, label in ((source, "source"), (restored, "restored")):
                crop = cv2.resize(value[445:640, 845:1070], (900, 780), interpolation=cv2.INTER_NEAREST)
                cv2.imwrite(str(output_dir / f"f0157-{label}-clock-crop.png"), crop)
        entry["diagnostic"] = str(diagnostic_path.relative_to(ROOT))
        entry["masks"] = {name: str((output_dir / f"f{frame:04d}-{name}.png").relative_to(ROOT)) for name in masks}
        manifest["assets"].append(entry)
        rows.append(entry)
    (output_dir / "opening-layer-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(output_dir / "opening-layer-manifest.json"),
                      "assets": len(rows), "pixel_copy_verified": all(r["source_mismatch_after"] == 0 for r in rows),
                      "clock_centers": [{"frame": r["frame"], **r["clock_display"]} for r in rows if "clock_display" in r]}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "qa" / "opening-layers")
    args = parser.parse_args()
    audit(args.output_dir)


if __name__ == "__main__":
    main()
