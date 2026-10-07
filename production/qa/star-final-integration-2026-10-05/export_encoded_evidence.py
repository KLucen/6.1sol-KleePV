"""Native source/raw/encoded evidence for the authorized 35-frame star draft."""

import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT))
from compose import validate_render_timing

START, END = 1008, 1043
RECT = (610, 950, 1310, 1055)
TIMELINE = ROOT / "timeline-star-1008-1043-authorized-draft-v1.json"
VIDEO = ROOT / "output/klee-star-1008-1043-authorized-draft-v1.mp4"
COMPARISON = ROOT / "output/klee-star-1008-1043-authorized-comparison-draft-v1.mp4"
PRIVATE = ROOT / "qa/star-caption-source-recovery-2026-10-05"
EVIDENCE = OUT / "encoded-native-evidence"
RELEVANT = (
    "compose.py", "star_gestures_layers.py", "star_caption_alternate.py",
    "cyan_profile_layers.py", "cyan_caption_layers.py", "night_transition_layers.py",
    "dance_caption_layers.py", "raised_caption_layers.py",
    "layers/star-caption-f3402-authorized-v1.npz",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bgr_sha(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, image):
    if not cv2.imwrite(str(path), image):
        raise OSError(path)
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(path)}


def pages(pairs, prefix, rows=7, native=True):
    result = []
    for start in range(0, len(pairs), rows):
        group = pairs[start:start + rows]
        height, width = group[0][1].shape[:2]
        canvas = np.full((len(group) * (height + 24), width, 3), 32, np.uint8)
        for i, (frame, pair) in enumerate(group):
            y = i * (height + 24)
            scale_label = "NATIVE PIXELS" if native else "640x360 THUMBNAILS"
            cv2.putText(canvas, f"f{frame:04d} {prefix} / {scale_label} / UNACCEPTED",
                        (8, y + 17), cv2.FONT_HERSHEY_SIMPLEX, .45,
                        (255, 255, 255), 1, cv2.LINE_AA)
            canvas[y + 24:y + 24 + height] = pair
        row = save(EVIDENCE / f"{prefix}-page-{start // rows + 1:02d}.png", canvas)
        row["frames"] = [frame for frame, _ in group]
        row["native_crop_pixels_not_scaled"] = native
        result.append(row)
    return result


