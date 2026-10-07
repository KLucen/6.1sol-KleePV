"""Freeze the two reviewed source aliases as a post-render extension."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
EXPECTED = {
    "source_map.json": "05de0751535d1c627171b81f41a0183bf3990b902d44435bfc8b3120a30caf76",
    "asset_selections.json": "ed7186f751a4c625219987085743fa31ec8e73ed88a281da453110e235088a55",
    "compose.py": "accdc5260867891caba73b9cbff3b3047c6c2f806157c1318d3d49214bf98181",
    "timeline-cyan-911-1008-fast-draft-v1.json": "3efab00f86b92e6fbf80eb24c606b40041f3fd052500f10b5874f5ae176f0453",
    "qa/standing-repeat-audit-2026-10-05/exact-source-evidence.json": "59987c1bc52ad3a4fe0ad0a631a80d626efedd06ec4af4645b50dba729a8e883",
    "qa/standing-missing-2026-10-05/oct5-full-7call-promptset.json": "1e6372e9e88024bfac931dc462b0f7f5993e7a823b80236b5ca2b6346e814608",
    "qa/fast-fullpv-batch2-integrity-2026-10-04/batch2-full-27call-promptset.json": "173f36b5ee4b9fd280b91db09db77c845789ddd5f39a67f58fb9675ae6eef32a",
    "output/klee-cyan-911-1008-fast-draft-v1.mp4": "d6fc2c5829ad263403af221669a2d28890cc52900963bf1f1ffd2cad8c887386",
    "output/klee-cyan-911-1008-comparison-fast-draft-v1.mp4": "7b6a51b6db42306075ffb122d37c4926f886918306853dce06223995a6c1b0a2",
    "qa/fast-fullpv-batch2-final-integrity-2026-10-05/final-integrity-audit.json": "a963453a0fe5cdaa9ce01fd76057d82fc1ec940f75b82918d8e17b1e73f224e3",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    report_path = OUT / "root-reviewed-alias-extension.json"
    snapshot_paths = [OUT / "source-aliases-post-review-snapshot.json",
                      OUT / "progress-post-review-snapshot.json"]
    if any(path.exists() for path in [report_path, *snapshot_paths]):
        raise FileExistsError("The frozen alias extension already exists; do not overwrite it.")
    unchanged = {}
    for name, expected in EXPECTED.items():
        actual = digest(ROOT / name)
        assert actual == expected, name
        unchanged[name] = actual
    source_map = read(ROOT / "source_map.json")
    source_meta = read(ROOT / "source_meta.json")
    aliases = read(ROOT / "source_aliases.json")
    manifest = read(ROOT / "full-pv-progress-manifest.json")
    evidence = read(OUT / "exact-source-evidence.json")
    promptset = read(ROOT / "qa/standing-missing-2026-10-05/oct5-full-7call-promptset.json")
    by_frame = {row["canonical_source_frame"]: row for row in manifest["cels"]}
    jobs = {row["complete_original_job"]["source_frame"]: row["complete_original_job"]
            for row in promptset["records"]}
    assert len(aliases["aliases"]) == 7
    reviewed = []
    for current, previous, start, end in [(1080, 1048, 1080, 1085), (1085, 1053, 1085, 1091)]:
        alias = next(row for row in aliases["aliases"] if row["source_frame"] == current)
        assert alias["verified_target_frame"] == previous
        assert alias["source_cel"] == source_map["frame_to_cel"][current]
        assert alias["verified_target_cel"] == source_map["frame_to_cel"][previous]
        assert alias["transform"] == {"kind": "identity", "matrix": [[1, 0, 0], [0, 1, 0]]}
        assert alias["review"] == "manual_full_resolution_source_approved"
        cel = by_frame[current]
        anchor = by_frame[previous]
        assert cel["selected_asset"]["verified_alias"] == alias
        assert cel["selected_asset"]["path"] == anchor["selected_asset"]["path"]
        assert Path(cel["selected_asset"]["path"]) == Path(jobs[previous]["output"])
        assert digest(ROOT / jobs[previous]["output"]) == jobs[previous]["output_sha256"]
        assert cel["artistic_accepted"] is False
        assert [(span["start"], span["end"]) for span in cel["source_exposures"]] == [(start, end)]
        checks = []
        for frame in range(start, end):
            record = evidence["saved_reference_checks"][str(frame)]
            actual_path = Path(record["path"])
            ref_path = Path(record["saved_reference"])
            actual = cv2.imread(str(actual_path))
            reference = cv2.imread(str(ref_path))
            assert actual.shape == (1080, 1920, 3)
            assert np.array_equal(actual, reference)
            assert digest(actual_path) == record["png_sha256"]
            assert digest(ref_path) == record["saved_reference_sha256"]
            assert sha256(actual.tobytes()).hexdigest() == record["decoded_bgr_sha256"]
            assert record["pts"] == source_meta["pts"][frame]
            checks.append({"frame": frame, "exact_reference": True,
                           "source_png_sha256": record["png_sha256"], "pts": record["pts"]})
        proof_names = [alias["proof_png"], alias["proof_local_regions"], *alias["proof_exposure_pages"]]
        reviewed.append({"alias": alias, "actual_source_checks": checks,
                         "proof_sha256": {name: digest(ROOT / name) for name in proof_names},
                         "source_drawing_review": "approved_by_root_native_spatial_and_all_exposure_inspection",
                         "character_artistic_accepted": False, "caption_gate_passed": False,
                         "final_composite_or_original_speed_review": "not_performed"})
    summary = manifest["summary"]
    assert (summary["mapped_cels_including_source_reuse"], summary["missing_selected_cels"],
            summary["covered_frames_draft_plus_source_reuse"],
            summary["contiguous_available_prefix_frames"]) == (422, 267, 2515, 1091)
    assert summary["raw_generated_png_files"] == 538 and summary["job_json_files"] == 543
    assert summary["accepted_character_cels"] == 0
    for name, path in zip(["source_aliases.json", "full-pv-progress-manifest.json"], snapshot_paths):
        path.write_bytes((ROOT / name).read_bytes())
    pending_files = [ROOT / "star_gestures_layers.py",
                     ROOT / "qa/star-gestures-layers-2026-10-05/f1037-native-caption-pair.png"]
    report = {
        "snapshot_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "after_render_source_alias_extension_not_a_retroactive_prerender_freeze",
        "source_alias_sha256_before": "4f694200247410c2e14e6fb5989c68ea0cf4b68ba6f6ca0d3e224c2620a53532",
        "source_alias_sha256_after": digest(ROOT / "source_aliases.json"),
        "reviewed_aliases": reviewed, "new_builtin_image_calls": 0,
        "source_exposures_changed": False, "new_covered_source_frames": 11,
        "progress": summary, "unchanged_frozen_inputs_and_videos": unchanged,
        "post_review_snapshots": {str(path.relative_to(ROOT)): digest(path) for path in snapshot_paths},
        "prior_420_cel_integrity_audit": "Preserved historical snapshot; it does not include these two later aliases.",
        "unresolved_private_star_layer_gate": {
            "interval": [1008, 1043], "blocking_caption_frames": [1037, 1043],
            "root_rechecked_f1037": "Japanese line still fragmented over the new boots; core-pixel numeric success is insufficient.",
            "shared_compositor_hooked": False,
            "frozen_private_files": {str(path.relative_to(ROOT)): digest(path) for path in pending_files},
        },
        "interrupted_parallel_tasks": {
            "tasks": ["star_finish_oct5", "standing_repeat_audit_oct5"],
            "reason": "Account usage-limit errors; no retry, model switch or alternate generation route attempted.",
            "existing_art_and_outputs_preserved": True,
        },
        "full_pv_delivered": False, "accepted": False,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "sha256": digest(report_path),
                      "source_aliases_sha256": report["source_alias_sha256_after"],
                      "new_source_frames_covered": 11, "progress": summary}, indent=2))


if __name__ == "__main__":
    main()
