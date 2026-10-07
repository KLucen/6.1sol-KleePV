"""Native-pixel diagnostic crops of original/encoded hand and cuff regions."""

from pathlib import Path
import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
CROPS = {
    "f1172-lower-hand-cuff-native": (1172, (180, 560, 710, 1035)),
    "f1172-upper-hand-cuff-native": (1172, (1000, 20, 1400, 450)),
    "f1203-left-hand-cuff-native": (1203, (350, 480, 750, 920)),
    "f1203-right-hand-cuff-native": (1203, (1210, 470, 1630, 920)),
    "f1224-left-spread-glove-native": (1224, (100, 50, 550, 490)),
    "f1224-right-spread-glove-native": (1224, (1380, 40, 1920, 480)),
}

for name, (frame, (x0, y0, x1, y1)) in CROPS.items():
    comparison = cv2.imread(str(HERE / f"f{frame:04d}-encoded-comparison-whole.png"))
    source = comparison[y0:y1, x0:x1]
    encoded = comparison[y0:y1, x0 + 1920:x1 + 1920]
    width = x1 - x0
    canvas = np.full((y1 - y0 + 32, width * 2, 3), 248, np.uint8)
    cv2.putText(canvas, "ORIGINAL / ENCODED V1 / NATIVE PIXELS", (12, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (25, 25, 25), 1, cv2.LINE_AA)
    canvas[32:, :width] = source
    canvas[32:, width:] = encoded
    cv2.imwrite(str(HERE / f"{name}.png"), canvas)

print(f"Saved {len(CROPS)} native diagnostic crops")
