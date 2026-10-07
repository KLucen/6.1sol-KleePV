"""Source-only native references for two confirmed neighboring occlusion repairs."""

import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta


def main():
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    mapping = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    out = ROOT / "qa/fast-fullpv-dance-occlusion-repairs"
    out.mkdir(exist_ok=True)
    wanted = {891, 894, 897}
    capture = cv2.VideoCapture(metadata["source"])
    actual = {}
    for frame in range(898):
        ok, current = capture.read()
        if not ok:
            raise ValueError(f"Decode stopped at {frame}")
        if frame in wanted:
            candidate = next(c for c in mapping["candidates"] if c["start"] == frame)
            reference = ROOT / candidate["reference"]
            if not np.array_equal(current, cv2.imread(str(reference))):
                raise ValueError(f"Canonical reference mismatch f{frame}")
            path = out / f"f{frame:04d}-source-actual.png"
            cv2.imwrite(str(path), current)
            actual[frame] = {"path": str(path), "decoded_sha256": hashlib.sha256(current.tobytes()).hexdigest(),
                             "canonical_reference": str(reference), "canonical_reference_exact": True}
    capture.release()
    for before, frame in [(891, 894), (894, 897)]:
        path = out / f"f{before:04d}-f{frame:04d}-source-ab-rgb-contours.png"
        make_delta(Path(actual[before]["path"]), Path(actual[frame]["path"]), path)
        actual[frame]["actual_delta"] = str(path)
        actual[frame]["delta_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (out / "source-evidence.json").write_text(json.dumps({"sequential_decode": [0, 898],
        "source": metadata["source"], "frames": actual, "artwork_edited": False}, indent=2), encoding="utf-8")
    print(json.dumps(actual, indent=2))


if __name__ == "__main__":
    main()
