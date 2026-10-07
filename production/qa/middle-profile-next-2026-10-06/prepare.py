"""New missing cels only: source evidence, never final character drawing."""

import hashlib
import json
from pathlib import Path
import sys

import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta


def main():
    target = HERE / "source-evidence-queue.json"
    if target.exists():
        raise FileExistsError("Keep prior source evidence")
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    lookup = {r["canonical_source_frame"]: r for r in manifest["cels"]}
    cap = cv2.VideoCapture(manifest["source"])
    frames = {}
    for frame in range(2163):
        ok, image = cap.read()
        if not ok:
            raise RuntimeError(frame)
        if frame >= 2154:
            frames[frame] = image
            cv2.imwrite(str(HERE / f"f{frame}-source-actual.png"), image)
    cap.release()
    queue = []
    for frame, before in [(2155, 2154), (2157, 2155)]:
        row = lookup[frame]
        assert row["selected_asset"] is None
        assert (frames[frame] == cv2.imread(str(ROOT / row["source_reference"]))).all()
        source = HERE / f"f{frame}-source-actual.png"
        delta = HERE / f"f{before}-f{frame}-source-ab-rgb-contours.png"
        make_delta(HERE / f"f{before}-source-actual.png", source, delta)
        crops = []
        for name, (x0, y0, x1, y1) in {
            "eyes-mouth-bangs": (1100, 240, 1480, 650),
            "collar-shoulder": (890, 680, 1290, 1040),
            "rear-hair-tip": (45, 480, 885, 1080)
        }.items():
            current = HERE / f"f{frame}-{name}-current-native.png"
            previous = HERE / f"f{before}-for-{frame}-{name}-previous-native.png"
            local = HERE / f"f{frame}-{name}-native-ab-rgb-contours.png"
            cv2.imwrite(str(current), frames[frame][y0:y1, x0:x1])
            cv2.imwrite(str(previous), frames[before][y0:y1, x0:x1])
            make_delta(previous, current, local)
            crops.append({"name": name, "box_xyxy": [x0, y0, x1, y1], "delta": str(local), "current": str(current)})
        queue.append({"source_frame": frame, "cel": row["cel"], "source_exposures": row["source_exposures"],
                      "current_source": str(source), "source_reference": row["source_reference"],
                      "current_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                      "actual_previous": before, "overview_delta": str(delta), "native_locals": crops,
                      "actual_original_sequential_exact": True, "accepted": False})
    target.write_text(json.dumps({"queue": queue, "decoded_actual_interval": [2154, 2163],
                                  "source_exposure_frames": 8, "generation": "not called by evidence preparation"}, indent=2), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
