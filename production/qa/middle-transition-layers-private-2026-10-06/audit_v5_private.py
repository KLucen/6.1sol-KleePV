"""Freeze all 24 frames, independently check observed body cores and source FX."""

import json
from pathlib import Path
import shutil

import cv2
import numpy as np

import audit_private as audit
import middle_transition_layers_v5_private as layer

HERE = Path(__file__).resolve().parent
OUT = HERE / "v5-star-outline-complete"


def main():
    if OUT.exists():
        raise FileExistsError("Retain previous v5 evidence")
    OUT.mkdir()
    shutil.copytree(HERE / "source", OUT / "source")
    audit.HERE = OUT
    audit.layer = layer
    audit.main()
    timeline = json.loads(audit.TIMELINE.read_text(encoding="utf-8"))
    report_path = OUT / "private-24-frame-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    extra = []
    cache = {}
    for frame in range(2121, 2145):
        exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = timeline["assets"][exposure["cel"]]
        name = Path(asset["path"]).name
        if name not in cache:
            cache[name] = cv2.resize(cv2.imread(str(audit.ROOT / asset["path"])), (1920, 1080),
                                     interpolation=cv2.INTER_LANCZOS4)
        generated = cache[name]
        source = cv2.imread(str(OUT / "source" / f"f{frame:04d}.png"))
        output = cv2.imread(str(OUT / f"f{frame:04d}-private.png"))
        b, g, r = cv2.split(source.astype(np.int16))
        yellow = (r > 205) & (g > 185) & (b < 100) & (r > b + 100) & (g > b + 100)
        effects = cv2.dilate(yellow.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0
        record = {"frame": frame, "original_yellow_support_pixels": int(effects.sum()),
                  "original_yellow_support_rgb_mismatches": int(np.any(output != source, axis=2)[effects].sum())}
        if frame == 2135:
            gb, gg, gr = cv2.split(generated.astype(np.int16))
            roi = np.zeros((1080, 1920), bool)
            roi[130:935, 1030:1870] = True
            warm = roi & (gr > gg + 15) & (gr > gb + 12) & (gr > 150) & (gg > 75)
            core = cv2.erode(warm.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0
            record["observed_warm_head_pixels"] = int(warm.sum())
            record["observed_warm_head_rgb_mismatches_including_boundary"] = int(np.any(output != generated, axis=2)[warm].sum())
            record["observed_warm_head_core_pixels"] = int(core.sum())
            record["observed_warm_head_core_rgb_mismatches"] = int(np.any(output != generated, axis=2)[core].sum())
            probes = [(1160, 440), (1270, 605), (1470, 340), (1720, 510),
                      (1560, 900), (1380, 760), (1110, 535), (1650, 365)]
            probe_pixels = np.zeros((1080, 1920), bool)
            for x, y in probes:
                probe_pixels[y-5:y+6, x-5:x+6] = True
            record["observed_head_probe_pixels"] = int(probe_pixels.sum())
            record["observed_head_probe_rgb_mismatches"] = int(np.any(output != generated, axis=2)[probe_pixels].sum())
        extra.append(record)
    failures = [r for r in extra if r["original_yellow_support_rgb_mismatches"]
                or r.get("observed_warm_head_core_rgb_mismatches", 0)
                or r.get("observed_head_probe_rgb_mismatches", 0)]
    report["additional_independent_checks"] = extra
    report["additional_independent_failures"] = failures
    report["technical_oracle_pass"] &= not failures
    report["known_boundary_deviations"] = [
        {"frame": 2135, "pixels": [[1868, 228], [1869, 229]],
         "classification": "Two unselected subpixel edge pixels of the generated dark hat; not a face/hair core hole. Retained as draft boundary difference, not reported as exact whole-art RGB."}]
    report["body_oracle"] += " Independent warm-head core/ink probes and original yellow-star RGB checks added; boundary-inclusive discrepancies are reported separately, never erased to make an exact-art claim."
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"technical_oracle_pass": report["technical_oracle_pass"], "independent_failures": failures}), flush=True)


if __name__ == "__main__":
    main()
