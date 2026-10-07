"""Measure a draft repair; masks and crops are QA references, not artwork."""
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
BEFORE = ROOT / "generated/root-continuation-f0839-v1.png"
AFTER = ROOT / "generated/root-continuation-f0839-gloves-v2.png"
SIZE = (1920, 1080)
BOXES = [(330, 395, 460, 510), (1090, 345, 1210, 455)]
HAND_POLYGONS = [
    [(350, 425), (437, 433), (452, 486), (395, 485), (350, 455)],
    [(1117, 351), (1195, 351), (1195, 454), (1131, 454),
     (1135, 438), (1134, 422), (1128, 404), (1122, 390)],
]


def main():
    originals = [Image.open(path).convert("RGB") for path in (BEFORE, AFTER)]
    images = [im.resize(SIZE, Image.Resampling.LANCZOS) for im in originals]
    arrays = [np.asarray(im).astype(np.int16) for im in images]
    delta = np.max(np.abs(arrays[0] - arrays[1]), axis=2)
    changed = delta > 28
    requested_mask = np.zeros((SIZE[1], SIZE[0]), dtype=bool)
    for x0, y0, x1, y1 in BOXES:
        requested_mask[y0:y1, x0:x1] = True

    # The inspected hand masks follow the diagonal/curved wrist seam to avoid
    # including cream sleeve cuffs; bounds are approximate visual QA regions.
    hand_mask_image = Image.new("L", SIZE, 0)
    hand_mask_draw = ImageDraw.Draw(hand_mask_image)
    for polygon in HAND_POLYGONS:
        hand_mask_draw.polygon(polygon, fill=255)
    hand_mask = np.asarray(hand_mask_image) != 0
    annotated = images[1].copy()
    annotation = ImageDraw.Draw(annotated)
    for polygon in HAND_POLYGONS:
        annotation.line(polygon + [polygon[0]], fill=(0, 255, 0), width=2)
    crops = [(330, 395, 500, 535), (1070, 325, 1230, 490)]
    contact = Image.new("RGB", (1440, 600), "#242426")
    draw = ImageDraw.Draw(contact)
    panels = [images[0], annotated, Image.fromarray(np.minimum(delta * 4, 255).astype(np.uint8)).convert("RGB")]
    for row, box in enumerate(crops):
        for col, (panel, label) in enumerate(zip(panels, ["BEFORE", "AFTER", "MAX RGB DELTA x4"])):
            crop = panel.crop(box)
            crop.thumbnail((450, 260))
            x, y = col * 480, row * 300
            draw.text((x + 10, y + 8), label + " " + str(box), fill="white")
            contact.paste(crop, (x + 10, y + 35))
    crop_path = QA / "f0839-glove-repair-tight-crops.png"
    contact.save(crop_path)
    report = {
        "before": str(BEFORE),
        "after": str(AFTER),
        "before_sha256": sha256(BEFORE.read_bytes()).hexdigest(),
        "after_sha256": sha256(AFTER.read_bytes()).hexdigest(),
        "original_sizes": [list(im.size) for im in originals],
        "normalized_size": list(SIZE),
        "normalization": "PIL RGB, same 1920x1080 target, LANCZOS",
        "changed_definition": "maximum absolute RGB channel difference > 28",
        "total_pixels": int(changed.size),
        "changed_pixels_total": int(np.count_nonzero(changed)),
        "requested_rectangles_xyxy_exclusive": BOXES,
        "requested_roi_union_pixels": int(np.count_nonzero(requested_mask)),
        "changed_inside_requested_roi_union": int(np.count_nonzero(changed & requested_mask)),
        "changed_outside_requested_roi_union": int(np.count_nonzero(changed & ~requested_mask)),
        "inspected_hand_polygons_xy": HAND_POLYGONS,
        "inspected_hand_roi_union_pixels": int(np.count_nonzero(hand_mask)),
        "changed_inside_inspected_hand_roi_union": int(np.count_nonzero(changed & hand_mask)),
        "changed_outside_inspected_hand_roi_union": int(np.count_nonzero(changed & ~hand_mask)),
        "hand_roi_review": "Visually inspected original images and normalized tight crops; polygon wrist edges exclude cream cuffs, face, torso and legs. Manual QA bounds are approximate, not a production matte.",
        "tight_crop_evidence": str(crop_path),
        "artistically_accepted": False,
        "limitations": [
            "Requested broad rectangles may include small parts of diagonal cuffs.",
            "A local color repair is not pixel-locked outside the hands.",
            "These are normalized draft image diagnostics, not source pose acceptance or video playback review."
        ],
    }
    path = QA / "f0839-glove-repair-drift.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
