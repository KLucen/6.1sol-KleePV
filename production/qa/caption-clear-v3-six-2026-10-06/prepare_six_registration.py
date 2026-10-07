"""Inspect original six-frame Chinese placement before any shared edit."""

import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import star_gestures_layers


def core(image):
    b, g, r = cv2.split(image.astype(np.int16))
    return (b >= 194) & (g >= 215) & (r >= 230)


def label(image, text):
    band = np.full((27, image.shape[1], 3), 245, np.uint8)
    cv2.putText(band, text, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, .48, (20, 20, 20), 1, cv2.LINE_AA)
    return np.concatenate((band, image))


def translated(mask, dx, dy):
    height, width = mask.shape
    result = np.zeros_like(mask)
    ax0, ax1 = max(0, -dx), min(width, width - dx)
    ay0, ay1 = max(0, -dy), min(height, height - dy)
    result[ay0+dy:ay1+dy, ax0+dx:ax1+dx] = mask[ay0:ay1, ax0:ax1]
    return result


def main():
    cv2.setNumThreads(2)
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    destination = HERE / "source"
    destination.mkdir(exist_ok=True)
    donor_path = ROOT / "source_refs/src-1905-f3402.png"
    donor = cv2.imread(str(donor_path))[1002:1047, 660:1240]
    donor_core = core(donor)
    prior_layer = star_gestures_layers.caption_layer(2)
    np.savez_compressed(HERE / "old-phase2-layer-before-six-v3.npz", **{
        key: np.array(value) if key == "region" else value
        for key, value in prior_layer.items()
        if isinstance(value, np.ndarray) or key == "region"})
    cap = cv2.VideoCapture(metadata["source"])
    rows, records, overlays = [], [], []
    for frame in range(1043):
        ok, source = cap.read()
        if not ok:
            raise RuntimeError(frame)
        if frame < 1037:
            continue
        path = destination / f"f{frame:04d}.png"
        assert not path.exists(), path
        cv2.imwrite(str(path), source)
        observed = core(source[1002:1047, 660:1240])
        window = np.zeros(observed.shape, bool)
        window[:, :180] = True
        scores = []
        for dx in range(-20, -9):
            for dy in range(-2, 3):
                candidate = translated(donor_core, dx, dy)
                a, b = candidate & window, observed & window
                dice = 2 * np.count_nonzero(a & b) / max(1, a.sum() + b.sum())
                scores.append({"dx": dx, "dy": dy, "dice_clear_left_phrase": float(dice)})
        scores.sort(key=lambda item: item["dice_clear_left_phrase"], reverse=True)
        best = scores[0]
        candidate = translated(donor_core, best["dx"], best["dy"])
        overlay = np.zeros((*observed.shape, 3), np.uint8)
        overlay[observed] = (210, 80, 20)
        overlay[candidate] = (30, 80, 230)
        overlay[candidate & observed] = (230, 230, 230)
        overlays.append(label(overlay, f"f{frame} current-blue / donor-red / common-white; native 1:1"))
        prior = cv2.imread(str(ROOT / "qa/oct6-star-extended-integration" / f"f{frame}-shared-raw.png"))
        assert prior is not None
        rows.append(label(np.concatenate((source[945:1047, 650:1250], prior[945:1047, 650:1250]), axis=1),
                          f"f{frame} ACTUAL ORIGINAL | RETAINED V1 CURRENT; native 1:1"))
        records.append({"frame": frame, "source": str(path), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "source_pts": metadata["pts"][frame], "best": best, "next": scores[1],
                        "relative_to_v2_cn_slot": [best["dx"] + 15, best["dy"]],
                        "accepted": False})
    cap.release()
    cv2.imwrite(str(HERE / "six-actual-source-and-current-cn-native.png"), np.concatenate(rows))
    cv2.imwrite(str(HERE / "six-integer-registration-core-overlay-native.png"), np.concatenate(overlays))
    report = {"interval": [1037, 1043], "frames": records, "donor": str(donor_path),
              "donor_sha256": hashlib.sha256(donor_path.read_bytes()).hexdigest(),
              "registration_basis": "clear left Chinese phrase only; exclude cream original cuff", "accepted": False,
              "actual_native_review": "pending actual viewing; no shared old-star edits yet"}
    (HERE / "six-registration-before-edit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"frames": records, "all_relative_slot_zero": all(record["relative_to_v2_cn_slot"] == [0, 0] for record in records)}))


if __name__ == "__main__":
    main()
