"""Audit six registered CN changes and preserve all earlier 29 star frames."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import compose as renderer
import star_gestures_layers


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label(image, text):
    band = np.full((27, image.shape[1], 3), 245, np.uint8)
    cv2.putText(band, text, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, .48, (20, 20, 20), 1, cv2.LINE_AA)
    return np.concatenate((band, image))


def main():
    cv2.setNumThreads(2)
    spec = importlib.util.spec_from_file_location("_old_star_before_six_v3", HERE / "star_gestures_layers-before-six-v3.py")
    before = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(before)
    before.ROOT = ROOT
    output_dir = HERE / "v3-raw"
    output_dir.mkdir(exist_ok=True)
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    timeline = json.loads((ROOT / "timeline-star-1008-1225-oct6-draft-v1.json").read_text(encoding="utf-8"))
    cap = cv2.VideoCapture(metadata["source"])
    records, rows, cache = [], [], {}
    for frame in range(1043):
        ok, source = cap.read()
        if not ok:
            raise RuntimeError(frame)
        if frame < 1008:
            continue
        span = next(entry for entry in timeline["output_exposures"] if entry["start"] <= frame < entry["end"])
        asset = timeline["assets"][span["cel"]]
        assert metadata["pts"][frame] == timeline["source_pts"][frame - 1008], frame
        if frame >= 1037:
            assert np.array_equal(source, cv2.imread(str(HERE / "source" / f"f{frame:04d}.png")))
        if asset["path"] not in cache:
            cache[asset["path"]] = renderer.read_image(ROOT / asset["path"])
        generated = cache[asset["path"]]
        reference = renderer.read_image(ROOT / asset["source_reference"])
        args = (source, reference, generated, span["source_matrix"], asset["source_frame"], Path(asset["path"]).name, frame)
        with patch.object(renderer, "restore_star_captions", before.restore_star_captions):
            prior, _, before_masks = renderer.compose(*args)
        current, _, masks = renderer.compose(*args)
        prior_frozen = cv2.imread(str(ROOT / "qa/oct6-star-extended-integration" / f"f{frame}-shared-raw.png"))
        assert np.array_equal(prior, prior_frozen), ("baseline-mismatch", frame)
        changed = np.any(current != prior, axis=2)
        owned = np.any(masks != 0, axis=2)
        outside = int(np.count_nonzero(np.any(current != source, axis=2) & ~owned))
        before_caption = np.all(before_masks == (245, 95, 180), axis=2)
        new_caption = np.all(masks == (245, 95, 180), axis=2)
        body = int(np.count_nonzero(changed & ~(before_caption | new_caption)))
        assert outside == body == 0, (frame, outside, body)
        assert not changed[:1002].any(), ("JP-or-body-changed", frame)
        if frame < 1037:
            assert not changed.any(), ("prior-phase-regression", frame)
        else:
            assert changed.any(), ("expected-CN-fix-missing", frame)
            path = output_dir / f"f{frame}-v3.png"
            cv2.imwrite(str(path), current)
            rows.append(label(np.concatenate([image[945:1047, 650:1250] for image in (source, prior, current)], axis=1),
                              f"f{frame} ORIGINAL | V2 OLD SIX | V3 COMPLETE CN; native 1:1"))
            cv2.imwrite(str(HERE / f"f{frame}-v3-whole.png"), current)
        records.append({"frame": frame, "original_pts": metadata["pts"][frame],
                        "changed_pixels": int(changed.sum()), "outside_ownership_errors": outside,
                        "body_vs_before_errors": body, "baseline_frozen_exact": True,
                        "japanese_unchanged": True, "earlier_phase_exact": frame < 1037,
                        "accepted": False})
        print(json.dumps({"frame": frame, "changed": int(changed.sum()), "outside": outside, "body": body}), flush=True)
    cap.release()
    page = HERE / "six-v3-source-before-after-caption-native.png"
    cv2.imwrite(str(page), np.concatenate(rows))
    current_layer = star_gestures_layers.caption_layer(2)
    with np.load(HERE / "old-phase2-layer-before-six-v3.npz") as old:
        assert np.array_equal(current_layer["region"], old["region"])
        for key in ("core", "extent", "alpha", "contrast_ring", "ink_rgb"):
            assert np.array_equal(current_layer[key][:48], old[key][:48]), key
    assert not current_layer["core"][48:].any()
    report = {"interval_checked": [1008, 1043], "frames": records, "raw_technical_pass": True,
              "changed_scope": [1037, 1043], "same_slot_registration": [0, 0],
              "prior_29_frames_exact": True, "native_page": str(page), "accepted": False,
              "native_visual_review": "pending actual viewing", "encoded_review": "not performed",
              "shared_helper_sha256": sha(ROOT / "star_gestures_layers.py"),
              "before_helper_sha256": sha(HERE / "star_gestures_layers-before-six-v3.py"),
              "unchanged_japanese_npz_sha256": sha(ROOT / "layers/star-caption-f3402-authorized-v1.npz"),
              "clear_original_cn_npz_sha256": sha(ROOT / "qa/caption-clear-v2-2026-10-06/long-f3402-cn-clear-real-caption-v2.npz")}
    (HERE / "six-v3-and-prior29-technical-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"frames": len(records), "technical_pass": True, "changed_frames": 6}))


if __name__ == "__main__":
    main()
