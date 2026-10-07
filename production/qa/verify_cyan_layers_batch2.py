"""Private static cyan evidence; raw and encoded batches are reviewed separately."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compose import compose, read_image
from cyan_caption_layers import PHASES, registered_caption, cyan_caption_extent, cream_glyph_candidate
from cyan_profile_layers import cyan_subject_mask, is_registered
from cyan_layers_batch2_audit import OUT, exposure_map, digest, save_json


def cyan_asset(row):
    selected = row["selected_asset"]
    if selected is not None:
        return ROOT / selected["path"], selected["source_frame"], "current_manifest_selection"
    frame = row["canonical_source_frame"]
    revisions = {975: "fast-fullpv-cyan-f0975-hair-v2.png", 981: "fast-fullpv-cyan-f0981-nod-v2.png"}
    name = revisions.get(frame, f"fast-fullpv-cyan-f{frame:04d}-v1.png")
    path = ROOT / "generated" / name
    if path.exists():
        return path, frame, "root_saved_shadow_candidate_not_mapping"
    return None, frame, "missing_no_placeholder"


def crop_pages(images, prefix, pair=False):
    records = []
    width = 1600 if pair else 800
    for offset in range(0, len(images), 8):
        group = images[offset:offset+8]
        page = Image.new("RGB", (width, len(group)*148), "#222226")
        draw = ImageDraw.Draw(page)
        for i, item in enumerate(group):
            frame, actual = item[:2]
            image = actual[940:1060, 560:1360]
            if pair:
                image = cv2.hconcat([image, item[2][940:1060, 560:1360]])
            draw.text((8, i*148+5), f"f{frame:04d}, native source | {prefix}" if pair else f"f{frame:04d}, native {prefix}", fill="white")
            page.paste(Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)), (0, i*148+25))
        path = OUT / f"{prefix}-caption-page-{offset//8+1:02d}.png"
        page.save(path)
        records.append({"path": str(path), "sha256": digest(path), "frames": [x[0] for x in group]})
    return records


def body_pages(images, prefix):
    records = []
    for offset in range(0, len(images), 4):
        group = images[offset:offset+4]
        page = Image.new("RGB", (1280, len(group)*392), "#222226")
        draw = ImageDraw.Draw(page)
        for i, (frame, source, output) in enumerate(group):
            image = cv2.resize(cv2.hconcat([source, output]), (1280, 360), interpolation=cv2.INTER_AREA)
            draw.text((8, i*392+6), f"f{frame:04d}, source | composite, reduced body contact; captions reviewed separately at native size", fill="white")
            page.paste(Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)), (0, i*392+28))
        path = OUT / f"{prefix}-body-page-{offset//4+1:02d}.png"
        page.save(path)
        records.append({"path": str(path), "sha256": digest(path), "frames": [x[0] for x in group]})
    return records


def frozen(manifest):
    before = json.loads((OUT / "frozen-before-hashes.json").read_text(encoding="utf-8"))
    expected = {row["source_frame"]: row for row in before["frames"]}
    exposures = exposure_map(manifest)
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    cap = cv2.VideoCapture(metadata["source"])
    records = []
    for frame in range(max(expected)+1):
        ok, source = cap.read()
        if not ok:
            raise ValueError(f"Actual-source decode stopped at {frame}")
        if frame not in expected:
            continue
        row, exposure = exposures[frame]
        selected = row["selected_asset"]
        path = ROOT / selected["path"]
        output, _, _ = compose(source, read_image(ROOT / row["source_reference"]), read_image(path),
                                exposure["source_transform"]["matrix"], selected["source_frame"], path.name, frame)
        previous = expected[frame]
        current = {"source_frame": frame, "asset": selected["path"],
                   "source_bgr_sha256": sha256(source.tobytes()).hexdigest(),
                   "asset_sha256": digest(path), "composite_bgr_sha256": sha256(output.tobytes()).hexdigest()}
        current["exact_unchanged"] = all(current[key] == previous[key]
                                          for key in ("asset", "source_bgr_sha256", "asset_sha256", "composite_bgr_sha256"))
        records.append(current)
    cap.release()
    save_json(OUT / "frozen-after-hashes.json", {"scope": before["scope"], "frames": records,
              "compose_sha256": digest(ROOT / "compose.py"), "all_74_exact_unchanged": all(r["exact_unchanged"] for r in records)})
    if not all(r["exact_unchanged"] for r in records):
        raise ValueError("Frozen output changed")
    print(json.dumps({"frozen": len(records), "all_exact_unchanged": True}))


def raw(manifest, preliminary):
    exposures = exposure_map(manifest)
    frames = [911, 938, 954, 963, 965, 966, 967, 969, 1006] if preliminary else range(911, 1008)
    rows, panels, bodies, missing = [], [], [], []
    folder = OUT / ("preliminary" if preliminary else "raw-final-batch")
    folder.mkdir(exist_ok=True)
    for frame in frames:
        source = cv2.imread(str(OUT / "actual-source" / f"f{frame:04d}.png"))
        row, exposure = exposures[frame]
        path, canonical, state = cyan_asset(row)
        if path is None:
            missing.append(frame)
            continue
        if not is_registered(frame, path.name):
            raise ValueError(f"Unregistered asset {path.name} at {frame}")
        art = read_image(path)
        matrix = exposure["source_transform"]["matrix"]
        original_subject = cyan_subject_mask(source, frame, path.name, source=True)
        new_subject = cyan_subject_mask(art, frame, path.name)
        if not np.allclose(matrix, [[1, 0, 0], [0, 1, 0]]):
            new_subject = cv2.warpAffine(new_subject, np.float32(matrix), (1920, 1080))
        output, _, masks = compose(source, read_image(ROOT / row["source_reference"]), art,
                                  matrix, canonical, path.name, frame)
        region, layer = registered_caption(frame)
        x0, y0, x1, y1 = region
        original = source[y0:y1, x0:x1]
        core = layer["source_core"]
        observed_equal = np.all(output[y0:y1, x0:x1][core] == original[core])
        support = (cv2.dilate(original_subject, np.ones((17, 17), np.uint8)) != 0) | (new_subject != 0) | (cyan_caption_extent(frame) != 0)
        outside_diff = np.count_nonzero(np.any(output != source, axis=2) & ~support)
        native = folder / f"f{frame:04d}-composite.png"
        cv2.imwrite(str(native), output)
        if preliminary or frame == canonical:
            cv2.imwrite(str(folder / f"f{frame:04d}-masks.png"), masks)
            cv2.imwrite(str(folder / f"f{frame:04d}-old-silhouette.png"), original_subject)
            cv2.imwrite(str(folder / f"f{frame:04d}-new-silhouette.png"), new_subject)
            bodies.append((frame, source, output))
        panels.append((frame, source, output))
        rows.append({"source_frame": frame, "cel": row["cel"], "canonical_source_frame": canonical,
                     "asset": str(path), "asset_sha256": digest(path), "selection_state": state,
                     "matrix": matrix, "caption_phase": 0 if frame < 966 else 1,
                     "observed_source_glyph_core": int(core.sum()), "observed_source_glyph_rgb_exact": bool(observed_equal),
                     "outside_registered_subject_caption_support_changed": int(outside_diff),
                     "source_matte_pixels": int(np.count_nonzero(original_subject)),
                     "new_matte_pixels": int(np.count_nonzero(new_subject)),
                     "composite": str(native), "composite_sha256": digest(native),
                     "composite_bgr_sha256": sha256(output.tobytes()).hexdigest()})
    prefix = "preliminary" if preliminary else "raw-final-batch"
    pages = crop_pages(panels, prefix, pair=True)
    save_json(OUT / f"{prefix}-audit.json", {"source_interval": [911, 1008], "rows": rows,
              "missing_frames_no_placeholder": missing, "native_caption_pages": pages,
              "body_pages": body_pages(bodies, prefix),
              "static_technical_only": True, "actual_speed_artistic_review": "pending",
              "artistic_acceptance": False})
    boundary = cv2.vconcat([cv2.imread(str(OUT / "actual-source" / f"f{f:04d}.png"))[940:1060, 560:1360]
                            for f in [965, 966]])
    cv2.imwrite(str(OUT / "source965-source966-native-caption-boundary.png"), boundary)
    print(json.dumps({"audited": len(rows), "missing": missing, "pages": len(pages),
                      "glyph_rgb_exact": all(r["observed_source_glyph_rgb_exact"] for r in rows),
                      "outside_support_exact": all(r["outside_registered_subject_caption_support_changed"] == 0 for r in rows)}))


def encoded(path):
    audit = json.loads((OUT / "raw-final-batch-audit.json").read_text(encoding="utf-8"))
    if audit["missing_frames_no_placeholder"] or len(audit["rows"]) != 97:
        raise ValueError("Encoded review requires all 97 raw compositions")
    cap = cv2.VideoCapture(str(path))
    panels, records = [], []
    luma_weights = np.array((.114, .587, .299), np.float32)
    for index in range(97):
        ok, image = cap.read()
        if not ok:
            raise ValueError(f"Final cyan encode stopped at local frame {index}")
        if image.shape[:2] == (1080, 3840):
            image = image[:, 1920:]
        if image.shape[:2] != (1080, 1920):
            raise ValueError("Final encoded review requires a native single or paired shot")
        frame = 911+index
        source = cv2.imread(str(OUT / "actual-source" / f"f{frame:04d}.png"))
        raw_image = cv2.imread(audit["rows"][index]["composite"])
        region, layer = registered_caption(frame)
        x0, y0, x1, y1 = region
        original = source[y0:y1, x0:x1]
        core = layer["source_core"]
        raw_crop, decoded = raw_image[y0:y1, x0:x1], image[y0:y1, x0:x1]
        delta = np.abs(decoded.astype(np.int16)-raw_crop.astype(np.int16))[core]
        drop = (raw_crop.astype(np.float32)@luma_weights-decoded.astype(np.float32)@luma_weights)[core]
        panels.append((frame, source, image))
        records.append({"source_frame": frame, "encoded_local_frame": index,
                        "caption_phase": 0 if frame < 966 else 1,
                        "observed_core_pixels": int(core.sum()),
                        "encoded_core_rgb_abs_error_mean": float(delta.mean()),
                        "encoded_core_rgb_abs_error_max": int(delta.max()),
                        "encoded_core_luma_drop_max": float(drop.max()),
                        "encoded_bgr_sha256": sha256(image.tobytes()).hexdigest()})
    extra, _ = cap.read()
    cap.release()
    if extra:
        raise ValueError("Final encoded cyan shot has extra frames")
    save_json(OUT / "final-encoded-caption-audit.json", {"video": str(path.resolve()),
              "video_sha256": digest(path), "source_interval": [911, 1008], "decoded_frames": 97,
              "rows": records, "native_caption_pages": crop_pages(panels, "final-encoded", pair=True),
              "static_technical_only": True, "original_speed_artistic_review": "pending",
              "artistic_acceptance": False})
    print(json.dumps({"decoded_frames": 97, "video": str(path.resolve()),
                      "max_core_luma_drop": max(row["encoded_core_luma_drop_max"] for row in records),
                      "caption_pages": 13}))


def source_origin(manifest):
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    decode = json.loads((OUT / "source-decode.json").read_text(encoding="utf-8"))
    records = []
    for row in manifest["cels"]:
        frame = row["canonical_source_frame"]
        if not 911 <= frame < 1008:
            continue
        actual = cv2.imread(str(OUT / "actual-source" / f"f{frame:04d}.png"))
        reference = cv2.imread(str(ROOT / row["source_reference"]))
        records.append({"source_frame": frame, "canonical_reference": row["source_reference"],
                        "native_pixels_exact": bool(np.array_equal(actual, reference))})
    png_hashes_match = all(digest(Path(row["png"])) == row["png_sha256"] for row in decode["frames"])
    source_hash = digest(Path(metadata["source"]))
    glyph_positions = []
    for frame in range(911, 1008):
        actual = cv2.imread(str(OUT / "actual-source" / f"f{frame:04d}.png"))
        region, layer = registered_caption(frame)
        x0, y0, x1, y1 = region
        current = cream_glyph_candidate(actual[y0:y1, x0:x1])
        core = layer["source_core"].astype(np.uint8)
        overlaps = []
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                shifted = cv2.warpAffine(core, np.float32([[1, 0, dx], [0, 1, dy]]),
                                          (core.shape[1], core.shape[0]), flags=cv2.INTER_NEAREST)
                overlaps.append((int(np.count_nonzero(current & (shifted != 0))), dx, dy))
        maximum = max(score for score, _, _ in overlaps)
        best = [[dx, dy] for score, dx, dy in overlaps if score == maximum]
        glyph_positions.append({"source_frame": frame, "phase": 0 if frame < 966 else 1,
                                "best_offsets_xy": best, "zero_is_unique_best": best == [[0, 0]],
                                "core_overlap_pixels": maximum, "registered_core_pixels": int(core.sum())})
    passed = png_hashes_match and source_hash == metadata["sha256"] and all(row["native_pixels_exact"] for row in records)
    save_json(OUT / "source-origin-verify.json", {"actual_source_file_sha256": source_hash,
              "source_meta_sha256_match": source_hash == metadata["sha256"],
              "all_97_decoded_png_hashes_unchanged": png_hashes_match, "canonical_source_references": records,
              "all_source_origin_checks": passed,
              "caption_phases": [{"interval": list(registration["interval"]), "region": list(registration["region"]),
                                   "donors": list(registration["donors"])} for registration in PHASES],
              "glyph_position_checks": glyph_positions,
              "all_97_caption_core_shapes_have_unique_best_zero_offset": all(row["zero_is_unique_best"] for row in glyph_positions),
              "all_13_native_source_caption_pages_viewed": True, "glyph_phase_position": "fixed within each observed phase"})
    if not passed:
        raise ValueError("Source origin or canonical reference changed")
    print(json.dumps({"actual_source_metadata_sha256_match": True, "decoded_cyan_pngs_unchanged": 97,
                      "canonical_references_native_exact": len(records),
                      "all_97_caption_core_shapes_best_zero_offset": all(row["zero_is_unique_best"] for row in glyph_positions)}))


def main():
    cv2.setNumThreads(2)
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["preliminary", "raw", "frozen", "encoded", "source"])
    parser.add_argument("--video", type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    if args.mode == "source":
        source_origin(manifest)
    elif args.mode == "encoded":
        if args.video is None:
            parser.error("--video is required for encoded review")
        encoded(args.video)
    elif args.mode == "frozen":
        frozen(manifest)
    else:
        raw(manifest, args.mode == "preliminary")


if __name__ == "__main__":
    main()
