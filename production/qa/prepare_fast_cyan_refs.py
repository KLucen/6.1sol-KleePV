"""Exact sequential source and per-cel spatial evidence for the next missing shot."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta


def main():
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    package = next(p for p in manifest["work_packages"] if p["id"] == "shot-11-cyan_profile-f0911-f1008")
    all_rows = manifest["cels"]
    missing = set(package["missing_owned_cels"])
    pairs = [(all_rows[i-1], row) for i, row in enumerate(all_rows) if row["cel"] in missing]
    wanted = {row["canonical_source_frame"] for pair in pairs for row in pair}
    out = ROOT / "qa/fast-fullpv-cyan-2026-10-04"
    out.mkdir(exist_ok=True)
    capture = cv2.VideoCapture(manifest["source"])
    actual = {}
    for frame in range(max(wanted) + 1):
        ok, image = capture.read()
        if not ok:
            raise ValueError(f"Decode stopped at {frame}")
        if frame not in wanted:
            continue
        row = next(r for r in all_rows if r["canonical_source_frame"] == frame)
        if not np.array_equal(image, cv2.imread(str(ROOT / row["source_reference"]))):
            raise ValueError(f"Source/canonical mismatch f{frame}")
        path = out / f"f{frame:04d}-source-actual.png"
        cv2.imwrite(str(path), image)
        actual[frame] = {"path": str(path), "decoded_bgr_sha256": sha256(image.tobytes()).hexdigest(),
                         "png_sha256": sha256(path.read_bytes()).hexdigest(), "canonical_reference_exact": True}
    capture.release()
    queue = []
    for before, row in pairs:
        a, b = before["canonical_source_frame"], row["canonical_source_frame"]
        delta = out / f"f{a:04d}-f{b:04d}-source-ab-rgb-contours.png"
        make_delta(Path(actual[a]["path"]), Path(actual[b]["path"]), delta)
        current = cv2.imread(actual[b]["path"])
        face = out / f"f{b:04d}-source-eyes-nose-mouth.png"
        cv2.imwrite(str(face), current[230:730, 1060:1580])
        queue.append({"source_frame": b, "cel": row["cel"], "source_reference": row["source_reference"],
                      "current_source": actual[b], "before_source_frame": a, "before_source": actual[a],
                      "actual_delta": str(delta), "delta_sha256": sha256(delta.read_bytes()).hexdigest(),
                      "native_face_crop": str(face), "source_exposures": row["source_exposures"],
                      "manual_source_and_delta_review": "pending", "alias_created": False})
    target = out / "missing-source-reference-queue.json"
    target.write_text(json.dumps({"package": package["id"], "source": manifest["source"],
        "sequential_decode": [0, max(wanted)+1], "queue": queue,
        "exposures_changed": False, "artwork_generated": False}, indent=2), encoding="utf-8")
    print(json.dumps({"queue": str(target), "missing_cels": len(queue)}))


if __name__ == "__main__":
    main()
