"""Real f3504 Japanese prefix and same-phase f1161 Chinese, estimated alpha."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
REGION = (850, 954, 1040, 1047)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = cv2.imread(str(HERE / "source/f1161.png"))
    x0, y0, x1, y1 = REGION
    donor = source[y0:y1, x0:x1]
    b, g, r = cv2.split(donor.astype(np.int16))
    rows = np.zeros(donor.shape[:2], bool)
    rows[959-y0:988-y0] = True
    rows[1006-y0:1041-y0] = True
    outline = rows & (b >= 170) & (g >= 195) & (r >= 210) & (r > b + 8) & (g > b + 5)
    core = rows & (b >= 194) & (g >= 216) & (r >= 230) & (r > b + 8) & (g > b + 5)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(outline.astype(np.uint8), 8)
    outline = np.isin(labels, [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 3])
    core &= outline
    assert int(core[:38].sum()) > 300
    assert int(core[38:].sum()) > 700
    extent = cv2.dilate(outline.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0
    plate = cv2.inpaint(donor, extent.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
    foreground = np.median(donor[core], axis=0).astype(np.float32)
    direction = foreground - plate.astype(np.float32)
    alpha = np.clip(np.sum((donor.astype(np.float32) - plate) * direction, axis=2)
                    / np.maximum(np.sum(direction * direction, axis=2), 1), 0, 1)
    alpha[~extent | (alpha < .04)] = 0
    alpha[outline] = np.maximum(alpha[outline], .85)
    alpha[core] = 1
    japanese_source = cv2.imread(str(HERE / "source/f3504.png"))
    japanese_region = (650, 954, 820, 992)
    jx0, jy0, jx1, jy1 = japanese_region
    japanese = japanese_source[jy0:jy1, jx0:jx1]
    jb, jg, jr = cv2.split(japanese.astype(np.int16))
    jrows = np.zeros(japanese.shape[:2], bool)
    jrows[959-jy0:988-jy0] = True
    joutline = jrows & (jb >= 170) & (jg >= 195) & (jr >= 210) & (jr > jb + 8) & (jg > jb + 5)
    jcore = jrows & (jb >= 194) & (jg >= 216) & (jr >= 230) & (jr > jb + 8) & (jg > jb + 5)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(joutline.astype(np.uint8), 8)
    joutline = np.isin(labels, [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 3])
    jextent = cv2.dilate(joutline.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0
    jplate = cv2.inpaint(japanese, jextent.astype(np.uint8)*255, 3, cv2.INPAINT_TELEA)
    jforeground = np.median(japanese[jcore], axis=0).astype(np.float32)
    jdirection = jforeground - jplate.astype(np.float32)
    jalpha = np.clip(np.sum((japanese.astype(np.float32)-jplate)*jdirection, axis=2)
                     / np.maximum(np.sum(jdirection*jdirection, axis=2), 1), 0, 1)
    jalpha[~jextent | (jalpha < .04)] = 0
    jalpha[joutline] = np.maximum(jalpha[joutline], .85)
    jalpha[jcore] = 1
    # The real final kana has lower decoded cream values over a uniform coat.
    # Measure its alpha against that local observed plate instead of raising
    # an absolute cream threshold or inventing a missing stroke.
    u = japanese[:, 124:168].astype(np.float32)
    yy, xx = np.indices(u.shape[:2], dtype=np.float32)
    design = np.stack((np.ones_like(xx), xx, yy), axis=2)
    background = u[..., 1] <= np.percentile(u[..., 1], 60)
    coefficients = np.linalg.lstsq(design[background], u[background], rcond=None)[0]
    uplate = design @ coefficients
    udirection = jforeground - uplate
    ualpha = np.clip(np.sum((u-uplate)*udirection, axis=2)
                     / np.maximum(np.sum(udirection*udirection, axis=2), 1), 0, 1)
    residual = np.max(np.abs(u - (uplate + ualpha[..., None]*udirection)), axis=2)
    usupport = jrows[:, 124:168] & (ualpha > .08) & (residual < 12)
    ualpha[~usupport] = 0
    jalpha[:, 124:168] = ualpha
    jextent[:, 124:168] = usupport
    alpha[:38] = 0
    core[:38] = False
    extent[:38] = False
    destination_x = 650 + 214
    offset = destination_x - x0
    alpha[:38, offset:offset+170] = jalpha
    extent[:38, offset:offset+170] = jextent
    japanese_donor_core = np.zeros(alpha.shape, bool)
    japanese_donor_core[:38, offset:offset+170] = jcore
    visible = alpha > .1
    ring = (cv2.dilate(visible.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0) & ~visible
    path = HERE / "short-caption-f1161-real.npz"
    np.savez_compressed(path, region=np.array(REGION), alpha=alpha.astype(np.float32),
                        core=core, extent=extent, contrast_ring=ring, foreground=foreground,
                        japanese_donor_core=japanese_donor_core)
    cv2.imwrite(str(HERE / "short-f1161-native-observed.png"), donor)
    cv2.imwrite(str(HERE / "short-f1161-observed-diagnostic-4x.png"), cv2.resize(donor, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST))
    cv2.imwrite(str(HERE / "short-f1161-support-diagnostic-4x.png"), cv2.resize(outline.astype(np.uint8)*255, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST))
    for name, color in (("purple", (231, 139, 154)), ("brown", (44, 77, 136)), ("cream", (181, 212, 246))):
        target = np.broadcast_to(np.array(color), donor.shape).copy().astype(np.float32)
        ring_target = target.copy()
        ring_target[ring] = (54, 45, 65)
        preview = alpha[..., None] * foreground + (1-alpha[..., None]) * ring_target
        cv2.imwrite(str(HERE / f"short-f1161-real-glyphs-on-{name}.png"), np.rint(preview).clip(0, 255).astype(np.uint8))
    report = {"accepted": False, "authorization": "允许先重建清晰字幕，看片后再指定返工",
              "chinese_source_frame": 1161, "source_path": str(HERE / "source/f1161.png"),
              "source_sha256": sha(HERE / "source/f1161.png"),
              "japanese_source_frame": 3504, "japanese_source_path": str(HERE / "source/f3504.png"),
              "japanese_source_sha256": sha(HERE / "source/f3504.png"),
              "japanese_donor_region": japanese_region,
              "japanese_destination_region": (864, 954, 1034, 992),
              "region": REGION, "chinese_translation": [0, 0], "japanese_translation": [214, 0],
              "interval": [1144, 1162], "japanese": "分け合う", "chinese": "彼此分担",
              "donor_status": "Actual f3504 original Japanese prefix and same-phase f1161 Chinese; sequential native decode exact",
              "core_pixels_japanese": int(japanese_donor_core.sum()), "core_pixels_chinese": int(core[38:].sum()),
              "visible_alpha_pixels": int(visible.sum()), "foreground_bgr": foreground.tolist(),
              "npz_sha256": sha(path),
              "outline_policy": "Observed warm outline support receives minimum .85 opacity; no shape growth or guessed pixels.",
              "limitations": ["Donor plate and antialias alpha are estimated, not recovered invisible f1144 pant strokes.",
                              "Only original real glyph pixels determine shape; no AI lettering or guessed strokes.",
                              "Native static and original-speed acceptance remain pending."]}
    (HERE / "short-caption-provenance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"japanese_core": int(japanese_donor_core.sum()), "chinese_core": int(core[38:].sum()),
                      "sha256": sha(path)}))


if __name__ == "__main__":
    main()
