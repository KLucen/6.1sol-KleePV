"""Seal private visual recommendations without adopting any source alias."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REVIEWED = set(range(1097, 1103)) | set(range(1113, 1123)) | set(range(1129, 1141)) | set(range(1216, 1221)) | {1211}
REPEATS = {
    (1097, 1100): (
        "Same half-open eyelids, tiny closed caret mouth, right hand at collar and left arm lowered outward; "
        "hat, hair roots and ends, glove contours, cuffs, button/pocket/seam/hem lines, knees and boots overlap. "
        "Actual RGB differences inside the person are isolated codec-colored one-pixel strips, not coherent new outlines. "
        "Stars move and Japanese edges vary independently. All five source frames f1097..1101 visually reviewed."
    ),
    (1113, 1117): (
        "Same small open oval mouth, half-open eyes, left outward raised palm/cuff and right hand beside collar; "
        "hat/hair, shoulders, sleeve folds, coat/pockets/hem, legs and boots overlap. "
        "Only moving stars, lyric compression and scattered codec-colored short strips change. "
        "All five source frames f1113..1117 visually reviewed. f1118 is a new both-hands-at-chest drawing."
    ),
    (1129, 1133): (
        "Same tiny closed caret mouth, half-open eyes and clasped hands below chin at the collar; "
        "hat/hair, fingers, cuffs, crossed sleeve outlines, seam/pockets/hem, legs and boots overlap. "
        "A few one-pixel vertical/horizontal RGB strips coincide with codec grid lines without silhouette or fold displacement. "
        "Only moving stars and lyric compression are coherent differences. "
        "All five source frames f1129..1133 visually reviewed. f1134 is a new hands-raised-to-mouth drawing."
    ),
    (1216, 1217): (
        "Same close-up drawing with horizontal closed eyelids, large open round mouth, both arms raised and all fingers spread. "
        "Hat/hair, both palms/fingers, cuff openings, shoulder/sleeve folds, scarf/collar, lower hair tips and coat seams overlap. "
        "The Japanese and Chinese lyric changes at f1217; lower coat texture below the lyrics is otherwise the same drawing. "
        "All five source frames f1216..1220 visually reviewed. f1211 has half-open eyes and a smaller mouth and is not interchangeable."
    ),
}
DISTINCT = {
    (1117, 1118): (
        "Independent drawing: left hand moves inward from an outward visible palm/open cuff to the chest, "
        "left sleeve crosses the torso diagonally, right hand and cuff redraw, head/hat and lower coat/legs also redraw. "
        "All target exposure frames f1117..1122 visually reviewed."
    ),
    (1133, 1134): (
        "Independent drawing: clasped hands rise from collar/chest to in front of the mouth, "
        "finger/palm shapes and both sleeves/cuffs change, head/hat, hair ends, coat hem and boots also redraw. "
        "All target exposure frames f1133..1139 visually reviewed."
    ),
    (1211, 1216): (
        "Independent canonical poses are unambiguous in actual full-frame source AB: "
        "f1211 has half-open eyes and a small mouth, while f1216 has fully closed horizontal eyelids and a much larger round mouth; "
        "hat/hair and both sleeve/fold silhouettes also redraw. "
        "Only f1211 canonical and all f1216..1220 were visually inspected; do not claim all f1211..1215 received manual review."
    ),
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    evidence_path = OUT / "source-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    proposals, distinct = [], []
    for row in evidence["pairs"]:
        pair = (row["earlier"], row["current"])
        if pair not in REPEATS and pair not in DISTINCT:
            continue
        proof_files = dict(row["files"])
        actual_viewed = []
        if pair[0] < 1200:
            actual_viewed += [proof_files["character-native-ab"], proof_files["character-rgb-contours"]]
        for key, path in proof_files.items():
            if key.startswith("locals-page") and pair != (1211, 1216):
                actual_viewed.append(path)
        for page in evidence["exposure_review_pages"]:
            if set(page["frames"]).issubset(REVIEWED):
                for exposure in row["earlier_exposures"] + row["current_exposures"]:
                    if any(exposure["start"] <= frame < exposure["end"] for frame in page["frames"]):
                        actual_viewed.append(page["path"])
                        break
        item = {
            "source_frame": row["current"], "source_cel": row["current_cel"],
            "verified_target_frame": row["earlier"], "verified_target_cel": row["earlier_cel"],
            "source_exposures_unchanged": row["current_exposures"],
            "target_exposures_unchanged": row["earlier_exposures"],
            "transform": {"kind": "identity", "matrix": [[1, 0, 0], [0, 1, 0]]},
            "character_only_reuse": True, "background_and_captions_keep_each_original_frame": True,
            "semantic_reason": REPEATS.get(pair, DISTINCT.get(pair)),
            "proof_files": {key: {"path": path, "sha256": digest(Path(path))} for key, path in proof_files.items()},
            "actual_viewed_files": sorted(set(actual_viewed)),
            "review": "worker_original_source_semantic_review_complete_root_approval_required",
            "artistic_accepted": False, "alias_created": False,
        }
        if pair in REPEATS:
            item["recommendation"] = "propose_original_character_identity_alias_after_root_actual_visual_review"
            item["mapping_available_only_after_target_art_selected"] = True
            proposals.append(item)
        else:
            item["recommendation"] = "preserve_independent_source_cels"
            distinct.append(item)
    report = {
        "source": evidence["source"], "source_sha256": evidence["source_sha256"],
        "evidence_path": str(evidence_path), "evidence_sha256": digest(evidence_path),
        "sequential_decode_exact_saved_ref_frames": evidence["sequential_decode"]["exact_checked_frame_count"],
        "all_saved_references_exact_bgr": evidence["all_saved_reference_exact"],
        "actual_manual_source_frame_reviewed": sorted(REVIEWED),
        "manual_review_scope": "Original source, canonical native AB/RGB/dual contours/locals and all candidate exposures; not generated-art acceptance or actual-speed playback.",
        "proposal_count": len(proposals), "proposed_alias_source_frames_total": sum(
            exp["end"] - exp["start"] for row in proposals for exp in row["source_exposures_unchanged"]),
        "proposals": proposals, "independent_drawings": distinct,
        "no_global_mapping_or_source_edit": True, "aliases_adopted": False,
        "status": "private_original_source_recommendations_complete_pending_root_visual_approval",
    }
    path = OUT / "source-alias-proposal.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "sha256": digest(path),
                      "proposals": [{"source": row["source_frame"], "target": row["verified_target_frame"]} for row in proposals],
                      "proposed_alias_source_frames_total": report["proposed_alias_source_frames_total"],
                      "manually_viewed_source_frames": len(REVIEWED)}, indent=2))


if __name__ == "__main__":
    main()
