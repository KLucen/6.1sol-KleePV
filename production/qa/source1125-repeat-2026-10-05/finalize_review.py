"""Record the completed manual source review; do not adopt an alias."""

from hashlib import sha256
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    evidence_path = OUT / "source-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    checks = json.loads((OUT / "candidate-and-exposure-checks.json").read_text(encoding="utf-8"))
    check = next(row for row in checks if row["source_frame"] == 1125)
    names = [
        "f1123-f1125-character-native-ab.png",
        "f1123-f1125-character-rgb-contours.png",
        "f1123-f1125-locals-native-page-01.png",
        "f1123-f1125-locals-native-page-02.png",
        "f1123-f1125-locals-native-page-03.png",
        "exposure-native-f1123-f1124.png",
        "exposure-native-f1125-f1126.png",
        "exposure-native-f1127-f1128.png",
    ]
    proposal = {
        "source": evidence["source"],
        "source_sha256": evidence["source_sha256"],
        "evidence_path": str(evidence_path),
        "evidence_sha256": digest(evidence_path),
        "sequential_decode": evidence["sequential_decode"],
        "all_six_saved_references_exact_bgr": evidence["all_saved_reference_exact"],
        "actual_source_frames_manually_viewed": list(range(1123, 1129)),
        "source_frame": 1125,
        "source_candidate": check["source_candidate"]["id"],
        "source_cel": check["source_cel"],
        "verified_target_frame": 1123,
        "target_candidate": check["target_candidate"]["id"],
        "verified_target_cel": check["target_cel"],
        "source_exposures_unchanged": check["source_exposures"],
        "target_exposures_unchanged": check["target_exposures"],
        "transform": {"kind": "identity", "matrix": [[1, 0, 0], [0, 1, 0]]},
        "character_only_reuse": True,
        "background_and_captions_keep_each_original_frame": True,
        "semantic_reason": (
            "All f1123..1128 retain the same half-open eyelids, small round mouth, hat face/ears, "
            "hair roots and ends, two curled hands at the chest, tightly crossing cream cuffs/sleeves, "
            "torso button/pocket/seam/hem lines, straight legs, pant cuffs and boot silhouettes. "
            "Native canonical RGB/dual contour/local evidence shows only isolated codec-colored "
            "person-edge pixels, not coherent redrawn contours. Pink stars and Japanese caption "
            "edges vary independently, including a star moving between the lower legs. "
            "The all-exposure native sheets show no intermediate character pose or expression change."
        ),
        "actual_viewed_files": [{"path": str(OUT / name), "sha256": digest(OUT / name)} for name in names],
        "generated_art_reviewed": False,
        "artistic_accepted": False,
        "actual_speed_reviewed": False,
        "alias_created": False,
        "recommendation": "propose_original_character_identity_alias_after_root_actual_visual_review",
        "mapping_available_only_after_target_art_selected": True,
        "metadata_only_previous_alias_checks": [row for row in checks if row["source_frame"] != 1125],
        "shared_files_written_by_worker": [],
        "status": "private_source_semantic_review_complete_pending_root_visual_approval",
    }
    path = OUT / "source-alias-proposal.json"
    path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    print(json.dumps({"proposal": str(path), "sha256": digest(path),
                      "source_exposure": check["source_exposures"],
                      "metadata_checks_pass": all(row["previous_proposal_metadata_matches"] for row in checks[:-1])}, indent=2))


if __name__ == "__main__":
    main()
