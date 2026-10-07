"""Seal already-viewed private evidence; no production files are modified."""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VIEWED_STARTS = [1043, 1048, 1053, 1059, 1064, 1069, 1075, 1080, 1085,
                 1091, 1097, 1100, 1102, 1106, 1113, 1117, 1118, 1123,
                 1125, 1129, 1133, 1134, 1140, 1144, 1147, 1154, 1161]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = HERE / "private-static-review-seal-2026-10-06.json"
    if target.exists():
        raise FileExistsError("Do not overwrite a sealed private review")
    report_path = HERE / "private-119frame-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    timeline = json.loads((HERE / "timeline-private-1043-1162.json").read_text(encoding="utf-8"))
    assert [e["start"] for e in timeline["output_exposures"]] == VIEWED_STARTS
    assert [r["frame"] for r in report["frames"]] == list(range(1043, 1162))
    assert report["outside_ownership_bgr_exact_all119"]
    assert report["generated_interior_exact_all119"]
    assert report["current_source_observed_core_exact_all119"]
    assert all(report["shared_code_unchanged"].values())
    for record in report["frames"]:
        assert sha(Path(record["output_path"])) == record["output_sha256"]
    for name, digest in report["proposal_files"].items():
        assert sha(HERE / name) == digest
    pages = [Path(path) for path in report["caption_native_pages"]]
    bodies = [Path(path) for path in report["canonical_native_body_files"]]
    assert len(pages) == 12 and len(bodies) == 28
    evidence = pages + bodies + [HERE / "donor-f3504-native-caption.png",
                                HERE / "donor-f1144-native-caption.png",
                                HERE / "japanese-f3504-actual-4x.png",
                                HERE / "japanese-f1161-actual-4x.png"]
    files = [HERE / name for name in (
        "standing_layers_private.py", "audit_private.py", "build_short_caption.py",
        "short-caption-f1161-real.npz", "short-caption-provenance.json",
        "source-provenance.json", "timeline-private-1043-1162.json",
        "private-119frame-report.json", "PRIVATE_PROPOSAL.md", "seal_static_review.py")]
    files += evidence
    files += [Path(record["output_path"]) for record in report["frames"]]
    source_provenance = json.loads((HERE / "source-provenance.json").read_text(encoding="utf-8"))
    files += [Path(record["path"]) for record in source_provenance["retained_sources"]]
    assets = {timeline["assets"][e["cel"]]["path"] for e in timeline["output_exposures"]}
    files += [ROOT / path for path in sorted(assets)]
    seal = {
        "accepted": False,
        "date_client_timezone": "2026-10-06 Asia/Shanghai",
        "reviewer": "standing_oct6 worker; parent review pending",
        "interval": [1043, 1162],
        "source_frames": 119,
        "source_cel_ids": report["source_cels"],
        "output_exposures": report["exposures"],
        "unique_selected_images": report["unique_selected_images"],
        "actual_viewing": {
            "all_caption_native_pages_viewed": True,
            "caption_source_frames_viewed": list(range(1043, 1162)),
            "canonical_exposure_native_bodies_viewed": VIEWED_STARTS,
            "evidence_paths_and_sha256": {str(path): sha(path) for path in evidence},
            "native_scale_note": "Caption pages width1200 and bodies width1400/1340 shown at native pixel scale; diagnostic 4x donor images explicitly enlarged.",
        },
        "technical": {
            "all119_outside_ownership_bgr_exact": True,
            "all119_generated_interior_exact": True,
            "all119_current_observed_caption_core_exact": True,
            "source_pts_and_exposures_unchanged": True,
            "shared_code_unchanged": report["shared_code_unchanged"],
        },
        "native_static_findings": [
            "Major original pink hair, sleeve, and trouser ghosts found initially are removed in the final native body outputs.",
            "Both hands and two outside ponytails remain present in the selected drawings; closed-eye, clasped-hand, raised-index changes survive extraction.",
            "Chinese lines have no newly observed clipping or disappearance in all119 native caption rows.",
            "Authorized Japanese glyph shapes remain stationary and correctly timed; boot badges interfere visually with cream glyphs from1129 onward, especially short 分/う at1144..1160.",
            "Real final kana う in the f3504 donor is weaker than the other glyphs; f1161 closeup separates the word from boot badges.",
            "Selected coat/boot decoration changes, pose-amplitude differences, simplified pupils, and small boundary/gradient differences are deferred art issues, not a clean final acceptance.",
        ],
        "original_speed_review": "not performed",
        "encoded_review": "not performed",
        "parent_integration": "pending; exact interval/filename registration required",
        "technical_report_sha256": sha(report_path),
        "files": {str(path): sha(path) for path in sorted(set(files))},
    }
    target.write_text(json.dumps(seal, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(target), "sha256": sha(target), "sealed_files": len(seal["files"])}))


if __name__ == "__main__":
    main()
