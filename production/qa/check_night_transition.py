"""Actual sequential-source, native-size registered night matte evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import compose
from dance_caption_layers import restore_dance_captions
from night_transition_layers import REGISTERED, _matte_and_sky, night_subject_mask, restore_night_transition

TARGET = ROOT / "qa" / "fast-fullpv-dance-night-matte-2026-10-04"


def digest(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, nargs="+", default=list(range(902, 911)))
    args = parser.parse_args()
    cv2.setNumThreads(2)
    TARGET.mkdir(exist_ok=True)
    timeline = json.loads((ROOT / "timeline-dance-812-911-fast-draft-v10.json").read_text())
    cap = cv2.VideoCapture(timeline["source"])
    sources = {}
    for frame in range(max(args.frames) + 1):
        if frame in args.frames:
            ok, current = cap.read()
            if not ok:
                raise RuntimeError(f"Sequential decode failed at {frame}")
            sources[frame] = current
        elif not cap.grab():
            raise RuntimeError(f"Sequential decode failed at {frame}")
    cap.release()
    records = []
    for frame in args.frames:
        exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = timeline["assets"][exposure["cel"]]
        name = Path(asset["path"]).name
        source = sources[frame]
        generated = compose.read_image(ROOT / asset["path"])
        old = compose.subject_mask(source)
        generic_new = compose.subject_mask(generated)
        gate = compose.registered_night_transition
        compose.registered_night_transition = lambda *_: False
        try:
            before, _, _ = compose.compose(source, source, generated, exposure.get("source_matrix"),
                                            asset["source_frame"], name, frame)
        finally:
            compose.registered_night_transition = gate
        fixed, _, diagnostic = compose.compose(source, source, generated, exposure.get("source_matrix"),
                                               asset["source_frame"], name, frame)
        _, repair = restore_night_transition(before, source, generated, old, generic_new, frame, name)
        new = night_subject_mask(generated, frame, name)
        caption = np.all(diagnostic == (245, 95, 180), axis=2).astype(np.uint8) * 255
        source_matte, sky = _matte_and_sky(source)
        region = (source_matte != 0) | (new != 0)
        declared = (repair != 0) | (caption != 0)
        changed = np.any(fixed != before, axis=2)
        colors = np.zeros_like(source)
        colors[source_matte != 0] = (235, 100, 30)
        colors[new != 0] = (30, 160, 235)
        colors[(source_matte != 0) & (new != 0)] = (240, 235, 235)
        stem = f"f{frame:04d}"
        for suffix, image in (("source-native", source), ("generated-native", generated),
                              ("before-native", before), ("fixed-native", fixed),
                              ("matte", colors), ("repair-mask", repair),
                              ("source-sky", sky.astype(np.uint8) * 255)):
            cv2.imwrite(str(TARGET / f"{stem}-{suffix}.png"), image)
        panels = [cv2.resize(im, (768, 432), interpolation=cv2.INTER_AREA)
                  for im in (source, generated, before, fixed, colors)]
        cv2.imwrite(str(TARGET / f"{stem}-contact.jpg"), np.concatenate(panels, axis=1))
        records.append({"frame": frame, "asset": asset["path"], "range": REGISTERED[name],
                        "source_rgb_sha256": digest(source[:, :, ::-1]),
                        "generated_bgr_sha256": digest(generated),
                        "fixed_bgr_sha256": digest(fixed),
                        "new_matte_pixels": int(np.count_nonzero(new)),
                        "source_matte_pixels": int(np.count_nonzero(source_matte)),
                        "repair_pixels": int(np.count_nonzero(repair)),
                        "changed_pixels": int(np.count_nonzero(changed)),
                        "changed_outside_support": int(np.count_nonzero(changed & ~declared)),
                        "source_visible_background_preserved": bool(np.array_equal(
                            fixed[~declared], source[~declared])),
                        "inspection": "pending_actual_native_review"})
        print(json.dumps(records[-1]), flush=True)
    (TARGET / ("actual-native-evidence-" + "-".join(map(str, args.frames)) + ".json")).write_text(
        json.dumps({"source": timeline["source"], "sequential_decode": [0, max(args.frames)],
                    "timeline": "timeline-dance-812-911-fast-draft-v10.json",
                    "scope": [902, 911], "records": records,
                    "reconstruction": "Current-source visible sky robust smooth gradient, only vacated old support",
                    "not_a_cleanplate_donor": "Source1007 actually contains two huge people and different scene"}, indent=2))


if __name__ == "__main__":
    main()
