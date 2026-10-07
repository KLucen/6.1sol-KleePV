"""Review derivatives from a frozen encoded draft, never current layer helpers."""

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
START, END = 1008, 1225
VIDEO = ROOT / "output/klee-star-1008-1225-oct6-draft-v1.mp4"
COMPARISON = ROOT / "output/klee-star-1008-1225-oct6-existing-v1-comparison-draft.mp4"
RAW = ROOT / "qa/oct6-star-extended-integration/integrated-raw"


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(part)
    return sha.hexdigest()


def write_page(rows, number):
    canvas = np.full((35 + len(rows) * 132, 1200, 3), 248, np.uint8)
    cv2.putText(canvas, "ORIGINAL SOURCE                         EXISTING ENCODED V1 (NATIVE PIXELS)",
                (12, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.53, (25, 25, 25), 1, cv2.LINE_AA)
    for index, (frame, source, encoded) in enumerate(rows):
        y = 35 + index * 132
        cv2.putText(canvas, f"f{frame:04d} / local {frame - START:03d}", (12, y + 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (30, 30, 30), 1, cv2.LINE_AA)
        canvas[y + 23:y + 130, :600] = source
        canvas[y + 23:y + 130, 600:1200] = encoded
    path = HERE / f"caption-native-page-{number:02d}.png"
    if not cv2.imwrite(str(path), canvas):
        raise ValueError(f"Cannot save {path}")
    return path


def main():
    metadata_path = ROOT / "source_meta.json"
    timeline_path = ROOT / "timeline-star-1008-1225-oct6-draft-v1.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    source_path = Path(metadata["source"])
    pts = [Fraction(str(value)) for value in metadata["pts"]]
    origin = pts[START]
    boundary = pts[END] - origin
    origin_ticks = int(origin * 16000)
    last_pts_ticks = int((pts[END - 1] - origin) * 16000)
    last_duration_ticks = int((pts[END] - pts[END - 1]) * 16000)
    frozen = {"source": digest(source_path), "metadata": digest(metadata_path),
              "timeline": digest(timeline_path), "existing_encoded_v1": digest(VIDEO)}
    if frozen["source"] != metadata["sha256"]:
        raise ValueError("Frozen original has changed")
    source = cv2.VideoCapture(str(source_path))
    encoded = cv2.VideoCapture(str(VIDEO))
    for frame in range(START):
        if not source.grab():
            raise ValueError(f"Original ended at {frame}")
    canonical = {exposure["start"] for exposure in timeline["output_exposures"]}
    pts_filter = (f"settb=1/16000,setpts=round((N+{START})*1000/24)*16-{origin_ticks}")
    duration_bsf = (f"setts=duration=if(eq(PTS\\,{last_pts_ticks})\\,{last_duration_ticks}\\,DURATION)"
                    ":time_base=1/16000")
    encoder = subprocess.Popen([
        "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pixel_format", "bgr24",
        "-video_size", "3840x1080", "-framerate", "24", "-i", "pipe:0",
        "-ss", str(float(origin)), "-i", str(source_path), "-map", "0:v", "-map", "1:a:0",
        "-vf", pts_filter, "-fps_mode", "passthrough", "-enc_time_base", "1:16000",
        "-video_track_timescale", "16000", "-t", str(float(boundary)), "-c:v", "libopenh264",
        "-b:v", "24M", "-pix_fmt", "yuv420p", "-bsf:v", duration_bsf,
        "-c:a", "copy", "-movflags", "+faststart", str(COMPARISON)], stdin=subprocess.PIPE)
    rows, pages, records, whole = [], [], [], []
    try:
        for frame in range(START, END):
            ok_source, original = source.read()
            ok_encoded, current = encoded.read()
            if not ok_source or not ok_encoded:
                raise ValueError(f"Decode ended at source frame {frame}")
            if original.shape != (1080, 1920, 3) or current.shape != original.shape:
                raise ValueError(f"Unexpected dimensions at {frame}")
            comparison = np.concatenate((original, current), axis=1)
            encoder.stdin.write(comparison.tobytes())
            rows.append((frame, original[948:1055, 650:1250].copy(), current[948:1055, 650:1250].copy()))
            if len(rows) == 10 or frame == END - 1:
                pages.append(str(write_page(rows, len(pages) + 1).relative_to(ROOT)))
                rows = []
            if frame in canonical or frame in {1129, 1148, 1172, 1203, 1224}:
                path = HERE / f"f{frame:04d}-encoded-comparison-whole.png"
                cv2.imwrite(str(path), comparison)
                whole.append(str(path.relative_to(ROOT)))
            record = {"frame": frame, "encoded_std": float(np.std(current)),
                      "caption_std": float(np.std(current[948:1055, 650:1250]))}
            raw_path = RAW / f"f{frame:04d}-integrated.png"
            if raw_path.exists():
                raw = cv2.imread(str(raw_path))
                delta = np.abs(current.astype(np.int16) - raw.astype(np.int16))
                caption_delta = delta[948:1055, 650:1250]
                record.update({"raw_checkpoint_sha256": digest(raw_path),
                               "raw_mae": float(np.mean(delta)),
                               "raw_p95_absolute_channel_error": float(np.percentile(delta, 95)),
                               "caption_mae": float(np.mean(caption_delta)),
                               "caption_p95_absolute_channel_error": float(np.percentile(caption_delta, 95)),
                               "caption_p99_absolute_channel_error": float(np.percentile(caption_delta, 99))})
            records.append(record)
        if encoded.read()[0]:
            raise ValueError("Existing V1 has extra frames")
        encoder.stdin.close()
        if encoder.wait() != 0:
            raise ValueError("Comparison encoder failed")
    finally:
        source.release()
        encoded.release()
        if encoder.poll() is None:
            encoder.terminate()
    after = {"source": digest(source_path), "metadata": digest(metadata_path),
             "timeline": digest(timeline_path), "existing_encoded_v1": digest(VIDEO)}
    report = {
        "source_interval": [START, END], "frames": len(records),
        "comparison": str(COMPARISON.resolve()), "comparison_sha256": digest(COMPARISON),
        "frozen_input_sha256": frozen, "frozen_inputs_unchanged": frozen == after,
        "caption_roi": [650, 948, 1250, 1055], "caption_crops_rescaled": False,
        "caption_pages": pages, "canonical_whole_comparisons": whole, "frames_records": records,
        "derivative_method": "Sequential original decode plus existing V1 sequential decode; no layer helper or character generation used. Comparison is reencoded for display, not binary-identical stream copying.",
        "artistic_review": "pending_actual_view_of_saved_pages", "accepted": False,
        "limitations": ["Pixel deltas measure lossy encode error, not caption completeness or correct ownership.",
                        "This script has not watched at original speed.",
                        "Raw checkpoints exist for 182 of 217 frames; remaining 35 are only encoded/source comparisons."]}
    (HERE / "encoded-217-frame-diagnostic.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"frames": len(records), "caption_pages": len(pages), "whole_comparisons": len(whole),
                      "comparison": str(COMPARISON), "frozen_inputs_unchanged": frozen == after}))


if __name__ == "__main__":
    main()
