"""Find actually observed repeats of the target caption in one source decode."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

PRODUCTION = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
META = json.loads((PRODUCTION / "source_meta.json").read_text(encoding="utf-8"))
TARGET = cv2.imread(str(PRODUCTION / "source_refs/src-0569-f1037.png"))


def cream(image):
    b, g, r = cv2.split(image.astype(np.int16))
    return ((b > 170) & (g > 195) & (r > 210)
            & (r > b + 8) & (g > b + 5)).astype(np.uint8)


def sheet(rows, path):
    width = 1220
    height = 130
    canvas = np.full((height * len(rows), width, 3), 32, np.uint8)
    for i, row in enumerate(rows):
        title = f"f{row['frame']} ({row['frame']/24:.3f}s) match {row['score']:.4f} x={row['x']}"
        cv2.putText(canvas, title, (10, i*height+18), cv2.FONT_HERSHEY_SIMPLEX,
                    .45, (255, 255, 255), 1, cv2.LINE_AA)
        crop = cv2.imread(str(OUT / row["crop_path"]))
        canvas[i*height+25:i*height+25+crop.shape[0], :crop.shape[1]] = crop
    cv2.imwrite(str(path), canvas)


def main():
    template = cream(TARGET[959:989, 676:814]).astype(np.float32)
    cv2.imwrite(str(OUT / "target-clear-left-native.png"), TARGET[945:1047, 620:1240])
    capture = cv2.VideoCapture(META["source"])
    candidates = []
    sampled = []
    i = 0
    while True:
        ok, image = capture.read()
        if not ok:
            break
        if i % 12 == 0 or i == 1037:
            band = cream(image[959:989]).astype(np.float32)
            scores = cv2.matchTemplate(band, template, cv2.TM_CCOEFF_NORMED)
            _, score, _, location = cv2.minMaxLoc(scores)
            if score > .69:
                crop = image[945:1047, 350:1570]
                file = f"candidate-f{i}-native-caption.png"
                cv2.imwrite(str(OUT / file), crop)
                candidates.append({"frame": i, "pts": META["pts"][i],
                                   "score": score, "x": location[0],
                                   "crop_path": file,
                                   "source_bgr_sha256": hashlib.sha256(image.tobytes()).hexdigest()})
                cv2.imwrite(str(OUT / f"candidate-f{i}-source.png"), image)
            if i % 48 == 0:
                file = f"sample-f{i}-native-caption.png"
                cv2.imwrite(str(OUT / file), image[945:1047, 350:1570])
                sampled.append({"frame": i, "score": score,
                                "x": location[0], "crop_path": file})
        i += 1
    capture.release()
    record = {"source": META["source"], "source_sha256": META["sha256"],
              "decoded_frames": i, "scan_stride": 12,
              "target_frame": 1037, "target_region": [676,959,814,989],
              "candidate_threshold_only": .69, "candidates": candidates,
              "warning": "Template score is candidate selection only, not donor approval."}
    (OUT / "source-repeat-candidates.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    for n, start in enumerate(range(0, len(candidates), 8), 1):
        sheet(candidates[start:start+8], OUT / f"candidate-native-page-{n:02d}.png")
    for n, start in enumerate(range(0, len(sampled), 8), 1):
        sheet(sampled[start:start+8], OUT / f"whole-pv-native-caption-page-{n:02d}.png")
    print(json.dumps({"decoded_frames": i, "candidates": len(candidates),
                      "frames": [r["frame"] for r in candidates]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
