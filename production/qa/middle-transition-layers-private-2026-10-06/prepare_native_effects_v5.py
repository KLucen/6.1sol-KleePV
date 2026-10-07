"""Source / selected wholecel / composite native star-edge evidence."""

import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "v5-foreground-ownership-audit"


def main():
    timeline = json.loads((ROOT / "timeline-middle-2121-2145-oct6-draft-v1.json").read_text(encoding="utf-8"))
    rows, paths = [], []
    for exposure in timeline["output_exposures"]:
        frame = exposure["start"]
        asset = timeline["assets"][exposure["cel"]]
        source = cv2.imread(str(OUT / "source" / f"f{frame:04d}.png"))
        generated = cv2.resize(cv2.imread(str(ROOT / asset["path"])), (1920, 1080), interpolation=cv2.INTER_LANCZOS4)
        output = cv2.imread(str(OUT / f"f{frame:04d}-private.png"))
        b, g, r = cv2.split(source.astype(np.int16))
        yellow = ((r > 205) & (g > 185) & (b < 100)).astype(np.uint8)
        count, _, stats, _ = cv2.connectedComponentsWithStats(yellow, 8)
        for index in range(1, count):
            x, y, w, h, area = stats[index]
            if area < 10:
                continue
            cx, cy = x + w//2, y + h//2
            x0, y0 = min(max(cx-60, 0), 1800), min(max(cy-60, 0), 960)
            row = np.full((142, 360, 3), 248, np.uint8)
            cv2.putText(row, f"f{frame} FX {index} SOURCE / ART / COMPOSITE", (3, 15),
                        cv2.FONT_HERSHEY_SIMPLEX, .35, (25, 25, 25), 1, cv2.LINE_AA)
            for column, image in enumerate((source, generated, output)):
                row[22:, column*120:(column+1)*120] = image[y0:y0+120, x0:x0+120]
            rows.append(row)
    for index in range(0, len(rows), 8):
        path = OUT / f"effects-native-page-{index//8+1:02d}.png"
        if path.exists():
            raise FileExistsError(path)
        cv2.imwrite(str(path), np.concatenate(rows[index:index+8], axis=0))
        paths.append(str(path.relative_to(ROOT)))
    print(json.dumps({"native_effect_crops": len(rows), "pages": paths}))


if __name__ == "__main__":
    main()
