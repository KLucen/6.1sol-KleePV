"""Freeze bounded layer inputs and summarize actual cyan raw pixels."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compose import read_image
from cyan_caption_layers import cyan_caption_extent, cyan_caption_layer
from cyan_profile_layers import cyan_subject_mask

OUT = ROOT / "qa/fast-fullpv-cyan-layers-2026-10-04"


def main():
    cv2.setNumThreads(2)
    audit = json.loads((OUT / "raw-final-batch-audit.json").read_text(encoding="utf-8"))
    if len(audit["rows"]) != 97 or audit["missing_frames_no_placeholder"]:
        raise ValueError("Freeze requires all97 real raw compositions")
    files = ["compose.py", "cyan_profile_layers.py", "cyan_caption_layers.py",
             "night_transition_layers.py", "dance_caption_layers.py", "raised_caption_layers.py"]
    hashes = {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in files}
    rows = []
    for row in audit["rows"]:
        frame = row["source_frame"]
        source = cv2.imread(str(OUT / "actual-source" / f"f{frame:04d}.png"))
        actual = cv2.imread(row["composite"])
        path = Path(row["asset"])
        matte = cyan_subject_mask(read_image(path), frame, path.name)
        if not np.allclose(row["matrix"], [[1, 0, 0], [0, 1, 0]]):
            matte = cv2.warpAffine(matte, np.float32(row["matrix"]), (1920, 1080))
        h, s, v = cv2.split(cv2.cvtColor(source, cv2.COLOR_BGR2HSV))
        old_green_ink = (h >= 45) & (h <= 95) & (s >= 100) & (v < 210)
        inspect = old_green_ink & (matte == 0) & (cyan_caption_extent(frame) == 0)
        retained = inspect & np.all(actual == source, axis=2)
        rows.append({"source_frame": frame, "old_green_ink_outside_new_subject_checked": int(inspect.sum()),
                     "unchanged_old_green_ink_outside_new_subject": int(retained.sum())})
    freeze = {"scope": [911, 1008], "helper_sha256": hashes,
              "raw_audit_sha256": sha256((OUT / "raw-final-batch-audit.json").read_bytes()).hexdigest(),
              "source_origin_audit_sha256": sha256((OUT / "source-origin-verify.json").read_bytes()).hexdigest(),
              "all97_registered_current_source_glyph_core_rgb_exact": all(r["observed_source_glyph_rgb_exact"] for r in audit["rows"]),
              "all97_outside_registered_subject_and_caption_support_source_exact": all(r["outside_registered_subject_caption_support_changed"] == 0 for r in audit["rows"]),
              "old_green_ink_rows": rows,
              "all97_no_unchanged_old_green_ink_outside_new_subject": all(r["unchanged_old_green_ink_outside_new_subject"] == 0 for r in rows),
              "caption_donor_sha256": {str(phase): cyan_caption_layer(phase)["donor_sha256"] for phase in range(2)},
              "source_visible_pixels": "outside registered old/new anatomy and glyph support stay actual-source exact",
              "hidden_source_plate": "fit from current visible source sky; unobserved gradient and glyph antialias are reconstruction",
              "static_native_source_caption_pages_viewed": 13,
              "static_raw_native_caption_pages_viewed": "pending",
              "static_raw_canonical_body_pages_viewed": "pending",
              "original_speed_artistic_review": "pending", "artistic_acceptance": False}
    (OUT / "raw-layer-freeze.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    print(json.dumps({"helper_sha256": hashes,
                      "all97_glyph_core_rgb_exact": freeze["all97_registered_current_source_glyph_core_rgb_exact"],
                      "all97_outside_support_source_exact": freeze["all97_outside_registered_subject_and_caption_support_source_exact"],
                      "old_green_ink_remaining_frames": [r["source_frame"] for r in rows if r["unchanged_old_green_ink_outside_new_subject"]]}))


if __name__ == "__main__":
    main()
