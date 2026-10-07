"""Audit all retained star exposures and write native caption review pages."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from compose import compose, read_image
from star_extended_layers import CHECKPOINTS, _checkpoint
from star_extended_captions import compose_with_clear_captions, _clear_short_layer


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label(image, text):
    band = np.full((27, image.shape[1], 3), 245, np.uint8)
    cv2.putText(band, text, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, .48,
                (20, 20, 20), 1, cv2.LINE_AA)
    return np.concatenate((band, image))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, nargs="+")
    args = parser.parse_args()
    cv2.setNumThreads(2)
    output_dir = HERE / "integrated-raw"
    output_dir.mkdir(exist_ok=True)
    frames = args.sample or list(range(1043, 1225))
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    records, outputs, sources, old_outputs, canonical = [], {}, {}, {}, set()
    cache, timelines = {}, {}
    for start, end, directory, name in CHECKPOINTS:
        path = ROOT / "qa" / directory / f"timeline-private-{start}-{end}.json"
        timelines[directory] = json.loads(path.read_text(encoding="utf-8"))
        canonical.update(e["start"] for e in timelines[directory]["output_exposures"])
    cap = cv2.VideoCapture(metadata["source"])
    for frame in range(max(frames) + 1):
        ok, source = cap.read()
        if not ok:
            raise RuntimeError(f"Source decode failed f{frame}")
        if frame not in frames:
            continue
        start, end, directory, name = next(c for c in CHECKPOINTS if c[0] <= frame < c[1])
        checkpoint = _checkpoint(directory, name)
        timeline = timelines[directory]
        span = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = timeline["assets"][span["cel"]]
        source_path = ROOT / "qa" / directory / "source" / f"f{frame:04d}.png"
        assert np.array_equal(source, cv2.imread(str(source_path))), f"Source mismatch f{frame}"
        assert metadata["pts"][frame] == timeline["source_pts"][frame - start], frame
        if asset["path"] not in cache:
            cache[asset["path"]] = read_image(ROOT / asset["path"])
        generated = cache[asset["path"]]
        reference = read_image(ROOT / asset["source_reference"])
        integrated, _, _ = compose(source, reference, generated, span["source_matrix"],
                                    asset["source_frame"], Path(asset["path"]).name, frame)
        expected, masks = compose_with_clear_captions(checkpoint, source, generated, frame)
        assert np.array_equal(integrated, expected), f"Renderer hook mismatch f{frame}"
        prior, prior_masks = checkpoint.compose_private(source, generated, frame, Path(asset["path"]).name)
        outside = int(np.count_nonzero(np.any(integrated != source, axis=2) & ~masks["ownership"]))
        caption_union = masks["caption"] | prior_masks["caption"]
        body_errors = int(np.count_nonzero(np.any(integrated != prior, axis=2) & ~caption_union))
        interior = cv2.erode(masks["new"], np.ones((5, 5), np.uint8)) != 0
        interior &= ~masks["caption"]
        new_errors = int(np.count_nonzero(np.any(integrated != generated, axis=2) & interior))
        assert outside == body_errors == new_errors == 0, (frame, outside, body_errors, new_errors)
        layer = _clear_short_layer() if 1144 <= frame < 1162 else checkpoint.caption_layer(frame)
        x0, y0, x1, y1 = map(int, layer["region"])
        core_errors = 0
        if frame < 1162:
            core = layer["core"] & masks["caption"][y0:y1, x0:x1]
            core_errors = int(np.count_nonzero(np.any(integrated[y0:y1, x0:x1] != source[y0:y1, x0:x1], axis=2) & core))
            assert core_errors == 0, (frame, core_errors)
        output_path = output_dir / f"f{frame:04d}-integrated.png"
        cv2.imwrite(str(output_path), integrated)
        outputs[frame], sources[frame], old_outputs[frame] = integrated, source, prior
        records.append({"frame": frame, "pts": metadata["pts"][frame], "cel": span["cel"],
                        "asset": asset["path"], "asset_sha256": sha(ROOT / asset["path"]),
                        "output": str(output_path), "output_sha256": sha(output_path),
                        "source_actual_exact": True, "renderer_hook_exact": True,
                        "outside_ownership_errors": outside, "body_vs_checkpoint_errors": body_errors,
                        "generated_interior_errors": new_errors, "observed_current_core_errors": core_errors,
                        "accepted": False})
        if frame in canonical or args.sample:
            cv2.imwrite(str(HERE / f"f{frame:04d}-integrated-whole.png"), integrated)
        print(json.dumps({"frame": frame, "outside": outside, "body": body_errors, "new": new_errors}), flush=True)
    cap.release()
    pages = []
    for offset in range(0, len(frames), 10):
        rows = []
        for frame in frames[offset:offset + 10]:
            crops = [a[945:1047, 650:1250] for a in (sources[frame], old_outputs[frame], outputs[frame])]
            rows.append(label(np.concatenate(crops, axis=1), f"f{frame} SOURCE | PRIOR | COMPLETE REAL GLYPH OUTLINE; native 1:1"))
        name = f"{'sample' if args.sample else 'all'}-caption-native-page-{offset//10+1:02d}.png"
        path = HERE / name
        cv2.imwrite(str(path), np.concatenate(rows))
        pages.append(str(path))
    name = "sample-integrated-report.json" if args.sample else "integrated-182-frame-report.json"
    report = {"interval": [1043, 1225], "frames": records, "source_frames": len(records),
              "unique_assets": len(cache), "source_cels": len(canonical), "native_caption_pages": pages,
              "raw_technical_pass": True, "accepted": False, "art_review": "pending actual native viewing",
              "encoded_review": "not performed", "original_speed_review": "not performed",
              "helper_sha256": {p: sha(ROOT / p) for p in ("compose.py", "star_extended_layers.py", "star_extended_captions.py")},
              "limitations": ["Dark outlines modify real glyph edges only; no invented glyph strokes.",
                              "Hidden background under source anatomy is an estimated source gradient.",
                              "Only source-visible stars are restored; unseen star strokes are not invented."]}
    (HERE / name).write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
