"""Record viewed v8 source/composite evidence identity; no production edits."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
EVIDENCE_DIR = ROOT / "qa/dance-caption-v8"
START, END = 831, 887
REGION = (754, 954, 1136, 1047)


def identity(path):
    raw = path.read_bytes()
    im = Image.open(path).convert("RGB")
    return {"path": str(path), "file_sha256": sha256(raw).hexdigest(),
            "size_wh": list(im.size), "rgb_pixel_sha256": sha256(np.asarray(im).tobytes()).hexdigest()}


def main():
    evidence_path = EVIDENCE_DIR / "evidence.json"
    evidence_raw = evidence_path.read_bytes()
    evidence = json.loads(evidence_raw.decode("utf-8"))
    rows = [r for r in evidence["frames"] if START <= r["frame"] < END]
    if [r["frame"] for r in rows] != list(range(START, END)):
        raise ValueError("Exporter evidence does not contain exactly all 56 requested frames")
    prior_source = json.loads((OUT / "extension-caption-audit.json").read_text(encoding="utf-8"))
    actual_source_hashes = {r["frame"]: r["decoded_native_bgr_sha256"] for r in prior_source["decoded_frames"]}
    row_evidence, native_images = [], []
    for row in rows:
        path = Path(row["native_caption_pair"])
        ident = identity(path)
        if ident["size_wh"] != [764, 93] or ident["file_sha256"] != row["pair_sha256"]:
            raise ValueError("Native pair identity/dimensions changed: " + str(path))
        native_images.append(Image.open(path).convert("RGB"))
        row_evidence.append({
            "frame": row["frame"], "saved_unaccepted_asset": row["asset"],
            "exporter_decoded_source_bgr_sha256": row["decoded_source_sha256"],
            "independent_24_frame_source_hash_match": (row["decoded_source_sha256"] == actual_source_hashes[row["frame"]]) if row["frame"] in actual_source_hashes else None,
            "native_pair": ident, "native_pair_matches_exporter_hash": True,
            "exporter_caption_diagnostics": row["caption_diagnostics"],
            "exporter_undeclared_changed_pixels": row["undeclared_changed_pixels"],
            "manual_page_reviewed": True,
            "obvious_new_chinese_glyph_fragmentation_observed_at_viewed_2x_scale": False,
        })

    pages = []
    for page_number in range(1, 15):
        begin = (page_number - 1) * 4
        group = native_images[begin:begin + 4]
        reconstructed = Image.new("RGB", (1528, 840), "white")
        for i, im in enumerate(group):
            frame = START + begin + i
            panel = Image.new("RGB", (1528, 210), "white")
            panel.paste(im.resize((1528, 186), Image.Resampling.NEAREST), (0, 24))
            ImageDraw.Draw(panel).text((5, 5), f"f{frame:04d} ORIGINAL | COMPOSITE, nearest-neighbor detail", fill="black")
            reconstructed.paste(panel, (0, i * 210))
        path = EVIDENCE_DIR / f"overlap-caption-page-{page_number:02d}.png"
        im = Image.open(path).convert("RGB")
        changed = int(np.count_nonzero(np.any(np.asarray(im) != np.asarray(reconstructed), axis=2)))
        if changed:
            raise ValueError(f"Page {page_number} changed or does not match its four native pairs")
        pages.append({"page": page_number, "frames_inclusive": [START + begin, START + begin + 3],
                      "artifact": identity(path), "viewed": True,
                      "pixel_mismatch_to_rebuilt_page_from_its_four_native_pairs": changed})
    full = []
    x0, y0, x1, y1 = REGION
    for frame in (863, 868, 873, 880):
        path = EVIDENCE_DIR / f"f{frame:04d}-full-composite.png"
        image = np.asarray(Image.open(path).convert("RGB"))
        pair = np.asarray(native_images[frame - START])
        changed = int(np.count_nonzero(np.any(image[y0:y1, x0:x1] != pair[:, 382:], axis=2)))
        if changed:
            raise ValueError(f"Full image and native pair disagree for f{frame}")
        full.append({"frame": frame, "artifact": identity(path), "viewed": True,
                     "caption_region_mismatch_to_native_pair_composite_half": changed,
                     "no_obvious_orphan_cream_waist_dots_observed": True})
    provenance = []
    for name, expected in evidence["provenance"].items():
        current = sha256(Path(name).read_bytes()).hexdigest()
        provenance.append({"path": name, "exporter_recorded_sha256": expected,
                           "current_file_sha256": current, "matches_exporter_record": current == expected})
    findings = [
        {"frames_inclusive": [831, 838], "observation": "Chinese bottom line remains readable and no new missing/fractured stroke was obvious at viewed 2x scale; Japanese center remains crowded by pale star lines."},
        {"frames_inclusive": [839, 847], "observation": "Descending/front boot crosses the left lyric area. Chinese first characters remain in front of the brown boot/sole rather than erased; not all AA is source-exact."},
        {"frames_inclusive": [848, 867], "observation": "Left front boot sits behind the first Chinese glyphs. Registered cream strokes remain visible over brown. Japanese left/top boot-cuff contact can be pale-on-pale."},
        {"frames_inclusive": [868, 872], "observation": "New f868 shoe/pose underlay is present; Chinese first glyphs remain foreground with no obvious new break. Long rear hair remains an independent raw-art continuity issue."},
        {"frames_inclusive": [873, 879], "observation": "Foot/cuff shape changes with the unfolded kick. Chinese left two characters remain present over the left boot, and the rest of the line remains legible; Japanese starts cross pale cuff with weak contrast."},
        {"frames_inclusive": [880, 886], "observation": "Both boots enter opposite ends. Chinese left two characters lie over the left brown boot; the final two Chinese characters lie over the right brown boot. The visible strokes remain foreground without obvious new fragmentation. Japanese end glyphs cross cream cuffs and lose contrast; center star crossings remain reconstruction/contrast limits.",
         "native_inspection_regions_xyxy": {
             "chinese_left_boot_contact": [754, 1006, 850, 1041],
             "chinese_right_boot_contact": [1040, 1006, 1136, 1041],
             "chinese_center_star_crossing": [884, 1006, 1016, 1041],
             "japanese_left_pale_cuff_contact": [754, 954, 858, 990],
             "japanese_right_pale_cuff_contact": [1025, 954, 1136, 990]
         }}
    ]
    diagnostics = [d for row in rows for d in row["caption_diagnostics"] if d["name"] == "dance_stable_donor_lyric_subset"]
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Updated v8 transparent-caption static inspection of 14 source/composite pages, all 56 frames f831..886, plus four actual native full composites f863/868/873/880",
        "source_interval_half_open": [START, END],
        "native_pair_count": len(rows), "viewed_page_count": len(pages), "viewed_full_composite_count": len(full),
        "all_56_native_pairs_hash_verified_and_pages_viewed": True,
        "all_14_pages_pixel_equal_to_rebuilds_from_their_four_native_pairs": True,
        "all_four_full_composite_caption_crops_pixel_equal_to_native_pair_target_half": True,
        "exporter_evidence": {"path": str(evidence_path), "file_sha256": sha256(evidence_raw).hexdigest(),
                              "reported_actual_decode_count": evidence["decoded_frames"], "reported_interval_half_open": evidence["source_interval"]},
        "provenance": provenance,
        "all_current_production_provenance_hashes_match_exporter_evidence": all(p["matches_exporter_record"] for p in provenance),
        "independent_source_24_frame_audit": {"path": str(OUT / "extension-caption-audit.json"),
                                              "file_sha256": sha256((OUT / "extension-caption-audit.json").read_bytes()).hexdigest(),
                                              "scope_half_open": [863, 887],
                                              "all_24_full_native_bgr_hashes_match_exporter_decoded_source": all(r["independent_24_frame_source_hash_match"] for r in row_evidence if 863 <= r["frame"] < 887)},
        "new_56_frame_original_video_decode_performed_by_this_private_review": False,
        "exporter_stable_registered_subset_mismatch_gt30_count_range": [min(d["core_mismatch_gt30_pixels"] for d in diagnostics), max(d["core_mismatch_gt30_pixels"] for d in diagnostics)],
        "exporter_warm_candidate_outside_alpha_count_range": [min(d["current_warm_candidates_outside_donor_alpha_pixels"] for d in diagnostics), max(d["current_warm_candidates_outside_donor_alpha_pixels"] for d in diagnostics)],
        "pages": pages, "full_composites": full, "frame_evidence": row_evidence, "manual_findings": findings,
        "obvious_new_chinese_fragmentation_observed": False,
        "confirmed_new_fragmentation_locations": [],
        "verdict": "No obvious new fragmented Chinese glyph found within these reviewed static artifacts. Registered stable-subset numbers and fixed-phase support are not complete glyph acceptance, exact source alpha or a contrast/motion pass.",
        "complete_glyph_acceptance": False, "artistic_acceptance": False, "actual_speed_watch_performed": False,
        "core_or_selections_modified": False,
        "limitations": [
            "This review reads exporter-produced actual composites and pairs. It does not independently decode 56 original-video frames; only the earlier separate 24-frame actual source audit is cross-hash-checked.",
            "All Chinese observations are static 2x nearest-neighbor page inspection, not OCR certification or inspection of every AA pixel.",
            "The stable registered donor subset is narrower than full glyph geometry. Zero subset mismatches do not certify glyph counters, AA, contrast or exact original alpha.",
            "Japanese glyphs over cream cuffs and moving pale star crossings remain hard to read; no complete Japanese glyph acceptance is claimed.",
            "Four updated full images showed no obvious orphan cream waist dots, but existing pale hair wedges at f880 remain raw-art occlusion questions, not yellow-effect or caption-layer approval.",
            "All underlying Klee drafts remain unaccepted for hair/costume/contour continuity. No full-speed watch or whole-PV completion is claimed."
        ]}
    report_path = OUT / "updated-v8-transparent-caption-static-review.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = ["# Updated V8 Transparent Caption Static Review", "",
          "Scope: all 14 updated overlap pages, covering every frame f831..886 (56 frames), and the four actual native full composites f863/f868/f873/f880. All were visually viewed. No core/selection changes.", "",
          f"Exporter evidence SHA256: `{report['exporter_evidence']['file_sha256']}`.",
          "All 56 native-pair file hashes match exporter records. Each viewed page is pixel-equal to a reconstructed page from its four specific native pairs. All four full-composite caption crops match their native pair target halves. Exact page/frame/file hashes and dimensions are in the JSON.",
          "The previous independent f863..886 source audit's 24 native BGR hashes all match the exporter source hashes. This private static review did not re-decode 56 source-video frames and does not convert old 32-frame labels into a new 56-frame proof.", "",
          "## Static Findings", ""]
    md += [f"- f{f['frames_inclusive'][0]}..{f['frames_inclusive'][1]}: {f['observation']}" for f in findings]
    md += ["", "No obvious new fragmented Chinese glyph was found at the viewed 2x static scale. At f880..886, the first Chinese characters remain over the left brown boot and the final characters remain over the right brown boot; no broad source-shoe rectangle was visibly reintroduced. Japanese on pale cuffs and star crossings remain contrast/reconstruction limitations.",
           "", f"Exporter stable registered-subset mismatch >30 range: `{report['exporter_stable_registered_subset_mismatch_gt30_count_range']}`; warm candidates outside alpha range: `{report['exporter_warm_candidate_outside_alpha_count_range']}`. These diagnostics have their stated subset-only scope and are not full-glyph acceptance.", "",
           "## Reviewed Artifacts", "", "| Page | Frames Inclusive | SHA256 |", "|---|---|---|"]
    md += [f"| {p['page']} | {p['frames_inclusive']} | `{p['artifact']['file_sha256']}` |" for p in pages]
    md += ["", "| Full Composite Frame | SHA256 |", "|---|---|"]
    md += [f"| {f['frame']} | `{f['artifact']['file_sha256']}` |" for f in full]
    md += ["", "## Limits", ""] + ["- " + s for s in report["limitations"]]
    md += ["", "Complete glyph acceptance: false. Artistic acceptance: false. Actual-speed watch: not performed."]
    (OUT / "updated-v8-transparent-caption-static-review.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "pages": len(pages), "native_pairs": len(rows),
                      "full_images": len(full), "current_provenance_matches": report["all_current_production_provenance_hashes_match_exporter_evidence"],
                      "independent_24_source_hash_match": report["independent_source_24_frame_audit"]["all_24_full_native_bgr_hashes_match_exporter_decoded_source"],
                      "subset_mismatch_range": report["exporter_stable_registered_subset_mismatch_gt30_count_range"],
                      "warm_outside_range": report["exporter_warm_candidate_outside_alpha_count_range"]}, indent=2))


if __name__ == "__main__":
    main()
