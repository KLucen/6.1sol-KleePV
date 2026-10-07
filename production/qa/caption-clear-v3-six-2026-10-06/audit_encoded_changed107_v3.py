"""Native encoded caption review for every changed Chinese source frame."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VIDEO = ROOT / "output/klee-star-1008-1225-oct6-draft-v3.mp4"
START, END = 1008, 1225
FIRST, LAST = 1037, 1144


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label(image, text):
    band = np.full((27, image.shape[1], 3), 245, np.uint8)
    cv2.putText(band, text, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, .48, (20, 20, 20), 1, cv2.LINE_AA)
    return np.concatenate((band, image))


def main():
    cv2.setNumThreads(2)
    destination = HERE / "encoded-107-native-review.json"
    if destination.exists():
        raise FileExistsError("Retain the saved encoded diagnostic evidence")
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    source_cap = cv2.VideoCapture(metadata["source"])
    sources = {}
    for frame in range(LAST):
        ok, source = source_cap.read()
        if not ok:
            raise RuntimeError(("source", frame))
        if frame >= FIRST:
            sources[frame] = source[945:1047, 650:1250].copy()
    source_cap.release()
    encoded = cv2.VideoCapture(str(VIDEO))
    records, rows, pages = [], [], []
    for index in range(END - START):
        ok, image = encoded.read()
        if not ok:
            raise RuntimeError(("encoded", index))
        assert image.shape == (1080, 1920, 3), image.shape
        frame = index + START
        if not FIRST <= frame < LAST:
            continue
        if frame < 1043:
            raw_path = HERE / "v3-raw" / f"f{frame}-v3.png"
        else:
            raw_path = ROOT / "qa/caption-clear-v2-2026-10-06/v2-raw" / f"f{frame:04d}-v2.png"
        raw = cv2.imread(str(raw_path))[945:1047, 650:1250]
        crop = image[945:1047, 650:1250]
        difference = np.abs(raw.astype(np.int16) - crop.astype(np.int16))
        mse = np.mean((raw.astype(np.float32) - crop.astype(np.float32)) ** 2)
        rows.append(label(np.concatenate((sources[frame], raw, crop), axis=1),
                          f"f{frame} ORIGINAL | RAW CORRECTED CN | V3 ENCODED; JP retained; native 1:1"))
        records.append({"source_frame": frame, "encoded_index": index, "original_source_pts": metadata["pts"][frame],
                        "raw_reference": str(raw_path), "raw_reference_sha256": sha(raw_path),
                        "encoded_caption_bgr_sha256": hashlib.sha256(crop.tobytes()).hexdigest(),
                        "caption_mean_abs_bgr_error": float(difference.mean()),
                        "caption_psnr_db": float(10 * np.log10(255 ** 2 / max(float(mse), 1e-10))),
                        "accepted": False})
        if len(rows) == 10 or frame == LAST - 1:
            path = HERE / f"encoded-changed107-cn-native-page-{len(pages)+1:02d}.png"
            cv2.imwrite(str(path), np.concatenate(rows))
            pages.append({"path": str(path), "sha256": sha(path)})
            rows = []
    ok, _ = encoded.read()
    assert not ok, "Unexpected extra encoded video frame"
    encoded.release()
    assert [record["source_frame"] for record in records] == list(range(FIRST, LAST))
    report = {"video": str(VIDEO), "video_sha256": sha(VIDEO), "source_interval": [START, END],
              "encoded_frames_decoded": END - START, "changed_cn_interval": [FIRST, LAST],
              "changed_cn_frames": len(records), "frames": records, "native_pages": pages,
              "accepted": False, "native_visual_review": "pending actual viewing",
              "numeric_metrics_are_not_visual_acceptance": True,
              "remaining_japanese_risks": ["1129..1143 寂 clover camouflage", "1144..1160 分/う clover camouflage"],
              "actual_speed_review": "not performed"}
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"encoded_frames": END - START, "changed_cn_frames": len(records),
                      "pages": len(pages), "video_sha256": report["video_sha256"],
                      "mean_caption_error": float(np.mean([record["caption_mean_abs_bgr_error"] for record in records]))}))


if __name__ == "__main__":
    main()
