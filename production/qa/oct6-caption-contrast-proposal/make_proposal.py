"""Single five-frame real-glyph contrast proposal, never edits sealed inputs."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT / "qa/standing-layers-private-2026-10-05"
sys.path.insert(0, str(ROOT))
import compose
from night_transition_layers import _source_gradient

spec = importlib.util.spec_from_file_location("sealed_standing_oct6", PRIVATE / "standing_layers_private.py")
standing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(standing)

FRAMES = [1129, 1143, 1144, 1154, 1161]
SEALED_HELPER_SHA = "4a09b61c477a54bd2f4502f7184febb5eaf9fea484616690ea6d4cd1abc5e85a"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contrast_layer(frame):
    layer = {key: value.copy() if isinstance(value, np.ndarray) else value
             for key, value in standing.caption_layer(frame).items()}
    alpha = layer["alpha"].copy()
    boosted = np.zeros(alpha.shape, bool)
    if frame >= 1144:
        x0, y0, x1, y1 = map(int, layer["region"])
        # f3504's measured final kana occupies native x774..818 before +214.
        # Raise opacity only on its already-observed nonzero alpha support.
        crop = np.zeros(alpha.shape, bool)
        crop[0:38, 988-x0:1032-x0] = True
        boosted = crop & (alpha > 0) & layer["extent"]
        alpha[boosted] = np.maximum(alpha[boosted], .9)
    visible = alpha > .1
    ring = (cv2.dilate(visible.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0) & ~visible
    layer["alpha"] = alpha
    layer["contrast_ring"] = ring
    layer["boosted_existing_support"] = boosted
    return layer


def body_plate(source, generated, frame):
    old_matte, sky = standing._matte_and_sky(source, frame, source=True)
    new_matte, _ = standing._matte_and_sky(generated, frame)
    old = cv2.dilate(old_matte, np.ones((9, 9), np.uint8)) != 0
    effects = standing._warm_support(source) & ~old
    effects[950:] = False
    effects = cv2.dilate(effects.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0
    old &= ~effects
    new = new_matte != 0
    vacated = old & ~new
    plate = _source_gradient(source, sky, vacated)
    body = source.copy()
    body[vacated] = plate[vacated]
    body[new] = generated[new]
    return body


def apply_caption_contrast(body, source, frame):
    output = body.copy()
    layer = contrast_layer(frame)
    x0, y0, x1, y1 = map(int, layer["region"])
    target = output[y0:y1, x0:x1]
    original = source[y0:y1, x0:x1]
    alpha = layer["alpha"]
    ink = layer.get("ink_rgb", layer.get("foreground"))
    edited = np.any(target != original, axis=2)
    paint = (alpha > 0) & edited
    # Outline covers the complete measured glyph, including unchanged source
    # background. It is independent of underlying badge/sky luminance.
    ring = layer["contrast_ring"]
    target[ring] = (54, 45, 65)
    blended = alpha[..., None] * ink + (1-alpha[..., None]) * target
    target[paint] = np.rint(blended[paint]).clip(0, 255).astype(np.uint8)
    core = layer["core"] & paint
    target[core] = original[core]
    support = np.zeros(source.shape[:2], bool)
    support[y0:y1, x0:x1] = paint | ring
    return output, support, core, layer


def label(image, words):
    band = np.full((28, image.shape[1], 3), 245, np.uint8)
    cv2.putText(band, words, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, .48, (20, 20, 20), 1, cv2.LINE_AA)
    return np.concatenate((band, image), axis=0)


def main():
    cv2.setNumThreads(2)
    report_path = HERE / "five-frame-caption-contrast-proposal.json"
    if report_path.exists():
        raise FileExistsError("Exactly one bounded proposal run; do not overwrite it")
    assert sha(PRIVATE / "standing_layers_private.py") == SEALED_HELPER_SHA
    timeline = json.loads((PRIVATE / "timeline-private-1043-1162.json").read_text(encoding="utf-8"))
    sealed = json.loads((PRIVATE / "private-119frame-report.json").read_text(encoding="utf-8"))
    expected = {row["frame"]: row for row in sealed["frames"]}
    before = {str(path): sha(path) for path in (PRIVATE / "standing_layers_private.py",
              PRIVATE / "short-caption-f1161-real.npz", PRIVATE / "private-119frame-report.json",
              PRIVATE / "private-static-review-seal-2026-10-06.json", ROOT / "compose.py",
              ROOT / "star_gestures_layers.py", ROOT / "star_caption_alternate.py")}
    rows = []
    overview = []
    for frame in FRAMES:
        source = cv2.imread(str(PRIVATE / "source" / f"f{frame:04d}.png"))
        baseline_path = Path(expected[frame]["output_path"])
        assert sha(baseline_path) == expected[frame]["output_sha256"]
        baseline = cv2.imread(str(baseline_path))
        exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = timeline["assets"][exposure["cel"]]
        generated = compose.read_image(ROOT / asset["path"])
        body = body_plate(source, generated, frame)
        output, support, core, layer = apply_caption_contrast(body, source, frame)
        changed = np.any(output != baseline, axis=2)
        outside = int(np.count_nonzero(changed & ~support))
        assert outside == 0
        x0, y0, x1, y1 = map(int, layer["region"])
        core_errors = int(np.count_nonzero(np.any(output[y0:y1, x0:x1] != source[y0:y1, x0:x1], axis=2) & core))
        assert core_errors == 0
        path = HERE / f"f{frame:04d}-caption-only-proposal.png"
        cv2.imwrite(str(path), output)
        panel = np.concatenate((source[945:1047, 650:1250], baseline[945:1047, 650:1250],
                                output[945:1047, 650:1250]), axis=0)
        native_path = HERE / f"f{frame:04d}-native-caption-source-sealed-proposal.png"
        cv2.imwrite(str(native_path), label(panel, f"f{frame:04d}: top source / middle sealed / bottom proposal; native 1:1"))
        overview.append(label(panel, f"f{frame:04d}: source / sealed / 2px complete real-glyph outline"))
        layer_path = HERE / ("long-real-glyph-2px-contrast.npz" if frame < 1144 else "short-real-glyph-2px-contrast.npz")
        if not layer_path.exists():
            np.savez_compressed(layer_path, region=np.array(layer["region"]), alpha=layer["alpha"],
                                core=layer["core"], contrast_ring=layer["contrast_ring"],
                                ink_rgb=layer.get("ink_rgb", layer.get("foreground")),
                                boosted_existing_support=layer["boosted_existing_support"])
        rows.append({"frame": frame, "output_path": str(path), "output_sha256": sha(path),
                     "output_bgr_sha256": hashlib.sha256(output.tobytes()).hexdigest(),
                     "baseline_sha256": sha(baseline_path), "changed_pixels": int(changed.sum()),
                     "outside_caption_support_changed_pixels": outside,
                     "current_source_observed_core_exact_pixels": int(core.sum()),
                     "current_source_observed_core_errors": core_errors,
                     "boosted_existing_u_support_pixels": int(layer["boosted_existing_support"].sum()),
                     "native_evidence": str(native_path), "native_evidence_sha256": sha(native_path),
                     "layer_path": str(layer_path), "layer_sha256": sha(layer_path),
                     "accepted": False})
    page_path = HERE / "five-native-caption-source-sealed-proposal.png"
    cv2.imwrite(str(page_path), np.concatenate(overview, axis=0))
    after = {path: sha(Path(path)) for path in before}
    assert before == after
    report = {"accepted": False, "kind": "one bounded caption-only contrast proposal",
              "frames": rows, "outline_radius_pixels": 2, "outline_bgr": [54, 45, 65],
              "weak_u_policy": "Opacity floor .9 only on the already-measured real f3504 u support; no extra glyph pixels.",
              "source_observed_core_policy": "Current original-source observed core is restored exactly after blending.",
              "no_body_changes_outside_caption_support": True,
              "sealed_and_shared_files_unchanged": True, "immutable_input_sha256": before,
              "overview": str(page_path), "overview_sha256": sha(page_path),
              "native_static_review": "pending actual view", "actual_speed_review": "not performed",
              "encoded_review": "not performed"}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(report_path), "sha256": sha(report_path), "frames": len(rows), "inputs_unchanged": before == after}))


if __name__ == "__main__":
    main()
