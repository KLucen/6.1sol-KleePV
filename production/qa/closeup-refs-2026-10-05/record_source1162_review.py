"""Freeze a private source-only identity proposal after actual native image review."""

import json

from prepare_closeup_refs import OUT, ROOT, digest


def main():
    path = OUT / "source1162-alias-proposal.json"
    if path.exists():
        raise FileExistsError("Source alias proposal is already saved.")
    queue_path = OUT / "corrected-closeup-source-reference-queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    rows = {row["canonical_source_frame"]: row for row in manifest["cels"]}
    target = rows[1161]["selected_asset"]
    assert target is not None and target["path"].replace("\\", "/") == "generated/candidate-039.png"
    viewed = [OUT / f"f{frame:04d}-source-actual.png" for frame in [1161, 1162, 1163]]
    viewed += [OUT / f"f{frame:04d}-repeat-exposure-actual-native.png" for frame in [1161, 1162, 1163]]
    for frame in [1162, 1163]:
        viewed += [OUT / f"f1161-f{frame:04d}-repeat-{kind}-native.png"
            for kind in ["actual-rgb-x4-wide", "dual-contours-wide", "locals-1", "locals-2"]]
    viewed.append(OUT / "f1161-f1162-full-ab-rgb-contours.png")
    art = ROOT / target["path"]
    proposal = {
        "accepted": False, "source": queue["source"], "source_sha256": queue["source_sha256"],
        "source_frame": 1162, "source_candidate": "src-0694", "source_cel": "cel-0247",
        "verified_target_frame": 1161, "verified_target_candidate": "src-0693", "verified_target_cel": "cel-0246",
        "source_exposures_unchanged": rows[1162]["source_exposures"],
        "target_exposures_unchanged": rows[1161]["source_exposures"],
        "transform": {"kind": "identity", "matrix": [[1, 0, 0], [0, 1, 0]]},
        "character_only_reuse": True, "background_and_captions_keep_each_original_frame": True,
        "semantic_reason": "All actual f1161, f1162 and f1163 were sequentially decoded and checked pixel-exact against their canonical original references. Closed eyelids, small open O mouth, hat and bangs, both extended index fingers and curled remaining fingers, cuffs, shoulder sleeves, collar/hair edges, coat buttons and seam are the same source drawing. Actual native wide RGB differences and dual contours show caption replacement and independently moving stars, plus sparse codec strips rather than coherent character line changes. The caption at f1162 changes from the short previous line to the chorus line. f1163 is source-map codec_copy_of_representative for f1162. Only the character may reuse candidate-039 for [1162,1164); captions and graphics must come from each current original frame.",
        "all_actual_source_exposure_frames_viewed": [1161, 1162, 1163],
        "actual_viewed_files": [{"path": str(p), "sha256": digest(p)} for p in viewed],
        "view_scale": "1920x1080 original sources, 1570x1080 whole-character exposure/RGB/contour images, and 1440-wide local pages were viewed at native pixels. The 3840x2224 full AB overview was downscaled by the viewer to 2048x1186 and is not the native review basis.",
        "current_target": {"selection": target, "path": str(art), "sha256": digest(art),
            "actual_art_image_viewed": True, "artistic_accepted": False},
        "evidence_path": str(queue_path), "evidence_sha256": digest(queue_path),
        "sequential_decode": queue["sequential_decode"], "exact_source_checks": queue["exact_source_checks"],
        "source_map_sha256": queue["source_map_sha256"], "source_meta_sha256": queue["source_meta_sha256"],
        "worker_review": "source_semantic_visual_review_complete",
        "root_review": "actual_visual_review_required_before_adoption",
        "mapping_available_only_after_target_art_selected": True,
        "artistic_accepted": False, "alias_created": False, "original_speed_review": "not_performed",
        "no_art_or_shared_file_writes": True,
        "limits": "Source-only identity evidence; does not accept candidate art, future caption compositor or playback quality."
    }
    path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    print(json.dumps({"proposal": str(path), "sha256": digest(path), "viewed_source_frames": [1161, 1162, 1163]}))


if __name__ == "__main__":
    main()
