"""Enlarged diagnostic originals only; not character or lettering edits."""
from pathlib import Path
import cv2

HERE = Path(__file__).resolve().parent
for frame, box in ((2420, (824, 954, 1268, 992)), (1256, (796, 954, 1100, 992))):
    image = cv2.imread(str(HERE / "source" / f"f{frame:04d}.png"))
    x0, y0, x1, y1 = box
    cv2.imwrite(str(HERE / f"donor-f{frame}-japanese-diagnostic-4x.png"),
                cv2.resize(image[y0:y1, x0:x1], None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST))
