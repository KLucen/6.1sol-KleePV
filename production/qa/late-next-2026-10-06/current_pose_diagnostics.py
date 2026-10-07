"""Current-source crops only; never produces replacement artwork."""

import cv2
from pathlib import Path

HERE = Path(__file__).resolve().parent
for frame in [2926, 2932, 2938]:
    image = cv2.imread(str(HERE / f"f{frame}-source-actual.png"))
    cv2.imwrite(str(HERE / f"f{frame}-source-current-face-native.png"), image[170:420, 1200:1530])
    cv2.imwrite(str(HERE / f"f{frame}-source-wide-pose-native.png"), image[170:940, 1140:1700])
    cv2.imwrite(str(HERE / f"f{frame}-source-far-grip-native.png"), image[245:500, 1480:1700])
