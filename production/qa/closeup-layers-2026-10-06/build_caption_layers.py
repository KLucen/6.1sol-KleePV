"""Real same-line original glyphs, integer registration and estimated AA only."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def support(image, y0, chinese=False):
    b, g, r = cv2.split(image.astype(np.int16))
    rows = np.zeros(image.shape[:2], bool)
    start, end = (1006, 1041) if chinese else (959, 988)
    rows[max(0, start-y0):min(image.shape[0], end-y0)] = True
    # These inspected donors contain no cream clothing in the chosen line.
    # Their pale kana are real but have less warm chroma than the kanji.
    outline = rows & (b >= 155) & (g >= 185) & (r >= 210)
    core = rows & (b >= 194) & (g >= 215) & (r >= 230)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(outline.astype(np.uint8), 8)
    outline = np.isin(labels, [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= 3])
    return outline, core & outline


def real_line(frame, region, chinese=False):
    image = cv2.imread(str(HERE / "source" / f"f{frame:04d}.png"))
    x0, y0, x1, y1 = region
    donor = image[y0:y1, x0:x1]
    outline, core = support(donor, y0, chinese)
    extent = cv2.dilate(outline.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0
    foreground = np.median(donor[core], axis=0).astype(np.float32)
    plate = cv2.inpaint(donor, extent.astype(np.uint8)*255, 3, cv2.INPAINT_TELEA).astype(np.float32)
    direction = foreground - plate.astype(np.float32)
    alpha = np.clip(np.sum((donor.astype(np.float32)-plate)*direction, axis=2)
                    / np.maximum(np.sum(direction*direction, axis=2), 1), 0, 1)
    # A dark original shirt seam can bias the inpainted AA plate. Retain
    # only pale pixels actually observed in this clear original line.
    _, dg, dr = cv2.split(donor.astype(np.int16))
    alpha[~extent | (alpha < .04) | (dg < 180) | (dr < 208)] = 0
    alpha[outline] = np.maximum(alpha[outline], .85)
    alpha[core] = 1
    return {"region": region, "alpha": alpha.astype(np.float32), "core": core,
            "extent": extent, "foreground": foreground, "donor": donor, "frame": frame}


def find_shift(line, target_frame, target_region, chinese=False):
    target = cv2.imread(str(HERE / "source" / f"f{target_frame:04d}.png"))
    x0, y0, x1, y1 = target_region
    observed, _ = support(target[y0:y1, x0:x1], y0, chinese)
    # The original button only corrupts this known source Japanese corridor.
    test = np.ones(observed.shape, bool)
    if not chinese:
        test[:, max(0, 855-x0):max(0, 910-x0)] = False
    scores = []
    lx0, ly0, lx1, ly1 = line["region"]
    for dx in range(-125, -75):
        translated = np.zeros(observed.shape, bool)
        offset = lx0 + dx - x0
        if offset < 0 or offset + line["core"].shape[1] > translated.shape[1]:
            continue
        translated[:, offset:offset+line["core"].shape[1]] = line["core"]
        a, b = translated & test, observed & test
        score = 2*np.count_nonzero(a & b) / max(1, np.count_nonzero(a)+np.count_nonzero(b))
        scores.append((score, dx))
    score, dx = max(scores)
    return dx, score


def build(name, region, lines):
    x0, y0, x1, y1 = region
    alpha = np.zeros((y1-y0, x1-x0), np.float32)
    core = np.zeros(alpha.shape, bool)
    extent = np.zeros(alpha.shape, bool)
    ink = np.zeros((*alpha.shape, 3), np.float32)
    records = []
    for line, dx in lines:
        lx0, ly0, lx1, ly1 = line["region"]
        ox, oy = lx0 + dx - x0, ly0-y0
        section = np.s_[oy:oy+ly1-ly0, ox:ox+lx1-lx0]
        alpha[section] = line["alpha"]
        core[section] = line["core"]
        extent[section] = line["extent"]
        ink[section] = line["foreground"]
        records.append({"frame": line["frame"], "source_region": line["region"],
                        "integer_translation": [dx, 0], "destination_region": [lx0+dx, ly0, lx1+dx, ly1],
                        "core_pixels": int(line["core"].sum()), "foreground_bgr": line["foreground"].tolist(),
                        "source_sha256": sha(HERE / "source" / f"f{line['frame']:04d}.png")})
    visible = alpha > .1
    ring = (cv2.dilate(visible.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0) & ~visible
    path = HERE / f"{name}-real-caption.npz"
    np.savez_compressed(path, region=np.array(region), alpha=alpha, core=core, extent=extent,
                        contrast_ring=ring, ink_rgb=ink)
    for bg_name, color in (("purple", (231, 139, 154)), ("brown", (44, 77, 136)), ("cream", (181, 212, 246))):
        background = np.broadcast_to(np.array(color), ink.shape).copy().astype(np.float32)
        background[ring] = (54, 45, 65)
        preview = alpha[..., None]*ink + (1-alpha[..., None])*background
        cv2.imwrite(str(HERE / f"{name}-glyphs-on-{bg_name}.png"), np.rint(preview).clip(0, 255).astype(np.uint8))
    return {"path": str(path), "sha256": sha(path), "region": region, "lines": records}


def main():
    pain_jp = real_line(2420, (824, 954, 1268, 992))
    pain_cn = real_line(2420, (940, 1002, 1170, 1047), chinese=True)
    jp_dx, jp_score = find_shift(pain_jp, 1162, (720, 954, 1180, 992))
    cn_dx, cn_score = find_shift(pain_cn, 1162, (820, 1002, 1080, 1047), chinese=True)
    pain = build("pain", (710, 954, 1185, 1047), [(pain_jp, jp_dx), (pain_cn, cn_dx)])
    magic_jp = real_line(1256, (796, 954, 1100, 992))
    magic_cn = real_line(1267, (796, 1002, 1100, 1047), chinese=True)
    magic = build("magic", (796, 954, 1100, 1047), [(magic_jp, 0), (magic_cn, 0)])
    report = {"accepted": False, "authorization": "允许先重建清晰字幕，看片后再指定返工",
              "phases": [{"interval": [1162, 1217], "japanese": "痛いの痛いの飛んでいけ", "chinese": "痛痛飞走吧", **pain},
                         {"interval": [1217, 1225], "japanese": "魔法になる 合図", "chinese": "成为魔法的信号", **magic}],
              "pain_registration_dice": {"japanese": jp_score, "chinese": cn_score},
              "method": "Actual whole original line crops, integer translation only; alpha estimated from real source glyphs and donor plate, no scaling/morph/AI text/guessed strokes.",
              "native_static_review": "pending actual viewing", "actual_speed_review": "not performed"}
    (HERE / "caption-provenance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"jp_dx": jp_dx, "cn_dx": cn_dx, "jp_dice": jp_score, "cn_dice": cn_score}))


if __name__ == "__main__":
    main()
