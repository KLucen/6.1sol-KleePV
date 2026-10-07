"""Locate the actual post-compose old fringe and generated-sky seam."""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from night_transition_layers import _matte_and_sky, _sky_candidate

TARGET = ROOT / "qa" / "fast-fullpv-dance-backview-fragment-2026-10-04" / "fixed-v2"
ROI = (1125, 0, 1490, 285)


def bbox(mask):
    yy, xx = np.nonzero(mask)
    return [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1] if len(xx) else None


def samples(mask, source, generated, output):
    yy, xx = np.nonzero(mask)
    result = []
    for index in np.linspace(0, len(xx) - 1, min(8, len(xx))).astype(int):
        x, y = int(xx[index]), int(yy[index])
        result.append({"xy": [x, y], "source_bgr": source[y, x].tolist(),
                       "generated_bgr": generated[y, x].tolist(), "output_bgr": output[y, x].tolist()})
    return result


def main():
    global TARGET
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-scoped", action="store_true")
    args = parser.parse_args()
    if args.final_scoped:
        TARGET = TARGET.parent / "final-scoped"
    records = []
    for frame in (900, 901):
        source, generated, output = [cv2.imread(str(TARGET / f"f{frame:04d}-{name}-native.png"))
                                     for name in ("source", "generated", "composite")]
        area = np.zeros(source.shape[:2], bool)
        x0, y0, x1, y1 = ROI
        area[y0:y1, x0:x1] = True
        h, s, v = cv2.split(cv2.cvtColor(source, cv2.COLOR_BGR2HSV))
        fringe = (area & (h >= 40) & (h < 101) & (s > 90) & (v > 80)
                  & np.all(source == output, axis=2)
                  & (np.max(np.abs(source.astype(int) - generated.astype(int)), axis=2) > 8))
        old, _ = _matte_and_sky(source)
        sky_patch = (area & (old != 0) & _sky_candidate(generated)
                     & np.all(output == generated, axis=2))
        for name, mask in (("residual-source-green-aa", fringe), ("copied-generated-sky-in-vacated-old-hat", sky_patch)):
            cv2.imwrite(str(TARGET / f"f{frame:04d}-{name}-mask.png"), mask.astype(np.uint8) * 255)
        records.append({"frame": frame, "old_source_fringe_pixels": int(np.count_nonzero(fringe)),
                        "old_source_fringe_bounds_xyxy": bbox(fringe),
                        "old_source_fringe_samples": samples(fringe, source, generated, output),
                        "generated_sky_vacated_patch_pixels": int(np.count_nonzero(sky_patch)),
                        "generated_sky_vacated_patch_bounds_xyxy": bbox(sky_patch),
                        "generated_sky_patch_samples": samples(sky_patch, source, generated, output)})
        print(json.dumps(records[-1]), flush=True)
    (TARGET / "actual-v2-matte-residual-evidence.json").write_text(json.dumps({
        "roi_xyxy": ROI, "interpretation": ("Analytical remaining exact-source color coincidences; actual static scope review decides significance"
                                                 if args.final_scoped else "Static native residual old fringe and sky seam are blockers; core threshold zero alone is insufficient"),
        "records": records, "not_acceptance": True}, indent=2))


if __name__ == "__main__":
    main()
