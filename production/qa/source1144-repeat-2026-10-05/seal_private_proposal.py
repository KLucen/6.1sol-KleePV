"""Persist the reviewed original-source repeat proposal without adopting it."""

import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence_path = OUT / "source-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    current = evidence["1144_repeat_pending_visual_review"]
    assert current["source_exposures"][0]["start"] == 1144
    assert current["source_exposures"][0]["end"] == 1147
    proofs = current["proof_files"]
    exposures = current["all_exposure_pages"]
    for file in list(proofs.values()) + exposures:
        assert sha(Path(file["path"])) == file["sha256"]
    actually_viewed = [proofs[name]["path"] for name in (
        "full-native-ab", "character-native-ab", "character-rgb-contours",
        "locals-page-01", "locals-page-02", "locals-page-03")]
    actually_viewed += [page["path"] for page in exposures]
    report = {
        "accepted": False,
        "source": evidence["source"], "source_sha256": evidence["source_sha256"],
        "source_frame": 1144, "source_candidate": current["source_candidate"],
        "source_cel": current["source_cel"],
        "verified_target_frame": 1140, "verified_target_candidate": current["verified_target_candidate"],
        "verified_target_cel": current["verified_target_cel"],
        "source_exposures_unchanged": current["source_exposures"],
        "target_exposures_unchanged": current["target_exposures"],
        "transform": {"kind": "identity", "matrix": [[1, 0, 0], [0, 1, 0]]},
        "character_only_reuse": True,
        "background_and_captions_keep_each_original_frame": True,
        "semantic_reason": "All actual f1140..1146 were sequentially decoded, compared to exact saved source references, "
                           "and visually reviewed as native character crops. Closed eyelid strokes, tiny mouth dot, "
                           "the clasped hands directly in front of the mouth, overlapping cuffs and crossed sleeves, "
                           "hat/hair roots and tips, button/pocket/hem seams, trouser cuffs and shoe outlines coincide. "
                           "Actual RGB and dual contours show no coherent character movement; residual color/one-pixel "
                           "edge strips are codec noise. The lyric changes at f1144 and the stars continue moving "
                           "independently. Reuse only the character drawing for [1144,1147), never its earlier subtitle/background plate.",
        "all_actual_source_exposure_frames_viewed": list(range(1140, 1147)),
        "actual_viewed_files": actually_viewed,
        "view_scale": "Native character AB/RGB/contours, local pages and exposure pages were displayed without scaling. "
                      "The full-frame AB overview alone was resized from 3840x1112 to 2048x593; "
                      "it is not the basis for native local identity approval.",
        "proof_files": proofs, "proof_exposure_pages": exposures,
        "evidence_path": str(evidence_path), "evidence_sha256": sha(evidence_path),
        "worker_review": "source_semantic_visual_review_complete",
        "root_review": "actual_visual_review_required_before_adoption",
        "mapping_available_only_after_target_art_selected": True,
        "artistic_accepted": False, "alias_created": False,
        "original_speed_review": "not_performed",
        "1133_metadata_and_current_target_check": evidence["1133_existing_proposal_verified"],
        "no_art_or_shared_file_writes": True,
        "limits": "Original source identity evidence only. Does not accept generated artwork, a caption compositor, or motion at actual speed.",
    }
    path = OUT / "source-alias-proposal.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"source": 1144, "target": 1140, "reused_source_frames": 3,
                      "root_actual_visual_review_required": True, "alias_adopted": False,
                      "proposal_sha256": sha(path)}))


if __name__ == "__main__":
    main()
