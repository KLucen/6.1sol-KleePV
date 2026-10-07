"""Prepare exact source cels and cropped identity inputs, never artwork."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta

OUT = ROOT / "qa/standing-missing-2026-10-05"
TARGETS = [1043, 1048, 1053, 1059, 1064, 1069]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    rows = manifest["cels"]
    by_frame = {row["canonical_source_frame"]: row for row in rows}
    wanted = set(TARGETS)
    before = {}
    for frame in TARGETS:
        row = by_frame[frame]
        if row["selected_asset"] is not None:
            raise ValueError(f"f{frame} already mapped; do not regenerate as missing")
        previous = rows[rows.index(row) - 1]["canonical_source_frame"]
        before[frame] = previous
        wanted.add(previous)
    capture = cv2.VideoCapture(manifest["source"])
    decoded = {}
    for frame in range(max(wanted) + 1):
        ok, bgr = capture.read()
        if not ok:
            raise ValueError(f"Source decode stopped at f{frame}")
        if frame not in wanted:
            continue
        if not np.array_equal(bgr, cv2.imread(str(ROOT / by_frame[frame]["source_reference"]))):
            raise ValueError(f"Canonical source mismatch f{frame}")
        path = OUT / f"f{frame:04d}-source-actual.png"
        cv2.imwrite(str(path), bgr)
        decoded[frame] = {"path": str(path), "png_sha256": digest(path),
                          "decoded_bgr_sha256": sha256(bgr.tobytes()).hexdigest(),
                          "canonical_reference_exact": True}
    capture.release()
    queue = []
    for frame in TARGETS:
        row = by_frame[frame]
        previous = before[frame]
        delta = OUT / f"f{previous:04d}-f{frame:04d}-source-ab-rgb-contours.png"
        make_delta(Path(decoded[previous]["path"]), Path(decoded[frame]["path"]), delta)
        bgr = cv2.imread(decoded[frame]["path"])
        face = OUT / f"f{frame:04d}-source-face-native.png"
        cv2.imwrite(str(face), bgr[80:360, 840:1145])
        limbs = OUT / f"f{frame:04d}-source-body-native.png"
        cv2.imwrite(str(limbs), bgr[340:1060, 660:1300])
        queue.append({"source_frame": frame, "cel": row["cel"],
                      "source_reference": row["source_reference"],
                      "current_source": decoded[frame], "before_source_frame": previous,
                      "before_source": decoded[previous], "actual_delta": str(delta),
                      "delta_sha256": digest(delta), "native_face_crop": str(face),
                      "native_body_crop": str(limbs), "source_exposures": row["source_exposures"],
                      "manual_source_and_delta_review": "pending", "accepted": False,
                      "alias_created": False})
    # Separate crop roles keep the previous scene's pose out of the new standing cel.
    identity = ROOT / "generated/fullpv-early-f0812-source-v1.png"
    im = Image.open(identity).convert("RGB")
    hat = im.crop((1185, 125, 1525, 405))
    coat = im.crop((1260, 345, 1600, 905))
    board = Image.new("RGB", (700, 610), "#242428")
    draw = ImageDraw.Draw(board)
    board.paste(hat, (10, 35))
    board.paste(coat, (360, 35))
    draw.text((10, 10), "IDENTITY: beret, short rooted pale hair, elf ear only", fill="white")
    draw.text((360, 10), "COSTUME: red coat, cuff, boots only", fill="white")
    identity_board = OUT / "klee-cropped-identity-costume-reference.png"
    board.save(identity_board)
    report = {"source": manifest["source"], "source_meta_sha256": digest(ROOT / "source_meta.json"),
              "mode": "strict_source", "sequential_decode": [0, max(wanted) + 1],
              "queue": queue, "identity_board": str(identity_board),
              "identity_parent": str(identity), "identity_parent_sha256": digest(identity),
              "identity_board_sha256": digest(identity_board),
              "exposures_changed": False, "artwork_generated": False}
    path = OUT / "missing-source-reference-queue.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"queue": str(path), "targets": len(queue), "source_matches": len(decoded)}))


if __name__ == "__main__":
    main()
