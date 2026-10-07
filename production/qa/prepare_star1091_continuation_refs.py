"""Prepare the next missing source poses, without generating or selecting artwork."""

from hashlib import sha256
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa/star1091-continuation-2026-10-05"
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta

spec = importlib.util.spec_from_file_location(
    "standing_source_evidence", ROOT / "qa/standing-repeat-audit-2026-10-05/audit_source_repeats.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, nargs="+", default=[1091, 1097, 1100, 1102, 1106, 1113])
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output.resolve()
    queue_path = OUT / "missing-source-reference-queue.json"
    if queue_path.exists():
        raise FileExistsError("Source queue already saved; resume it without replacing the evidence.")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    rows = manifest["cels"]
    by_frame = {row["canonical_source_frame"]: row for row in rows}
    targets = args.frames
    wanted = set(targets)
    previous = {}
    for frame in targets:
        row = by_frame[frame]
        assert row["selected_asset"] is None, f"Already mapped f{frame}; do not regenerate."
        earlier = rows[rows.index(row) - 1]["canonical_source_frame"]
        previous[frame] = earlier
        wanted.add(earlier)
    decoded = {}
    capture = cv2.VideoCapture(manifest["source"])
    for frame in range(max(wanted) + 1):
        ok, image = capture.read()
        if not ok:
            raise ValueError(f"Source decode failed f{frame}")
        if frame not in wanted:
            continue
        reference = ROOT / by_frame[frame]["source_reference"]
        assert np.array_equal(image, cv2.imread(str(reference))), f"Exact source mismatch f{frame}"
        path = OUT / f"f{frame:04d}-source-actual.png"
        cv2.imwrite(str(path), image)
        decoded[frame] = {"path": str(path), "sha256": digest(path),
                          "decoded_bgr_sha256": sha256(image.tobytes()).hexdigest(),
                          "saved_reference": str(reference), "saved_reference_sha256": digest(reference),
                          "sequential_original_exact": True}
    capture.release()
    queue = []
    for frame in targets:
        earlier = previous[frame]
        current = cv2.imread(decoded[frame]["path"])
        before = cv2.imread(decoded[earlier]["path"])
        delta = OUT / f"f{earlier:04d}-f{frame:04d}-source-ab-rgb-contours.png"
        make_delta(Path(decoded[earlier]["path"]), Path(decoded[frame]["path"]), delta)
        locals_path = OUT / f"f{earlier:04d}-f{frame:04d}-source-locals-native.png"
        native.write_locals(before, current, earlier, frame, locals_path)
        face = OUT / f"f{frame:04d}-source-face-native.png"
        cv2.imwrite(str(face), current[60:370, 800:1180])
        body = OUT / f"f{frame:04d}-source-body-native.png"
        cv2.imwrite(str(body), current[330:1055, 600:1300])
        row = by_frame[frame]
        queue.append({"source_frame": frame, "cel": row["cel"],
                      "source_reference": row["source_reference"], "current_source": decoded[frame],
                      "before_source_frame": earlier, "before_source": decoded[earlier],
                      "actual_delta": str(delta), "actual_delta_sha256": digest(delta),
                      "native_local_delta": str(locals_path), "native_local_delta_sha256": digest(locals_path),
                      "native_face_crop": str(face), "native_body_crop": str(body),
                      "source_exposures": row["source_exposures"],
                      "manual_source_and_delta_review": "pending", "accepted": False})
    report = {"source": manifest["source"], "mode": "strict_source",
              "sequential_decode": [0, max(wanted) + 1], "queue": queue,
              "artwork_generated": False, "exposures_changed": False, "aliases_created": False}
    queue_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"queue": str(queue_path), "missing_targets": targets,
                      "exact_source_checks": len(decoded)}))


if __name__ == "__main__":
    main()
