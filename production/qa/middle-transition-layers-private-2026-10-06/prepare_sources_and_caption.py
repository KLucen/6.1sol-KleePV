"""Freeze actual sequential frames and reconstruct only real original lyric ink."""

import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE / "source"


def load_builder():
    path = ROOT / "qa/closeup-layers-2026-10-06/build_caption_layers.py"
    spec = importlib.util.spec_from_file_location("middle_real_glyph_builder", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.HERE = HERE
    module.support = donor_support
    return module


def donor_support(image, y0, chinese=False):
    b, g, r = cv2.split(image.astype(np.int16))
    rows = np.zeros(image.shape[:2], bool)
    start, end = (1006, 1041) if chinese else (959, 989)
    rows[max(0, start-y0):min(image.shape[0], end-y0)] = True
    # Actual f2141 pink plate samples are BGR ~166,182,228. The prior
    # closeup threshold g>=185 admitted this compressed pink background.
    outline = rows & (b >= 180) & (g >= 201) & (r >= 237)
    core = rows & (b >= 198) & (g >= 216) & (r >= (241 if chinese else 245))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(outline.astype(np.uint8), 8)
    outline = np.isin(labels, [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 3])
    return outline, core & outline


def actual_shift(line, image):
    foreground = line["foreground"]
    observed = np.max(np.abs(image.astype(np.float32) - foreground), axis=2) < 16
    x0, y0, x1, y1 = line["region"]
    points_y, points_x = np.nonzero(line["core"])
    scores = []
    for dy in range(-3, 4):
        for dx in range(-12, 13):
            values = observed[points_y + y0 + dy, points_x + x0 + dx]
            scores.append((float(np.mean(values)), -abs(dx) - abs(dy), dx, dy))
    score, _, dx, dy = max(scores)
    identity = next(item[0] for item in scores if item[2:] == (0, 0))
    # A one-pixel winner on compressed/occluded kana is not source movement.
    # Prefer the stable native coordinate when its evidence differs by <= 1.2%.
    chosen = [0, 0] if score - identity <= .012 else [dx, dy]
    return {"integer_translation": chosen, "observed_real_core_match": identity,
            "noisy_best_translation": [dx, dy], "noisy_best_match": score,
            "best_over_identity_difference": score - identity,
            "identity_noise_tolerance": .012}


def main():
    SOURCE.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    cap = cv2.VideoCapture(metadata["source"])
    for frame in range(2145):
        if frame < 2121:
            if not cap.grab():
                raise ValueError(f"Source ended at {frame}")
            continue
        ok, image = cap.read()
        if not ok:
            raise ValueError(f"Source ended at {frame}")
        cv2.imwrite(str(SOURCE / f"f{frame:04d}.png"), image)
    cap.release()
    builder = load_builder()
    donor = cv2.imread(str(SOURCE / "f2141.png"))
    cv2.imwrite(str(HERE / "f2141-japanese-donor-native.png"), donor[950:995, 695:1225])
    cv2.imwrite(str(HERE / "f2141-chinese-donor-native.png"), donor[998:1052, 695:1225])
    jp = builder.real_line(2141, (700, 954, 1220, 994))
    cn = builder.real_line(2141, (744, 1002, 1176, 1047), chinese=True)
    registration = {}
    for frame in range(2121, 2145):
        image = cv2.imread(str(SOURCE / f"f{frame:04d}.png"))
        registration[str(frame)] = {"japanese": actual_shift(jp, image),
                                    "chinese": actual_shift(cn, image)}
    if any(record[line]["integer_translation"] != [0, 0]
           for record in registration.values() for line in ("japanese", "chinese")):
        raise ValueError(f"Current caption registration needs a per-frame translated layer: {registration}")
    layer = builder.build("middle-same-line-f2141", (695, 950, 1225, 1052), [(jp, 0), (cn, 0)])
    report = {
        "accepted": False,
        "authorization": "User allows clear same-line original glyph reconstruction with original wording, position and timing, and minor glyph differences.",
        "source_interval": [2121, 2145],
        "japanese": "\u30db\u30f3\u30c8\u306f\u3053\u306e\u307e\u307e\u611b\u3057\u3066\u305f\u3044",
        "chinese": "\u5176\u5b9e\u662f\u60f3\u5c31\u8fd9\u6837\u7231\u4e0b\u53bb",
        "layer": layer,
        "registration": registration,
        "method": "Imported real_line/build only with private HERE. JP and CN independently checked against each actual target; integer translation only. Alpha estimated from real donor ink and an inpainted donor plate. No AI text, guessed strokes, scale, or warp.",
        "donor_actual_static_view": "Root and this agent viewed full f2141 source before extraction; native extracted glyph preview still requires actual view.",
        "actual_speed_review": "not performed"
    }
    (HERE / "caption-provenance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"layer": layer, "registration": registration}, indent=2))


if __name__ == "__main__":
    main()
