"""Exact sequential source proof and shot-specific real lyric donor evidence."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
START, END = 1162, 1225
DONORS = (1256, 1267, 2420)
FROZEN = ("compose.py", "star_gestures_layers.py", "star_caption_alternate.py",
          "night_transition_layers.py", "cyan_profile_layers.py", "cyan_caption_layers.py",
          "dance_caption_layers.py", "raised_caption_layers.py", "opening_clock_layers.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label(image, text):
    band = np.full((27, image.shape[1], 3), 245, np.uint8)
    cv2.putText(band, text, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, .5, (20, 20, 20), 1, cv2.LINE_AA)
    return np.concatenate((band, image), axis=0)


def main():
    cv2.setNumThreads(2)
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    candidates = {c["start"]: c for c in source_map["candidates"]}
    assert sha(Path(metadata["source"])) == metadata["sha256"]
    source_dir = HERE / "source"
    source_dir.mkdir(exist_ok=True)
    retained = set(range(START, END)) | set(DONORS)
    capture = cv2.VideoCapture(metadata["source"])
    records = []
    images = {}
    for frame in range(max(retained) + 1):
        ok, image = capture.read()
        assert ok, frame
        if frame not in retained:
            continue
        path = source_dir / f"f{frame:04d}.png"
        if path.exists():
            assert np.array_equal(cv2.imread(str(path)), image), frame
        else:
            assert cv2.imwrite(str(path), image)
        candidate = candidates.get(frame)
        equal = None
        if candidate:
            equal = bool(np.array_equal(image, cv2.imread(str(ROOT / candidate["reference"]))))
            assert equal, frame
        records.append({"frame": frame, "pts": metadata["pts"][frame], "path": str(path),
                        "sha256": sha(path), "bgr_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
                        "canonical_bgr_exact": equal})
        images[frame] = image
    capture.release()
    for frame in DONORS:
        cv2.imwrite(str(HERE / f"donor-f{frame:04d}-native-caption.png"),
                    label(images[frame][945:1047, 650:1280], f"Actual original f{frame} donor, native 1:1"))
    frames = list(range(START, END))
    for offset in range(0, len(frames), 9):
        rows = [label(images[f][945:1047, 650:1250], f"SOURCE f{f} native 1:1")
                for f in frames[offset:offset+9]]
        cv2.imwrite(str(HERE / f"source-caption-native-page-{offset//9+1:02d}.png"), np.concatenate(rows))
    report = {"accepted": False, "interval": [START, END], "source_frames": END-START,
              "source_sha256": metadata["sha256"], "sequentially_decoded_through": max(retained),
              "retained_sources": records, "source_map_sha256": sha(ROOT / "source_map.json"),
              "source_aliases_sha256": sha(ROOT / "source_aliases.json"),
              "asset_selections_sha256": sha(ROOT / "asset_selections.json"),
              "shared_code_freeze": {name: sha(ROOT / name) for name in FROZEN},
              "caption_phases_pending_visual_confirmation": [[1162, 1217], [1217, 1225]],
              "native_static_review": "pending actual viewing"}
    (HERE / "source-provenance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"retained": len(records), "interval_frames": END-START, "canonical_exact": True}))


if __name__ == "__main__":
    main()
