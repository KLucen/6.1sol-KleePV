"""Seal actual six-frame review and unchanged earlier star evidence."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = HERE / "six-v3-native-review-seal.json"
    if destination.exists():
        raise FileExistsError("Retain the actual six-frame review")
    report_path = HERE / "six-v3-and-prior29-technical-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    registration_path = HERE / "six-registration-before-edit.json"
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    assert report["raw_technical_pass"] and report["prior_29_frames_exact"]
    assert len(report["frames"]) == 35
    assert all(entry["outside_ownership_errors"] == entry["body_vs_before_errors"] == 0
               and entry["baseline_frozen_exact"] and entry["japanese_unchanged"] for entry in report["frames"])
    assert all(entry["changed_pixels"] == 0 for entry in report["frames"] if entry["frame"] < 1037)
    assert all(entry["relative_to_v2_cn_slot"] == [0, 0] for entry in registration["frames"])
    assert report["unchanged_japanese_npz_sha256"] == "a588071c0f94ff1697baf468cf9a7a8b13867d9cb5c36b8adc5318c13b7d09f6"
    assert sha(ROOT / "star_gestures_layers.py") == sha(HERE / "star_gestures_layers-after-six-v3.py")
    record = {
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "accepted": False,
        "changed_scope": [1037, 1043],
        "interval_checked": [1008, 1043],
        "raw_technical_frames": 35,
        "prior_29_frames_exact": True,
        "outside_ownership_errors": 0,
        "body_vs_before_errors": 0,
        "japanese_arrays_and_output_unchanged": True,
        "source_exposures_and_pts_unchanged": True,
        "same_clear_original_chinese": "深爱着 把寂寞两人各分一半",
        "registration": {"original_f3402_translation": [-15, 0], "relative_to_v2_cn_slot": [0, 0],
                         "all_six_sources_checked": True,
                         "best_dice_range": [.850910957146523, .8798604187437687],
                         "method": "Measured against clear left phrase, excluding original cream cuff; no scaling or guessed glyph strokes."},
        "native_review": {"actually_viewed": True, "all_six_caption_rows": True,
                          "source_and_current_page": "six-actual-source-and-current-cn-native.png",
                          "registration_overlay_page": "six-integer-registration-core-overlay-native.png",
                          "source_before_after_page": "six-v3-source-before-after-caption-native.png",
                          "whole_frames_viewed": [1037, 1042],
                          "observation": "Previously incomplete 人 is now complete and readable in all six native views; original-position phrase preserved. Character/JP are unchanged."},
        "tests": {"new_six_v3": "4 passed", "existing_old_star": "6 passed"},
        "shared_helper_sha256": sha(ROOT / "star_gestures_layers.py"),
        "before_helper_sha256": sha(HERE / "star_gestures_layers-before-six-v3.py"),
        "technical_report_sha256": sha(report_path),
        "registration_sha256": sha(registration_path),
        "unchanged_japanese_npz_sha256": report["unchanged_japanese_npz_sha256"],
        "clear_original_cn_npz_sha256": report["clear_original_cn_npz_sha256"],
        "rendering_policy": "Old-star contrast behavior left unchanged. No new halo experiment and no body redraw.",
        "encoded_review": "Not performed by this agent; old exports intentionally unchanged.",
        "actual_speed_review": "Not performed by this agent.",
        "remaining_issues": ["Japanese boot-clover camouflage at1129..1160 remains unaccepted, documented in v2 seal.",
                             "Old character boundary artifacts are retained baseline, not corrected or art-accepted by this caption-only work."],
        "preserved": "No shared selections, aliases, compose, docs, original Japanese NPZ or old exports changed.",
    }
    destination.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"seal": str(destination), "sha256": sha(destination),
                      "helper_sha256": record["shared_helper_sha256"], "accepted": False}))


if __name__ == "__main__":
    main()
