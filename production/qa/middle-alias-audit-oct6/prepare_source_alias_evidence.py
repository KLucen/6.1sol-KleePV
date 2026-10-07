"""Private source-only diagnostics; never creates replacement character artwork."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "middle-next-2026-10-06"
BOXES = {
    "face-hat-hair": (885, 190, 1240, 595),
    "raised-fingers-cuff-sleeve": (650, 120, 910, 440),
    "extended-hand-cuff-hair": (1025, 445, 1305, 665),
    "torso-collar-pockets-hem": (775, 365, 1075, 725),
    "legs-boots": (685, 680, 1265, 1065),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def labeled(pixels, label):
    output = np.full((pixels.shape[0] + 24, pixels.shape[1], 3), 32, np.uint8)
    output[24:] = pixels
    cv2.putText(output, label, (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (235, 235, 235), 1)
    return output


def main():
    before_path = SOURCE / "f2115-source-actual.png"
    after_path = SOURCE / "f2121-source-actual.png"
    before = cv2.imread(str(before_path))
    after = cv2.imread(str(after_path))
    assert before.shape == after.shape == (1080, 1920, 3)
    evidence = []
    for name, box in BOXES.items():
        x0, y0, x1, y1 = box
        a = before[y0:y1, x0:x1]
        b = after[y0:y1, x0:x1]
        rgb = np.minimum(np.abs(a.astype(np.int16) - b.astype(np.int16)) * 4, 255).astype(np.uint8)
        ae = cv2.Canny(a, 80, 160) > 0
        be = cv2.Canny(b, 80, 160) > 0
        overlay = np.full(a.shape, 250, np.uint8)
        overlay[ae] = (255, 90, 30)
        overlay[be] = (30, 80, 255)
        overlay[ae & be] = (40, 40, 40)
        page = np.vstack((
            np.hstack((labeled(a, "f2115 BEFORE native"), labeled(b, "f2121 CURRENT native"))),
            np.hstack((labeled(rgb, "Actual RGB difference x4"), labeled(overlay, "BEFORE blue / CURRENT red"))),
        ))
        path = HERE / f"f2115-f2121-{name}-native-ab-rgb-contours.png"
        assert cv2.imwrite(str(path), page)
        evidence.append({"name": name, "source_box_xyxy": list(box), "path": str(path),
                         "dimensions": [page.shape[1], page.shape[0]], "sha256": digest(path)})
    report = {
        "scope": "f2115 to f2121 source-only alias diagnostic evidence; not artistic acceptance",
        "source_images": [{"frame": frame, "path": str(path), "sha256": digest(path)}
                          for frame, path in ((2115, before_path), (2121, after_path))],
        "target_exposure": {"start": 2121, "end": 2122, "frames": 1, "pts": 88.375, "end_pts": 88.417},
        "diagnostics": evidence,
        "drawing_modified": False,
        "alias_created": False,
        "accepted": False,
        "human_review": "pending actual viewing of these supplementary native evidence pages",
    }
    (HERE / "prepared-source-alias-evidence.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
