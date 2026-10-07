"""Seal this bounded draft after technical and actual static image review."""

import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    evidence = read_json(OUT / "encoded-evidence-freeze.json")
    regression = read_json(OUT / "shared-35-cyan97-old74-regression.json")
    technical = {kind: read_json(OUT / f"{kind}-technical-verification.json")
                 for kind in ("draft", "comparison")}
    assert evidence["frames"] == 35 and evidence["unique_cels"] == 16
    assert regression["all_raw_checks_pass"] and not regression["failed"]
    assert len(regression["rows"]) == 206
    assert all(sha(ROOT / path) == value for path, value in
               evidence["frozen_sha256_after"].items())
    assert all(report["technical_pass"] and len(report["checks"]) == 17
               and all(report["checks"].values()) for report in technical.values())
    assert all(sha(Path(report["video"])) == report["video_sha256"]
               for report in technical.values())
    files = {
        "timeline-star-1008-1043-authorized-draft-v1.json",
        "qa/star-final-integration-2026-10-05/export_encoded_evidence.py",
        "qa/star-final-integration-2026-10-05/verify_shared_raw_regressions.py",
        "qa/star-final-integration-2026-10-05/static-encoded-review.md",
        "qa/star-final-integration-2026-10-05/encoded-evidence-freeze.json",
        "qa/star-final-integration-2026-10-05/shared-35-cyan97-old74-regression.json",
        "qa/star-final-integration-2026-10-05/draft-technical-verification.json",
        "qa/star-final-integration-2026-10-05/comparison-technical-verification.json",
    }
    files.update(evidence["frozen_sha256_after"])
    for kind in evidence["pages"].values():
        for page in kind:
            assert sha(ROOT / page["path"]) == page["sha256"]
            files.add(page["path"])
    for row in evidence["rows"]:
        for key in ("native_source_encoded_caption_pair", "native_raw_encoded_caption_pair", "full_encoded"):
            if key in row:
                file = row[key]
                assert sha(ROOT / file["path"]) == file["sha256"]
                files.add(file["path"])
    report = {
        "accepted": False, "source_interval": [1008, 1043], "source_frames": 35,
        "unique_selected_cels": 16, "output_exposures": 16,
        "video_boundary_seconds": 1.458,
        "technical_checks": {kind: {"passed": True, "checks": 17,
                                    "video": report["video"], "video_sha256": report["video_sha256"],
                                    "aac_packets": report["audio_copy"]["actual_packets"],
                                    "whole_packet_tail_seconds": report["audio_copy"]["whole_packet_tail_seconds"]}
                             for kind, report in technical.items()},
        "raw_regression": {"star_oracle_frames": 35, "cyan_frames": 97,
                           "older_dance_raised_frames": 74, "failures": 0,
                           "shared_code_unchanged_during_rerun": True},
        "actual_static_encoded_caption_view": {
            "source_encoded_pages": 5, "raw_encoded_pages": 5, "frames": 35,
            "caption_crop_pixels_not_scaled": True,
            "canonical_body_pages": 5, "body_images_are_thumbnails": True,
            "review_record": "qa/star-final-integration-2026-10-05/static-encoded-review.md"},
        "actual_speed_review_performed": False, "artistic_acceptance": False,
        "known_deferred_issues": [
            "Thin dark contrast edges over pale hair are more conspicuous than original captions.",
            "f1028 to f1033 selected decorated/plain coat simplification discontinuity.",
            "Existing selected draft pose/proportion/accessory differences remain unaccepted."],
        "authorization": "User allows clear original same-sentence glyph rebuilding, then requests rework after watching.",
        "authorized_alternate_interval": [1037, 1043],
        "authorized_glyph_layer_sha256": "a588071c0f94ff1697baf468cf9a7a8b13867d9cb5c36b8adc5318c13b7d09f6",
        "sha256": {path: sha(ROOT / path) for path in sorted(files)},
        "limits": "Bounded first-cut draft, not full PV completion. Static review and technical decode do not establish actual-speed motion or art acceptance.",
    }
    (OUT / "star-bounded-delivery-freeze.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"frames": 35, "files": len(files), "technical_pass": True,
                      "static_encoded_caption_review_complete": True,
                      "delivery_sha256": sha(OUT / "star-bounded-delivery-freeze.json")}))


if __name__ == "__main__":
    main()
