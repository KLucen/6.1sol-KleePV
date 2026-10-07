"""Private source-only evidence; no art, production code, or mapping mutation."""

import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
OLD = ROOT / "qa/star-microcel-audit-2026-10-05"
spec = importlib.util.spec_from_file_location("source_microcel_helpers", OLD / "prepare_evidence.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def descriptor(path):
    return {"path": str(path), "sha256": sha(path)}


def main():
    cv2.setNumThreads(2)
    meta = read_json(ROOT / "source_meta.json")
    source_map = read_json(ROOT / "source_map.json")
    candidates = {row["frame"]: row for row in source_map["candidates"]}
    manifest = read_json(ROOT / "full-pv-progress-manifest.json")
    cels = {row["canonical_source_frame"]: row for row in manifest["cels"]}
    source = Path(meta["source"])
    assert sha(source) == meta["sha256"]
    unchanged = {name: sha(ROOT / name) for name in (
        "source_map.json", "compose.py", "star_gestures_layers.py", "star_caption_alternate.py")}
    required = set(range(1140, 1147)) | set(range(1129, 1134))
    cap = cv2.VideoCapture(str(source))
    images, frames = {}, {}
    for frame in range(1147):
        ok, image = cap.read()
        if not ok:
            raise ValueError(f"Source stopped at f{frame}")
        if frame not in required:
            continue
        reference = ROOT / candidates[frame]["reference"]
        assert np.array_equal(image, cv2.imread(str(reference))), (frame, "saved source reference")
        images[frame] = image
        path = OUT / f"f{frame:04d}-source-actual.png"
        if not cv2.imwrite(str(path), image):
            raise OSError(path)
        frames[frame] = {
            "actual": descriptor(path), "pts": meta["pts"][frame],
            "decoded_bgr_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
            "source_reference": descriptor(reference), "source_reference_exact_bgr": True,
            "candidate": candidates[frame]["id"],
        }
    cap.release()
    pair_files = {}
    a, b = images[1140], images[1144]
    prefix = OUT / "f1140-f1144"
    for label, box, kinds in (
        ("full-native-ab", (0, 0, 1920, 1080), (0, 1)),
        ("full-rgb-contours", (0, 0, 1920, 1080), (2, 3)),
        ("character-native-ab", (600, 80, 1300, 1055), (0, 1)),
        ("character-rgb-contours", (600, 80, 1300, 1055), (2, 3)),
    ):
        path = prefix.with_name(prefix.name + f"-{label}.png")
        helper.board(a, b, 1140, 1144, box, path, kinds)
        pair_files[label] = descriptor(path)
    for offset in range(0, len(helper.STANDING_REGIONS), 2):
        path = OUT / f"f1140-f1144-locals-native-page-{offset // 2 + 1:02d}.png"
        helper.local_page(a, b, 1140, 1144, helper.STANDING_REGIONS[offset:offset + 2], path)
        pair_files[f"locals-page-{offset // 2 + 1:02d}"] = descriptor(path)
    exposure_pages = []
    for start in range(1140, 1147, 2):
        group = list(range(start, min(start + 2, 1147)))
        page = Image.new("RGB", (700 * len(group), 1007), "#242428")
        draw = ImageDraw.Draw(page)
        for col, frame in enumerate(group):
            draw.text((col * 700 + 8, 10), f"Actual source f{frame} native / no transform", fill="white")
            crop = images[frame][80:1055, 600:1300]
            page.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)), (col * 700, 32))
        path = OUT / f"exposure-native-f{group[0]:04d}-f{group[-1]:04d}.png"
        page.save(path)
        exposure_pages.append({"frames": group, **descriptor(path), "native_pixels_not_scaled": True})
    # Validate, but do not modify, the earlier independent worker's repeat evidence.
    old_proposal_path = OLD / "source-alias-proposal.json"
    old_proposal = next(row for row in read_json(old_proposal_path)["proposals"] if row["source_frame"] == 1133)
    old_evidence_path = OLD / "source-evidence.json"
    old_evidence = read_json(old_evidence_path)
    assert read_json(old_proposal_path)["evidence_sha256"] == sha(old_evidence_path)
    assert old_proposal["verified_target_frame"] == 1129
    assert old_proposal["source_exposures_unchanged"][0]["start"] == 1133
    assert old_proposal["source_exposures_unchanged"][0]["end"] == 1134
    old_files = []
    for name, proof in old_proposal["proof_files"].items():
        path = Path(proof["path"])
        assert sha(path) == proof["sha256"], (name, "old proof changed")
        old_files.append({"role": name, **proof})
    for page in old_evidence["exposure_review_pages"]:
        if any(1129 <= frame < 1134 for frame in page["frames"]):
            path = Path(page["path"])
            old_files.append({"role": "all-exposure-page", "frames": page["frames"], **descriptor(path)})
    for frame in range(1129, 1134):
        prior = old_evidence["frames"][str(frame)]
        assert prior["decoded_bgr_sha256"] == frames[frame]["decoded_bgr_sha256"]
        assert np.array_equal(images[frame], cv2.imread(prior["path"]))
    selected = read_json(ROOT / "asset_selections.json")["selections"]
    target = next(row for row in selected if row["source_frame"] == 1129)
    assert target["path"] == "generated/star-f1129-source-keypose-redraw-v2.png"
    assert sha(ROOT / target["path"]) == target["output_sha256"]
    after = {name: sha(ROOT / name) for name in unchanged}
    assert unchanged == after
    report = {
        "accepted": False, "source": str(source), "source_sha256": sha(source),
        "sequential_decode": [0, 1147], "checked_actual_frames": sorted(required),
        "frames": frames, "all_saved_source_references_exact": True,
        "1144_repeat_pending_visual_review": {
            "source_frame": 1144, "source_candidate": candidates[1144]["id"],
            "source_cel": cels[1144]["cel"],
            "verified_target_frame": 1140, "verified_target_candidate": candidates[1140]["id"],
            "verified_target_cel": cels[1140]["cel"],
            "source_exposures": cels[1144]["source_exposures"],
            "target_exposures": cels[1140]["source_exposures"],
            "proof_files": pair_files, "all_exposure_pages": exposure_pages,
            "numeric_screen_not_approval": helper.numeric_screen(a, b, helper.STANDING_REGIONS),
            "root_actual_visual_review_required": True,
        },
        "1133_existing_proposal_verified": {
            "proposal": descriptor(old_proposal_path), "evidence": descriptor(old_evidence_path),
            "source_interval": [1133, 1134], "target_interval": [1129, 1133],
            "actual1129_1133_source_matches_new_sequential_decode": True,
            "root_review_files": old_files,
            "currently_selected_target": target, "target_selected_draft_not_accepted": True,
            "root_actual_visual_review_required": True,
        },
        "unchanged_shared_source_code_sha256": after,
        "alias_adopted": False, "no_art_or_shared_file_writes": True,
        "status": "evidence_prepared_1144_source_semantic_visual_review_pending",
    }
    path = OUT / "source-evidence.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"actual_frames": len(frames), "1144_exposure_pages": len(exposure_pages),
                      "1133_proof_metadata_valid": True, "root_review_required": True,
                      "report": str(path)}))


if __name__ == "__main__":
    main()