def main():
    cv2.setNumThreads(2)
    EVIDENCE.mkdir(exist_ok=True)
    timeline = read_json(TIMELINE)
    metadata = read_json(ROOT / "source_meta.json")
    timing = validate_render_timing(timeline, metadata)
    regression = read_json(OUT / "shared-35-cyan97-old74-regression.json")
    assert regression["all_raw_checks_pass"] and len(regression["rows"]) == 206
    assert regression["timeline_sha256"]["star"] == sha(TIMELINE)
    assert (timeline["source_start"], timeline["frames"]) == (START, END - START)
    assert timeline["output_exposures"][0]["start"] == START
    assert timeline["output_exposures"][-1]["end"] == END
    assert all(a["end"] == b["start"] for a, b in
               zip(timeline["output_exposures"], timeline["output_exposures"][1:]))
    used = sorted({span["cel"] for span in timeline["output_exposures"]})
    asset_freeze = {}
    for cel in used:
        asset = timeline["assets"][cel]
        asset_freeze[cel] = {
            "path": asset["path"], "sha256": sha(ROOT / asset["path"]),
            "source_frame": asset["source_frame"],
            "source_reference": asset["source_reference"],
            "source_reference_sha256": sha(ROOT / asset["source_reference"]),
            "review": asset["review"], "accepted": False,
        }
    frozen_paths = [ROOT / name for name in RELEVANT]
    frozen_paths += [TIMELINE, VIDEO, COMPARISON,
                    PRIVATE / "authorized-candidate-post-static-freeze.json",
                    OUT / "shared-35-cyan97-old74-regression.json"]
    before = {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in frozen_paths}
    assert all(before[name] == value for name, value in
               regression["relevant_code_sha256_after"].items())
    star_rows = {row["frame"]: row for row in regression["rows"] if row["scope"] == "star"}
    source_cap = cv2.VideoCapture(timeline["source"])
    encoded_cap = cv2.VideoCapture(str(VIDEO))
    comparison_cap = cv2.VideoCapture(str(COMPARISON))
    for frame in range(START):
        if not source_cap.grab():
            raise ValueError(f"Source ended before {frame}")
    x0, y0, x1, y1 = RECT
    source_pairs, raw_pairs, rows, bodies = [], [], [], []
    canonical = {span["start"] for span in timeline["output_exposures"]}
    for frame in range(START, END):
        oks, source = source_cap.read()
        oke, encoded = encoded_cap.read()
        okc, comparison = comparison_cap.read()
        assert oks and oke and okc, (frame, "decode")
        assert source.shape == encoded.shape == (1080, 1920, 3)
        assert comparison.shape == (1080, 3840, 3)
        raw = cv2.imread(str(OUT / f"f{frame:04d}-shared-raw.png"))
        oracle = cv2.imread(str(PRIVATE / f"f{frame:04d}-authorized-private-compose.png"))
        assert np.array_equal(raw, oracle), (frame, "raw/private oracle")
        assert bgr_sha(raw) == star_rows[frame]["composite_bgr_sha256"]
        assert bgr_sha(source) == star_rows[frame]["source_bgr_sha256"]
        a, b, c = [image[y0:y1, x0:x1] for image in (source, raw, encoded)]
        source_pair = np.concatenate([a, c], axis=1)
        raw_pair = np.concatenate([b, c], axis=1)
        source_pairs.append((frame, source_pair))
        raw_pairs.append((frame, raw_pair))
        record = {
            "source_frame": frame, "accepted": False,
            "source_bgr_sha256": bgr_sha(source), "raw_bgr_sha256": bgr_sha(raw),
            "encoded_bgr_sha256": bgr_sha(encoded),
            "source_raw_unchanged_from_regression": True,
            "native_source_encoded_caption_pair": save(
                EVIDENCE / f"f{frame:04d}-source-encoded-caption.png", source_pair),
            "native_raw_encoded_caption_pair": save(
                EVIDENCE / f"f{frame:04d}-raw-encoded-caption.png", raw_pair),
            "raw_encoded_caption_mean_abs_channel_delta": float(
                np.abs(b.astype(np.int16) - c.astype(np.int16)).mean()),
            "metric_scope": "Compression diagnostic only; not a glyph readability or art acceptance test.",
            "real_glyph_alternate_applied": frame >= 1037,
        }
        if frame in canonical or frame == END - 1:
            record["full_encoded"] = save(EVIDENCE / f"f{frame:04d}-encoded.png", encoded)
            body = np.concatenate([cv2.resize(image, (640, 360), interpolation=cv2.INTER_AREA)
                                   for image in (source, raw, encoded)], axis=1)
            bodies.append((frame, body))
        rows.append(record)
    assert not encoded_cap.read()[0], "Draft has extra frame"
    assert not comparison_cap.read()[0], "Comparison has extra frame"
    source_cap.release()
    encoded_cap.release()
    comparison_cap.release()
    after = {name: sha(ROOT / name) for name in before}
    assert before == after, "Frozen inputs changed during encoded evidence export"
    report = {
        "accepted": False, "source_interval": [START, END], "frames": 35,
        "unique_cels": len(used), "exposures": len(timeline["output_exposures"]),
        "source_boundary_seconds": float(timing["boundary_seconds"]),
        "caption_rect": list(RECT), "assets": asset_freeze,
        "frozen_sha256_before": before, "frozen_sha256_after": after,
        "frozen_files_unchanged": True,
        "pages": {
            "native_source_encoded": pages(source_pairs, "SOURCE-ENCODED"),
            "native_raw_encoded": pages(raw_pairs, "RAW-ENCODED"),
            "canonical_bodies": pages(bodies, "SOURCE-RAW-ENCODED-BODY", 4, native=False),
        },
        "rows": rows, "static_native_review": "pending_separate_manual_record",
        "actual_speed_review": "not_performed", "artistic_acceptance": False,
        "limitations": "Source-exact frame PTS and independent glyph timing are technical checks. "
                       "f3402 real glyph alpha, AA and target ink are an authorized reconstruction, "
                       "not exact recovery of invisible original strokes. Encoded pages are static only.",
    }
    (OUT / "encoded-evidence-freeze.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"frames": len(rows), "cels": len(used),
                      "native_caption_pages": len(report["pages"]["native_source_encoded"]),
                      "timeline_sha256": sha(TIMELINE), "frozen_files_unchanged": True}))


if __name__ == "__main__":
    main()
