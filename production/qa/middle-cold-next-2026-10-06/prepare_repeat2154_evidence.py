"""Supplementary native original-cel diagnostics, never replacement art."""
import json
from pathlib import Path
import cv2
from worker import digest, local_page

here = Path(__file__).resolve().parent
a = cv2.imread(str(here / "f2152-source-actual.png"))
b = cv2.imread(str(here / "f2154-source-actual.png"))
boxes = {
    "cold-hat-brim": (580, 0, 1510, 350),
    "cold-rear-hair-tip": (360, 270, 1080, 950),
    "cold-collar-shoulder": (900, 700, 1270, 1080),
    "warm-lower-hair-fragment": (0, 620, 410, 1080),
}
records = []
for name, (x0, y0, x1, y1) in boxes.items():
    path = here / f"f2152-f2154-{name}-native-ab-rgb-contours.png"
    assert not path.exists()
    local_page(a[y0:y1, x0:x1], b[y0:y1, x0:x1], name, 2152, 2154, path)
    records.append({"path": str(path), "box_xyxy": [x0, y0, x1, y1], "sha256": digest(path)})
(here / "repeat2154-supplementary-evidence.json").write_text(json.dumps({"diagnostics": records,
    "drawing_modified": False, "alias_created": False, "accepted": False}, indent=2) + "\n", encoding="utf-8")
print(json.dumps(records, indent=2))
