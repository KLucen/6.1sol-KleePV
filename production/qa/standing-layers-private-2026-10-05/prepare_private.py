"""Sequential source provenance and initial native matte evidence, no art editing."""

import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import compose
import star_gestures_layers as base


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_asset(timeline, frame):
    exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
    return exposure, timeline["assets"][exposure["cel"]]


def main():
    cv2.setNumThreads(2)
    source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    timeline = json.loads((HERE / "timeline-private-1043-1162.json").read_text(encoding="utf-8"))
    source_path = Path(metadata["source"])
    assert sha(source_path) == metadata["sha256"]
    samples = {1043, 1048, 1053, 1059, 1064, 1069, 1080, 1085, 1091, 1097,
               1102, 1106, 1113, 1118, 1123, 1129, 1134, 1140, 1144, 1147, 1154, 1161}
    retained = set(range(1043, 1162)) | {3479, 3504}
    candidates = {c["start"]: c for c in source_map["candidates"]}
    capture = cv2.VideoCapture(str(source_path))
    source_records = []
    source_dir = HERE / "source"
    source_dir.mkdir(exist_ok=True)
    for frame in range(3505):
        ok, image = capture.read()
        assert ok, frame
        if frame not in retained:
            continue
        path = source_dir / f"f{frame:04d}.png"
        assert cv2.imwrite(str(path), image)
        candidate = candidates.get(frame)
        canonical_match = None
        if candidate is not None:
            canonical_match = bool(np.array_equal(image, cv2.imread(str(ROOT / candidate["reference"]))))
            assert canonical_match, frame
        record = {"frame": frame, "pts": metadata["pts"][frame], "path": str(path),
                  "sha256": sha(path), "bgr_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
                  "canonical_reference": candidate["reference"] if candidate else None,
                  "canonical_bgr_exact": canonical_match}
        if 1043 <= frame < 1162:
            exposure, asset = frame_asset(timeline, frame)
            assert np.array_equal(np.array(exposure["source_matrix"]), [[1, 0, 0], [0, 1, 0]]), frame
            record.update(asset=asset["path"], asset_source_frame=asset["source_frame"],
                          cel=exposure["cel"], exposure=[exposure["start"], exposure["end"]],
                          source_alias=asset.get("verified_source_alias"))
        source_records.append(record)
        if frame in samples:
            _, asset = frame_asset(timeline, frame)
            generated = compose.read_image(ROOT / asset["path"])
            old, sky = base._matte_and_sky(image, frame, source=True)
            new, _ = base._matte_and_sky(generated, frame)
            old_panel = image.copy()
            new_panel = generated.copy()
            old_panel[old != 0] = np.rint(old_panel[old != 0] * .55 + np.array((220, 90, 50)) * .45)
            new_panel[new != 0] = np.rint(new_panel[new != 0] * .55 + np.array((30, 160, 250)) * .45)
            cv2.imwrite(str(HERE / f"initial-f{frame:04d}-source-generated.png"), np.concatenate((image, generated), axis=1))
            cv2.imwrite(str(HERE / f"initial-f{frame:04d}-matte-pair.png"), np.concatenate((old_panel, new_panel), axis=1))
            cv2.imwrite(str(HERE / f"initial-f{frame:04d}-native-head-hands.png"), generated[60:690, 580:1320])
            cv2.imwrite(str(HERE / f"initial-f{frame:04d}-native-body.png"), generated[590:1080, 650:1260])
            record.update(initial_old_matte_pixels=int(np.count_nonzero(old)),
                          initial_new_matte_pixels=int(np.count_nonzero(new)),
                          initial_sky_pixels=int(np.count_nonzero(sky)))
        if frame in (1144, 3479, 3504):
            cv2.imwrite(str(HERE / f"donor-f{frame:04d}-native-caption.png"), image[945:1047, 350:1570])
    capture.release()
    frozen = ["compose.py", "star_gestures_layers.py", "star_caption_alternate.py",
              "night_transition_layers.py", "cyan_profile_layers.py", "cyan_caption_layers.py",
              "dance_caption_layers.py", "raised_caption_layers.py", "opening_clock_layers.py"]
    report = {"accepted": False, "source_sha256": metadata["sha256"],
              "sequentially_decoded_through": 3504, "retained_sources": source_records,
              "interval": [1043, 1162], "source_frames": 119,
              "source_map_sha256": sha(ROOT / "source_map.json"),
              "asset_selections_sha256": sha(ROOT / "asset_selections.json"),
              "source_aliases_sha256": sha(ROOT / "source_aliases.json"),
              "timeline_sha256": sha(HERE / "timeline-private-1043-1162.json"),
              "shared_code_freeze": {name: sha(ROOT / name) for name in frozen},
              "initial_matte_review": "Pending actual native inspection; initial base extraction is not proof."}
    (HERE / "source-provenance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"retained_sources": len(source_records), "interval_frames": 119,
                      "sample_matte_pairs": len(samples), "canonical_exact": True}))


if __name__ == "__main__":
    main()
