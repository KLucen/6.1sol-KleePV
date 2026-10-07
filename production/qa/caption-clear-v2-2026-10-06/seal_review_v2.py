"""Seal technical evidence and the actual native review without art acceptance."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = HERE / "caption-v2-native-review-seal.json"
    if destination.exists():
        raise FileExistsError("Retain the actual review record")
    report = json.loads((HERE / "v2-182-frame-report.json").read_text(encoding="utf-8"))
    assert report["raw_technical_pass"]
    assert len(report["frames"]) == 182
    assert [entry["frame"] for entry in report["frames"]] == list(range(1043, 1225))
    assert all(entry["outside_ownership_errors"] == entry["body_vs_v1_errors"] == 0
               and entry["renderer_hook_exact"] and entry["japanese_unchanged"]
               for entry in report["frames"])
    assert all(entry["changed_pixels"] == 0 for entry in report["frames"] if entry["frame"] >= 1144)
    before = json.loads((HERE / "baseline-freeze.json").read_text(encoding="utf-8"))
    for path, expected in before.items():
        assert sha(HERE / path) == expected, path
    assert sha(ROOT / "star_extended_captions.py") == sha(HERE / "star_extended_captions-after-v2.py")
    assert sha(ROOT / "qa/oct6-star-extended-integration/short-f2420-clear-real-caption.npz") == before["short-f2420-before-v2.npz"]
    assert sha(ROOT / "layers/star-caption-f3402-authorized-v1.npz") == before["star-caption-f3402-before-v2.npz"]
    record = {
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "accepted": False,
        "changed_scope": [1043, 1144],
        "raw_technical_frames": 182,
        "source_pts": "Compared every frame to retained private timeline original PTS",
        "outside_ownership_errors": 0,
        "body_vs_v1_errors": 0,
        "all_81_frames_after_1143_exact_v1": True,
        "focused_tests": {"caption_v2": "4 passed", "registration_and_coverage": "12 passed"},
        "native_visual_review": {
            "actually_viewed": True,
            "frames": [1043, 1144],
            "all_101_cn_frames": True,
            "pages": [{"path": path, "sha256": sha(Path(path))} for path in report["native_cn_pages"]],
            "reference_crops": ["f3402-cn-native.png", "f1037-cn-native.png", "f3402-both-native.png", "f1037-both-native.png",
                                "v2-long-glyphs-native.png", "v2-cn-alpha-native.png", "f3402-cn-exact-donor.png"],
            "observations": ["Complete same-line Chinese is readable in all 101 native CN views; missing 人 stroke restored from the actual original donor.",
                             "Japanese and character artwork are unchanged.",
                             "Estimated donor AA differs slightly from current compressed original strokes; this was explicitly authorized."],
        },
        "single_contrast_experiment": {
            "radius": 4,
            "frames": [1129, 1144, 1154],
            "actually_viewed_native": True,
            "adopted": False,
            "decision": "Reject: the extra cream boot-clover shapes still camouflage 寂/分/う, while the thicker halo makes Chinese edges heavier. No further outline/threshold tuning.",
            "files": [f"f{frame}-single-4px-halo-proposal-native.png" for frame in (1129, 1144, 1154)],
        },
        "remaining_issues": [
            {"interval": [1129, 1144], "issue": "Japanese 寂 camouflages with cream boot clover; not visually passed."},
            {"interval": [1144, 1161], "issue": "Japanese 分/う camouflages with cream boot clovers; not visually passed."},
            {"interval": [1037, 1043], "issue": "Outside this shared helper; inherited incomplete Chinese glyph is not repaired by this scoped v2 update."},
        ],
        "encoded_review": "Not performed by this agent; chapter export and encoded review are separate root work.",
        "actual_speed_review": "Not performed by this agent.",
        "next_evidence_based_route": "Independent clean lyric underlay/ownership for same-color character badges; do not continue expanding halos.",
        "shared_helper_sha256": sha(ROOT / "star_extended_captions.py"),
        "layer_sha256": sha(HERE / "long-f3402-cn-clear-real-caption-v2.npz"),
        "technical_report_sha256": sha(HERE / "v2-182-frame-report.json"),
        "baseline_freeze_sha256": sha(HERE / "baseline-freeze.json"),
        "preserved_prior_artifacts": "Original helper snapshot, short layer, combined long data and Japanese donor NPZ frozen before edits. No old exports, selections, aliases or docs changed.",
    }
    destination.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"review_seal": str(destination), "sha256": sha(destination),
                      "raw_technical_frames": 182, "native_cn_frames": 101, "accepted": False}))


if __name__ == "__main__":
    main()
