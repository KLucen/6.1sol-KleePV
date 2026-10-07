"""Native original caption comparison; no generated character manipulation."""

import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import star_gestures_layers


def main():
    source = cv2.imread(str(ROOT / "source_refs/src-1905-f3402.png"))
    target = cv2.imread(str(ROOT / "source_refs/src-0569-f1037.png"))
    assert source.shape == target.shape == (1080, 1920, 3)
    layer = star_gestures_layers.caption_layer(2)
    np.savez_compressed(HERE / "long-combined-before-v2.npz", **{
        k: v for k, v in layer.items() if isinstance(v, np.ndarray)})
    for frame, image in ((3402, source), (1037, target)):
        cv2.imwrite(str(HERE / f"f{frame}-cn-native.png"), image[1002:1047, 660:1240])
        cv2.imwrite(str(HERE / f"f{frame}-both-native.png"), image[950:1047, 660:1240])
    x0, y0, x1, y1 = map(int, layer["region"])
    ink = layer["ink_rgb"]
    rendered = layer["alpha"][..., None] * ink
    cv2.imwrite(str(HERE / "before-long-glyphs-native.png"), np.rint(rendered).astype(np.uint8))
    colors = {
        "source_cn": source[1002:1047, 660:1240],
        "target_cn": target[1002:1047, 660:1240],
    }
    votes = {}
    for name, image in colors.items():
        b, g, r = cv2.split(image.astype(np.int16))
        core = (b >= 194) & (g >= 215) & (r >= 230)
        votes[name] = core
        cv2.imwrite(str(HERE / f"{name}-core.png"), core.astype(np.uint8) * 255)
    scores = []
    for dx in range(-60, 1):
        shifted = np.zeros(votes["source_cn"].shape, bool)
        if dx:
            shifted[:, :dx] = votes["source_cn"][:, -dx:]
        else:
            shifted[:] = votes["source_cn"]
        observed = votes["target_cn"]
        # The left phrase is clear in the target; the center boot fill is not
        # reliable registration evidence.
        window = np.zeros(observed.shape, bool)
        window[:, :180] = True
        a, b = shifted & window, observed & window
        score = 2 * np.count_nonzero(a & b) / max(1, a.sum() + b.sum())
        scores.append({"dx": dx, "dice_left_clear_phrase": float(score)})
    scores.sort(key=lambda entry: entry["dice_left_clear_phrase"], reverse=True)
    (HERE / "registration-candidates.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    frozen = {}
    for path in HERE.glob("*before-v2.*"):
        frozen[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (HERE / "baseline-freeze.json").write_text(json.dumps(frozen, indent=2), encoding="utf-8")
    print(json.dumps({"region": layer["region"], "registration_top": scores[:6], "frozen": frozen}))


if __name__ == "__main__":
    main()
