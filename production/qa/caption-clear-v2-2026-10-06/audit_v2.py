"""Validate versioned CN repair and one native contrast proposal."""

import hashlib
import importlib.util
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
from star_extended_captions import caption_layer, compose_with_clear_captions


def load_before():
    spec = importlib.util.spec_from_file_location("_frozen_clear_before_v2", HERE / "star_extended_captions-before-v2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    return module


def label(image, text):
    band = np.full((27, image.shape[1], 3), 245, np.uint8)
    cv2.putText(band, text, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, .48, (20, 20, 20), 1, cv2.LINE_AA)
    return np.concatenate((band, image))


def halo_proposal(image, source, layer):
    result = image.copy()
    x0, y0, x1, y1 = map(int, layer["region"])
    target = result[y0:y1, x0:x1]
    alpha = layer["alpha"]
    visible = alpha > .1
    ring4 = (cv2.dilate(visible.astype(np.uint8), np.ones((9, 9), np.uint8)) != 0) & ~visible
    target[ring4] = (54, 45, 65)
    ink = layer.get("ink_rgb", layer.get("foreground"))
    blended = alpha[..., None] * ink + (1 - alpha[..., None]) * target
    paint = alpha > 0
    target[paint] = np.rint(blended[paint]).clip(0, 255).astype(np.uint8)
    core = layer["core"] & paint
    target[core] = source[y0:y1, x0:x1][core]
    return result


def main():
    cv2.setNumThreads(2)
    output_dir = HERE / "v2-raw"
    output_dir.mkdir(exist_ok=True)
    before = load_before()
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    timelines = {}
    for start, end, directory, name in CHECKPOINTS:
        timelines[directory] = json.loads((ROOT / "qa" / directory / f"timeline-private-{start}-{end}.json").read_text(encoding="utf-8"))
    records, rows, pages, cache = [], [], [], {}
    cap = cv2.VideoCapture(metadata["source"])
    for frame in range(1225):
        ok, source = cap.read()
        if not ok:
            raise RuntimeError(frame)
        if frame < 1043:
            continue
        start, end, directory, name = next(c for c in CHECKPOINTS if c[0] <= frame < c[1])
        checkpoint = _checkpoint(directory, name)
        timeline = timelines[directory]
        span = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = timeline["assets"][span["cel"]]
        if asset["path"] not in cache:
            cache[asset["path"]] = read_image(ROOT / asset["path"])
        generated = cache[asset["path"]]
        reference = read_image(ROOT / asset["source_reference"])
        current, masks = compose_with_clear_captions(checkpoint, source, generated, frame)
        prior, prior_masks = before.compose_with_clear_captions(checkpoint, source, generated, frame)
        actual, _, _ = compose(source, reference, generated, span["source_matrix"], asset["source_frame"], Path(asset["path"]).name, frame)
        assert np.array_equal(current, actual), ("hook", frame)
        assert metadata["pts"][frame] == timeline["source_pts"][frame - start]
        different = np.any(current != prior, axis=2)
        outside = np.count_nonzero(np.any(current != source, axis=2) & ~masks["ownership"])
        body = np.count_nonzero(different & ~(masks["caption"] | prior_masks["caption"]))
        assert outside == body == 0, (frame, outside, body)
        if frame < 1144:
            assert not different[:1002].any(), ("JP-or-body-regression", frame)
        else:
            assert not different.any(), ("out-of-CN-scope-regression", frame)
        layer = caption_layer(checkpoint, frame)
        x0, y0, x1, y1 = map(int, layer["region"])
        if frame < 1144:
            assert not layer["core"][1002-y0:].any(), "Corrupt old cuff must not be restored as a glyph"
        path = output_dir / f"f{frame:04d}-v2.png"
        cv2.imwrite(str(path), current)
        records.append({"frame": frame, "changed_pixels": int(different.sum()),
                        "outside_ownership_errors": int(outside), "body_vs_v1_errors": int(body),
                        "japanese_unchanged": True, "renderer_hook_exact": True,
                        "output": str(path), "accepted": False})
        if frame < 1144:
            crops = [image[945:1047, 650:1250] for image in (source, prior, current)]
            rows.append(label(np.concatenate(crops, axis=1), f"f{frame} ORIGINAL | V1 | V2 COMPLETE ORIGINAL CN; native 1:1"))
            if len(rows) == 10 or frame == 1143:
                path = HERE / f"cn-v2-native-page-{len(pages)+1:02d}.png"
                cv2.imwrite(str(path), np.concatenate(rows))
                pages.append(str(path))
                rows = []
        if frame in (1129, 1144, 1154):
            proposed = halo_proposal(current, source, layer)
            image = np.concatenate([a[945:1047, 650:1250] for a in (prior, current, proposed)], axis=1)
            cv2.imwrite(str(HERE / f"f{frame}-single-4px-halo-proposal-native.png"), label(image, f"f{frame} V1 | V2 CN ONLY | SINGLE 4px HALO PROPOSAL (not adopted); native 1:1"))
        print(json.dumps({"frame": frame, "changed": int(different.sum()), "body": int(body)}), flush=True)
    cap.release()
    report = {"interval": [1043, 1225], "frames": records, "raw_technical_pass": True,
              "changed_scope": [1043, 1144], "native_cn_pages": pages,
              "accepted": False, "native_visual_review": "pending actual viewing",
              "encoded_and_actual_speed_review": "not performed",
              "shared_helper_sha256": hashlib.sha256((ROOT / "star_extended_captions.py").read_bytes()).hexdigest(),
              "contrast_proposal": "One 4px outline native proposal only, not adopted. No threshold search or guessed strokes."}
    (HERE / "v2-182-frame-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"frames": len(records), "technical_pass": True, "pages": len(pages)}))


if __name__ == "__main__":
    main()
