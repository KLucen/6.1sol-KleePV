from pathlib import Path
import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
for frame in (1144, 1161, 3479, 3504):
    image = cv2.imread(str(HERE / "source" / f"f{frame:04d}.png"))
    b, g, r = cv2.split(image[959:989].astype(np.int16))
    mask = (b >= 194) & (g >= 216) & (r >= 230) & (r > b + 8) & (g > b + 5)
    columns = np.count_nonzero(mask, axis=0) > 1
    runs = []
    start = None
    for x in range(620, 1050):
        if columns[x] and start is None:
            start = x
        if not columns[x] and start is not None:
            runs.append((start, x, int(mask[:, start:x].sum())))
            start = None
    print(frame, runs)
    if frame in (1161, 3479, 3504):
        region = (850, 954, 1040, 992) if frame == 1161 else (650, 954, 820, 992)
        x0, y0, x1, y1 = region
        crop = image[y0:y1, x0:x1]
        cv2.imwrite(str(HERE / f"japanese-f{frame}-actual-4x.png"), cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST))
        print("pixel sample", frame, [(x, image[974, x].tolist()) for x in ((880,925,970,1010) if frame == 1161 else (674,714,754,795))])
