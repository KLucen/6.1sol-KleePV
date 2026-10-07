"""Record a complete draft delivery only after both encoded videos verify."""

from datetime import datetime, timezone
from hashlib import file_digest
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "qa/full-draft-one-pass-2026-10-07"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def main():
    pre = read(HERE / "pre-adoption-verification.json")
    post = read(HERE / "post-adoption-verification.json")
    summary = read(ROOT / "full-pv-progress-manifest.json")["summary"]
    timeline = read(ROOT / "timeline-full-oct7-draft-v1.json")
    regressions = read(HERE / "regression-test-run.json")
    assert pre["status"] == post["status"] == "ready"
    assert post["checked_assets"] == 195 and post["sealed_owners"] == 5
    assert not post["baseline_preservation"]["changed_original_frames"]
    assert summary["mapped_cels_including_source_reuse"] == 689
    assert summary["missing_selected_cels"] == 0
    assert summary["covered_frames_draft_plus_source_reuse"] == timeline["frames"] == 3658
    assert regressions["successful"] and regressions["tests_run"] == 81
    videos = {}
    for name in ("master", "comparison"):
        verification = HERE / f"{name}-technical-verification.json"
        verified = read(verification)
        path = Path(verified["video"])
        assert verified["technical_pass"] and all(verified["checks"].values())
        assert verified["expected_frames"] == 3658
        assert verified["video_sha256"] == digest(path)
        videos[name] = {"path": str(path), "sha256": digest(path),
                        "bytes": path.stat().st_size,
                        "dimensions": verified["video_timing"]["dimensions"],
                        "technical_check_count": len(verified["checks"]),
                        "verification": str(verification),
                        "verification_sha256": digest(verification),
                        "source_exact_video_seconds": verified["expected_boundary_seconds"],
                        "aac_packet_count": verified["audio_copy"]["actual_packets"],
                        "original_aac_payloads_copied": True}
    sampling = HERE / "encoded-sampling-report.json"
    visual_review = HERE / "encoded-static-visual-review.json"
    inputs = [ROOT / "source_map.json", ROOT / "source_meta.json",
              ROOT / "source_aliases.json", ROOT / "asset_selections.json",
              ROOT / "timeline-full-oct7-draft-v1.json", ROOT / "compose.py",
              HERE / "pre-adoption-verification.json", HERE / "post-adoption-verification.json",
              HERE / "regression-test-run.json", HERE / "deferred-art-review.json"]
    if visual_review.exists():
        inputs.append(visual_review)
    report = {"snapshot_utc": datetime.now(timezone.utc).isoformat(),
              "status": "complete_full_length_first_draft_for_user_feedback",
              "accepted": False, "mode": "strict_source_draft_preview",
              "new_missing_cels_resolved": 195, "new_source_exposure_frames": 790,
              "source_frames": 3658, "source_cel_upper_bound": 689,
              "output_exposures": len(timeline["output_exposures"]),
              "original_explicit_selection_rows_preserved": 323,
              "coverage_summary": summary, "videos": videos,
              "regression_tests_passed": 81, "private_batch_seals": post["seals"],
              "encoded_static_sampling_report": str(sampling) if sampling.exists() else None,
              "encoded_actual_static_visual_review": str(visual_review) if visual_review.exists() else None,
              "per_reference_view_flag_warning_count": post["warning_count"],
              "original_speed_art_acceptance": "not_performed; user feedback pending",
              "limitations": ["Complete exposure coverage is not artistic acceptance.",
                              "Known anatomy, costume, occlusion, caption and continuity issues are deferred, not passed.",
                              "689 is the conservative source cel upper bound, not 689 proven independent character gestures.",
                              "The comparison is additionally compressed; use the master for visual feedback."],
              "provenance_sha256": {str(p.relative_to(ROOT)): digest(p) for p in inputs}}
    output = HERE / "delivery.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({"delivery": str(output), "sha256": digest(output),
                      "status": report["status"], "videos": videos}))


if __name__ == "__main__":
    main()
