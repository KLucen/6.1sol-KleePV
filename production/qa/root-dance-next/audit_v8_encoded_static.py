"""Bounded final-encoded f863..886 artifact review; no encode or generation."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "qa/opening-v8-encoded-caption-evidence"
sys.path.insert(0, str(ROOT))
from dance_caption_layers import REGION, dance_caption_layer, warm_glyph_core
from review_opening_preview import file_hash


def identity(path):
    raw = path.read_bytes()
    image = Image.open(path).convert("RGB")
    return {"path": str(path), "file_sha256": sha256(raw).hexdigest(),
            "size_wh": list(image.size), "native_rgb_pixel_sha256": sha256(np.asarray(image).tobytes()).hexdigest()}


def main():
    report_path = EVIDENCE / "report.json"
    raw_report = report_path.read_bytes()
    report = json.loads(raw_report.decode("utf-8"))
    rows = [r for r in report["caption_rows"] if 863 <= r["frame"] < 887]
    if [r["frame"] for r in rows] != list(range(863, 887)):
        raise ValueError("Missing a requested actual encoded/source caption row")
    video_path = Path(report["encoded_video"])
    video_hash = file_hash(video_path)
    if video_hash != report["video_sha256"]:
        raise ValueError("Final single-video identity changed")
    source_audit = json.loads((OUT / "extension-caption-audit.json").read_text(encoding="utf-8"))
    source_hashes = {r["frame"]: r["decoded_native_bgr_sha256"] for r in source_audit["decoded_frames"]}
    layer = dance_caption_layer()
    x0, y0, x1, y1 = REGION
    chinese_rows = np.zeros(layer["source_core"].shape, bool)
    chinese_rows[1006-y0:1040-y0] = True
    pairs, frame_evidence = [], []
    for row in rows:
        pair_path = Path(row["pair"])
        ident = identity(pair_path)
        if ident["size_wh"] != [764, 93] or ident["file_sha256"] != row["pair_sha256"]:
            raise ValueError("Encoded pair identity changed for f" + str(row["frame"]))
        pair_image = Image.open(pair_path).convert("RGB")
        pairs.append(pair_image)
        rgb = np.asarray(pair_image)
        original, encoded = rgb[:, :382], rgb[:, 382:]
        core = warm_glyph_core(np.ascontiguousarray(original[..., ::-1])) & layer["source_core"]
        difference = np.max(np.abs(original.astype(np.int16) - encoded.astype(np.int16)), axis=2)
        unsupported_delta = core & (difference > 30)
        yy, xx = np.nonzero(unsupported_delta)
        count = int(unsupported_delta.sum())
        if count != row["core_difference_gt30_pixels"]:
            raise ValueError("Subset metric changed for f" + str(row["frame"]))
        raw_pair_path = ROOT / "qa/dance-caption-v8" / f"f{row['frame']:04d}-native-caption-pair.png"
        raw_pair = np.asarray(Image.open(raw_pair_path).convert("RGB"))
        compression_delta = np.max(np.abs(encoded.astype(np.int16) - raw_pair[:, 382:].astype(np.int16)), axis=2)
        frame_evidence.append({
            "frame": row["frame"], "native_pair": ident,
            "exporter_decoded_source_bgr_sha256": row["decoded_source_sha256"],
            "exporter_decoded_encoded_bgr_sha256": row["decoded_encoded_sha256"],
            "source_hash_matches_independent_actual_24_frame_audit": source_hashes[row["frame"]] == row["decoded_source_sha256"],
            "source_half_pixel_equal_to_raw_composite_evidence_source_half": np.array_equal(original, raw_pair[:, :382]),
            "registered_current_warm_subset_pixels": int(core.sum()),
            "registered_current_warm_subset_difference_gt30_pixels": count,
            "chinese_registered_subset_difference_gt30_pixels": int((unsupported_delta & chinese_rows).sum()),
            "nonchinese_registered_subset_difference_gt30_pixels": int((unsupported_delta & ~chinese_rows).sum()),
            "registered_subset_delta_gt30_native_xy": [[int(x + x0), int(y + y0)] for x, y in zip(xx, yy)],
            "subset_difference_is_not_fragmentation_or_full_glyph_test": True,
            "encoded_vs_raw_caption_crop_mean_max_channel_delta": float(compression_delta.mean()),
            "encoded_vs_raw_caption_crop_p95_max_channel_delta": float(np.percentile(compression_delta, 95)),
            "encoded_vs_raw_caption_crop_pixels_max_channel_delta_gt30": int((compression_delta > 30).sum()),
            "page_manually_viewed": True,
            "obvious_new_fragmented_chinese_glyph_observed": False,
        })
    pages = []
    for number in range(9, 15):
        page_ref = report["pages"]["overlap"][number - 1]
        path = Path(page_ref["path"])
        ident = identity(path)
        if ident["file_sha256"] != page_ref["sha256"]:
            raise ValueError("Encoded page identity changed")
        begin = (number - 9) * 4
        rebuilt = Image.new("RGB", (1528, 840), "white")
        for i, pair in enumerate(pairs[begin:begin + 4]):
            panel = Image.new("RGB", (1528, 210), "white")
            panel.paste(pair.resize((1528, 186), Image.Resampling.NEAREST), (0, 24))
            ImageDraw.Draw(panel).text((5, 5), f"f{863+begin+i:04d} ORIGINAL | ENCODED SINGLE V8", fill="black")
            rebuilt.paste(panel, (0, i * 210))
        mismatch = int(np.count_nonzero(np.any(np.asarray(Image.open(path).convert("RGB")) != np.asarray(rebuilt), axis=2)))
        if mismatch:
            raise ValueError("Encoded page differs from its native pairs")
        pages.append({"page": number, "frames_inclusive": [863 + begin, 866 + begin],
                      "artifact": ident, "manually_viewed": True, "page_rebuild_pixel_mismatch": mismatch})
    full = []
    for frame in (880, 886):
        sample = next(s for s in report["full_samples"] if s["frame"] == frame)
        path = Path(sample["path"])
        ident = identity(path)
        image = np.asarray(Image.open(path).convert("RGB"))
        full_bgr_hash = sha256(np.ascontiguousarray(image[..., ::-1]).tobytes()).hexdigest()
        row = next(r for r in rows if r["frame"] == frame)
        crop = np.asarray(pairs[frame - 863])[:, 382:]
        pixel_match = np.array_equal(image[y0:y1, x0:x1], crop)
        if ident["file_sha256"] != sample["sha256"] or full_bgr_hash != row["decoded_encoded_sha256"] or not pixel_match:
            raise ValueError("Final encoded full-image identity/crop mismatch")
        full.append({"frame": frame, "artifact": ident, "manually_viewed": True,
                     "native_bgr_sha256_matches_exporter_actual_decode": True,
                     "caption_crop_pixel_equal_to_native_pair_encoded_half": pixel_match})
    differences = [r["registered_current_warm_subset_difference_gt30_pixels"] for r in frame_evidence]
    chinese = [r["chinese_registered_subset_difference_gt30_pixels"] for r in frame_evidence]
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Final single V8 encoded static review only: pages 09..14, all 24 new frames f863..886, and native full samples f880/f886",
        "reviewed_interval_half_open": [863, 887], "pages_viewed": 6, "new_encoded_frames_viewed": 24, "full_samples_viewed": 2,
        "encoded_video": str(video_path), "encoded_video_file_sha256": video_hash,
        "exporter_report": {"path": str(report_path), "file_sha256": sha256(raw_report).hexdigest(),
                            "reported_sequential_decode_count": report["sequential_decoded_video_frames"],
                            "reported_caption_interval_half_open": report["caption_interval"],
                            "reported_total_caption_rows": len(report["caption_rows"])},
        "all_requested_pages_native_pair_hashes_and_two_full_decode_hashes_verified": True,
        "all_24_source_bgr_hashes_match_prior_independent_source_decode": all(r["source_hash_matches_independent_actual_24_frame_audit"] for r in frame_evidence),
        "additional_encoded_video_decode_performed_by_this_static_review": False,
        "raw_vs_encoded_are_separate_evidence_versions": True,
        "stable_registered_current_warm_subset_gt30_difference_range": [min(differences), max(differences)],
        "chinese_registered_current_warm_subset_gt30_difference_range": [min(chinese), max(chinese)],
        "pages": pages, "full_samples": full, "frame_evidence": frame_evidence,
        "manual_findings": [
            "All 24 new encoded-frame crops were viewed. No obvious newly fragmented Chinese glyph was seen at the displayed 2x nearest-neighbor scale relative to the raw-composite inspection.",
            "At f880..886, Chinese first characters remain foreground over the left brown boot and final characters remain foreground over the right brown boot. No pasted source shoe/cuff rectangle was observed.",
            "Japanese left/right end glyphs overlap pale cream boot cuffs and remain low-contrast. Moving pale star lines cross central Japanese counters and the Chinese middle; that limitation existed in the raw composites and is not cured by encoding.",
            "f880/f886 full encoded samples preserve the new open two-leg stance and registered caption contact. Their display is static, not actual-speed or artistic approval.",
            "Encoding changes antialiased/color pixels. A subset difference count is not a new-fragmentation locator; recorded pixel coordinates are technical deltas only."
        ],
        "confirmed_new_chinese_fragmentation_locations": [],
        "complete_glyph_acceptance": False, "encoded_source_exact_claim": False,
        "artistic_acceptance": False, "actual_speed_watch_performed": False,
        "production_core_or_selections_modified": False,
        "stopping_boundary": "This bounded subtask is complete after the static encoded review. No further generation, encode retry, stage continuation or shared-state change is authorized by this review.",
        "limitations": [
            "The parent exporter performed the actual sequential 887-frame encoded/source decode and kept 75 caption rows; this private review reads and hash-verifies its artifacts, not a second 887-frame decode.",
            "Only pages 09..14/new f863..886 and f880/f886 encoded full samples are visually reviewed here. Other encoded pages and clear-phase images remain the parent review scope.",
            "Current warm core intersected with the stable donor is a subset, not every glyph pixel, OCR or exact original source transparency.",
            "H264/YUV color and AA differences mean raw/composite source-exact claims cannot be transferred to the encoded video.",
            "Japanese pale-on-pale cuff contact, star crossings and full-motion readability are not accepted.",
            "Underlying hair/costume/contour continuity findings remain open; no artistic acceptance or complete PV claim is made."
        ]}
    target = OUT / "final-v8-encoded-new-frames-static-review.json"
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    md = ["# Final V8 Encoded New-Frame Static Review", "",
          "Scope: pages 09..14, every new encoded frame f863..886 (24 frames), plus f880/f886 full encoded samples. All six pages and both full samples were visually viewed. No generation, production edit, encode or retry was performed.", "",
          f"Final single V8 video SHA256: `{video_hash}`.",
          f"Exporter report SHA256: `{sha256(raw_report).hexdigest()}`.",
          "All 24 native-pair hashes, six page hashes and two full-image hashes match exporter evidence. Each page is pixel-equal to its four native pairs. Both full-image BGR hashes match the exporter's actual full-frame decode hash, and their caption crops match encoded pair halves. All 24 original-source BGR hashes match the earlier independent actual-source decode.", "",
          "## Observations And Limits", ""]
    md += ["- " + finding for finding in result["manual_findings"]]
    md += ["", f"Registered current-warm subset difference >30 range across these new 24 encoded frames: `{result['stable_registered_current_warm_subset_gt30_difference_range']}`. Chinese-only registered subset range: `{result['chinese_registered_current_warm_subset_gt30_difference_range']}`. These are limited technical deltas, not full glyph acceptance.",
           "", "| Encoded Page | Frames Inclusive | SHA256 |", "|---|---|---|"]
    md += [f"| {p['page']} | {p['frames_inclusive']} | `{p['artifact']['file_sha256']}` |" for p in pages]
    md += ["", "| Full Encoded Frame | SHA256 |", "|---|---|"]
    md += [f"| {s['frame']} | `{s['artifact']['file_sha256']}` |" for s in full]
    md += ["", "## Scope Boundary", ""] + ["- " + limit for limit in result["limitations"]]
    md += ["", "Complete glyph acceptance: false. Encoded source-exact claim: false. Artistic acceptance: false. Actual-speed watch: not performed.", "", result["stopping_boundary"]]
    (OUT / "final-v8-encoded-new-frames-static-review.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(target), "page_count": 6, "new_frames": 24, "full_samples": 2,
                      "subset_gt30_range": result["stable_registered_current_warm_subset_gt30_difference_range"],
                      "chinese_subset_gt30_range": result["chinese_registered_current_warm_subset_gt30_difference_range"],
                      "all_24_original_source_hash_match": result["all_24_source_bgr_hashes_match_prior_independent_source_decode"]}, indent=2))


if __name__ == "__main__":
    main()
