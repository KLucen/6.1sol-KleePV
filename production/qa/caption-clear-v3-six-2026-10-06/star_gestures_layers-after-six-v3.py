"""Registered own-image mattes and independent lyrics for f1008..1042.

Only vacated source anatomy receives a reconstructed sky plate. The source
outside old/new subject and registered lyric support stays pixel-identical.
"""

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from night_transition_layers import _source_gradient
from star_caption_alternate import build_authorized_phase2_layer

ROOT = Path(__file__).resolve().parent
SOURCE_INTERVAL = (1008, 1043)
CANVAS_SHAPE = (1080, 1920)
REGISTERED = {
    "candidate-033-clean.png": (1008, 1009),
    "star-gestures-f1009-fast-v1.png": (1009, 1010),
    "star-gestures-f1010-fast-v1.png": (1010, 1011),
    "candidate-034-clean.png": (1011, 1012),
    "star-gestures-f1012-fast-v1.png": (1012, 1013),
    "star-gestures-f1013-fast-v1.png": (1013, 1014),
    "star-gestures-f1014-fast-v1.png": (1014, 1017),
    "star-gestures-f1017-rear-hair-v2.png": (1017, 1019),
    "candidate-036.png": (1019, 1022),
    "candidate-037.png": (1022, 1023),
    "star-gestures-f1023-fast-v1.png": (1023, 1025),
    "star-gestures-f1025-fast-v1.png": (1025, 1028),
    "candidate-038.png": (1028, 1033),
    "star-gestures-f1033-fast-v1.png": (1033, 1037),
    "star-gestures-f1037-fast-v1.png": (1037, 1038),
    "star-gestures-f1038-fast-v1.png": (1038, 1043),
}
CAPTION_PHASES = (
    (1008, 1012, (846, 954, 1051, 1047),
     ("source_refs/src-0541-f1008.png", "source_refs/src-0544-f1011.png")),
    (1012, 1037, (886, 954, 1007, 1047),
     ("source_refs/src-0545-f1012.png", "source_refs/src-0546-f1013.png")),
    (1037, 1043, (676, 954, 1203, 1047),
     ("source_refs/src-0569-f1037.png", "source_refs/src-0570-f1038.png")),
)


def is_registered(current_frame, asset_name):
    interval = REGISTERED.get(Path(asset_name or "").name)
    return (interval is not None and current_frame is not None
            and interval[0] <= current_frame < interval[1])


def _effect_support(image, current_frame):
    effect = np.zeros(CANVAS_SHAPE, np.uint8)
    if current_frame < 1033:
        return effect
    b, g, r = cv2.split(image[110:310, 1040:1240].astype(np.int16))
    effect[110:310, 1040:1240] = (
        (b > 170) & (g > 155) & (g <= b + 3) & (r > g + 6))
    return cv2.dilate(effect, np.ones((5, 5), np.uint8))


def _matte_and_sky(image, current_frame, source=False, split_effects=True):
    if image.shape[:2] != CANVAS_SHAPE:
        raise ValueError("Star gestures require the native 1920x1080 canvas")
    value = np.max(image, axis=2)
    b, g, r = cv2.split(image.astype(np.int16))
    blue_field = (b > r + 18) & (b > g + 18) & (value >= 180)
    edges = cv2.Canny(cv2.GaussianBlur(image, (3, 3), 0), 30, 90)
    if split_effects and current_frame >= 1033:
        # The observed pink star beside the cream feather is a background
        # effect. Ignore its barrier only during ownership extraction.
        effect = _effect_support(image, current_frame) != 0
        blue_field |= effect
        edges[effect] = 0
    barrier = ((~blue_field) | (edges != 0)).astype(np.uint8)
    barrier = cv2.morphologyEx(barrier, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    _, labels, _, _ = cv2.connectedComponentsWithStats(1 - barrier, 8)
    # Cropped blue original hair is not an exterior seed at the lower edge.
    if current_frame < 1019:
        borders = (labels[0, :400], labels[:, 0])
        anchors = ((700, 600), (850, 700), (1400, 500))
    elif current_frame < 1028:
        borders = (labels[0, 1500:], labels[:, -1])
        anchors = ((400, 500), (700, 850), (1000, 450))
    else:
        borders = (labels[0], labels[:, -1])
        anchors = ((950, 550), (950, 800))
        if current_frame < 1033:
            anchors += ((30, 950),)
    exterior_ids = np.unique(np.concatenate(borders))
    exterior = np.isin(labels, exterior_ids[exterior_ids != 0])
    count, components, stats, _ = cv2.connectedComponentsWithStats(
        (~exterior).astype(np.uint8), 8)
    matte = np.zeros(CANVAS_SHAPE, np.uint8)
    for i in range(1, count):
        x, y, width, height, area = stats[i]
        anchored = any(np.any(components[max(0, ay-20):ay+20, max(0, ax-20):ax+20] == i)
                       for ax, ay in anchors)
        if area >= 7000 and width >= 40 and height >= 40 and anchored:
            matte[components == i] = 255
    if source:
        # The original detached purple long-hair lines must remain removal
        # support, including when a compression gap separates them from hair.
        matte[value < 180] = 255
    sky = exterior & blue_field
    sky &= cv2.dilate(matte, np.ones((25, 25), np.uint8)) == 0
    return matte, sky


def star_subject_mask(image, current_frame, asset_name, source=False):
    if not is_registered(current_frame, asset_name):
        return None
    return _matte_and_sky(image, current_frame, source=source)[0]


def restore_star_gestures(output, source, generated, original_subject,
                          new_subject, current_frame, asset_name):
    mask = np.zeros(source.shape[:2], np.uint8)
    if not is_registered(current_frame, asset_name):
        return output, mask
    if source.shape != generated.shape or source.shape != output.shape:
        raise ValueError("Registered star images must share native dimensions")
    # The local effect split must not alter the previously reviewed sky fit
    # or treat observed pink graphics as blue gradient evidence.
    _, sky = _matte_and_sky(source, current_frame, source=True, split_effects=False)
    old = cv2.dilate(original_subject, np.ones((9, 9), np.uint8)) != 0
    old &= _effect_support(source, current_frame) == 0
    new = new_subject != 0
    vacated = old & ~new
    plate = _source_gradient(source, sky, vacated)
    fixed = source.copy()
    fixed[vacated] = plate[vacated]
    fixed[new] = generated[new]
    mask[old | new] = 255
    return fixed, mask


def _phase(frame):
    if frame is None:
        return None
    return next((i for i, phase in enumerate(CAPTION_PHASES)
                 if phase[0] <= frame < phase[1]), None)


@lru_cache(maxsize=3)
def caption_layer(phase_index):
    _, _, region, paths = CAPTION_PHASES[phase_index]
    x0, y0, x1, y1 = region
    images = [cv2.imread(str(ROOT / path)) for path in paths]
    if any(im is None for im in images):
        raise FileNotFoundError("Missing registered star lyric donor")
    crops = [im[y0:y1, x0:x1] for im in images]
    votes = []
    for crop in crops:
        b, g, r = cv2.split(crop.astype(np.int16))
        votes.append((b >= 194) & (g >= 216) & (r >= 230)
                     & (r > b + 8) & (g > b + 5))
    rows = np.zeros(votes[0].shape, bool)
    rows[959-y0:988-y0] = True
    rows[1006-y0:1041-y0] = True
    core = votes[0] & votes[1] & rows
    count, labels, stats, _ = cv2.connectedComponentsWithStats(core.astype(np.uint8), 8)
    core = np.isin(labels, [i for i in range(1, count)
                           if stats[i, cv2.CC_STAT_AREA] >= 3])
    if np.count_nonzero(core) < 400:
        raise ValueError("Registered star lyric core is incomplete")
    b, g, r = cv2.split(crops[0].astype(np.int16))
    if phase_index < 2:
        # These two independently registered donors have cool character fill
        # under every glyph, so the complete warm outline is source-observed.
        outline = ((b >= 170) & (g >= 195) & (r >= 210)
                   & (r > b + 8) & (g > b + 5) & rows)
    else:
        original = _changed_word_layer(crops[0], region, rows, paths)
        layer = build_authorized_phase2_layer(
            original, ROOT / "layers/star-caption-f3402-authorized-v1.npz")
        clear_path = ROOT / "qa/caption-clear-v2-2026-10-06/long-f3402-cn-clear-real-caption-v2.npz"
        with np.load(clear_path) as clear:
            if tuple(map(int, clear["region"])) != tuple(layer["region"]):
                raise ValueError("Complete Chinese donor is not registered to phase 2")
            chinese_start = 1002 - y0
            for key in ("core", "extent", "alpha", "contrast_ring", "ink_rgb"):
                layer[key] = layer[key].copy()
                layer[key][chinese_start:] = clear[key][chinese_start:]
        layer.update(real_chinese_donor="source_refs/src-1905-f3402.png",
                     chinese_integer_translation=(-15, 0),
                     chinese_reconstruction="Human-authorized complete same-line original CN; independently registered to all six f1037..1042 originals. No current cuff core restoration.")
        return layer
    extent = cv2.dilate(outline.astype(np.uint8), np.ones((5, 5), np.uint8)) != 0
    donor = crops[0]
    plate = cv2.inpaint(donor, extent.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
    foreground = np.median(np.concatenate([crop[core] for crop in crops]), axis=0)
    direction = foreground - plate.astype(np.float32)
    alpha = np.clip(np.sum((donor.astype(np.float32) - plate) * direction, axis=2)
                    / np.maximum(np.sum(direction * direction, axis=2), 1), 0, 1)
    alpha[~extent | (alpha < 0.04)] = 0
    alpha[core] = 1
    visible = alpha > 0.1
    ring = (cv2.dilate(visible.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0) & ~visible
    return {"region": region, "core": core, "extent": extent,
            "alpha": alpha.astype(np.float32), "foreground": foreground,
            "contrast_ring": ring, "donors": paths,
            "reconstruction": "Registered stationary glyph cores; donor plate and AA are reconstructed"}


def _changed_word_layer(donor, region, rows, paths):
    # f1036 and f1037 retain the same source feet/cuffs. Their independently
    # changing words provide observed glyph support over otherwise warm cuffs.
    previous_path = "source_refs/src-0568-f1036.png"
    previous = cv2.imread(str(ROOT / previous_path))
    if previous is None:
        raise FileNotFoundError(previous_path)
    x0, y0, x1, y1 = region
    plate = previous[y0:y1, x0:x1].copy()
    short = caption_layer(1)
    sx0, sy0, sx1, sy1 = short["region"]
    old_words = np.zeros(plate.shape[:2], np.uint8)
    old_words[sy0-y0:sy1-y0, sx0-x0:sx1-x0] = short["extent"].astype(np.uint8)*255
    plate = cv2.inpaint(plate, old_words, 3, cv2.INPAINT_TELEA)
    observed = donor.astype(np.float32)
    baseline = plate.astype(np.float32)
    foreground = np.array((209, 224, 241), np.float32)
    direction = foreground - baseline
    change = observed - baseline
    alpha = np.clip(np.sum(change * direction, axis=2)
                    / np.maximum(np.sum(direction * direction, axis=2), 1), 0, 1)
    residual = np.max(np.abs(change - alpha[..., None]*direction), axis=2)
    b, g, r = cv2.split(donor.astype(np.int16))
    cream = (g > b + 5) & (r > b + 8) & (g > 180) & (r > 210)
    changed = np.max(np.abs(change), axis=2) > 1
    outline = rows & cream & changed & (alpha > 0.04) & (residual < 12)
    core = outline & (alpha > 0.8) & (residual < 22)
    # Actual clear corridors in this same word phase supply the part hidden
    # by the previous short word and the later moving right cuff. Neither
    # window contains the observed pale cuff fill.
    clear_windows = (
        (paths[0], (946, 959, 1038, 988)),
        ("source_refs/src-0672-f1140.png", (1102, 959, 1203, 988)),
    )
    for path, (cx0, cy0, cx1, cy1) in clear_windows:
        clear_donor = cv2.imread(str(ROOT / path))
        if clear_donor is None:
            raise FileNotFoundError(path)
        local = clear_donor[cy0:cy1, cx0:cx1]
        cb, cg, cr = cv2.split(local.astype(np.int16))
        observed_outline = ((cb >= 170) & (cg >= 195) & (cr >= 210)
                            & (cr > cb + 8) & (cg > cb + 5))
        observed_core = ((cb >= 194) & (cg >= 216) & (cr >= 230)
                         & (cr > cb + 8) & (cg > cb + 5))
        section = np.s_[cy0-y0:cy1-y0, cx0-x0:cx1-x0]
        outline[section] |= observed_outline
        core[section] |= observed_core
        alpha[section][observed_outline] = 1
    extent = cv2.dilate(outline.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0
    alpha[~extent | (alpha < 0.05)] = 0
    alpha[outline] = np.maximum(alpha[outline], 0.85)
    alpha[core] = 1
    visible = alpha > 0.1
    ring = (cv2.dilate(visible.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0) & ~visible
    return {"region": region, "core": core, "extent": extent,
            "alpha": alpha.astype(np.float32), "foreground": foreground,
            "contrast_ring": ring,
            "donors": (*paths, previous_path, clear_windows[1][0]),
            "clear_donor_windows": clear_windows,
            "reconstruction": "Actual pre/post word RGB change and registered same-word clear corridors; pale-cuff weak glyphs remain incomplete"}


def star_caption_extent(frame, shape=CANVAS_SHAPE):
    mask = np.zeros(shape, np.uint8)
    index = _phase(frame)
    if index is None:
        return mask
    if tuple(shape) != CANVAS_SHAPE:
        raise ValueError("Star captions require the native source canvas")
    layer = caption_layer(index)
    x0, y0, x1, y1 = layer["region"]
    mask[y0:y1, x0:x1][layer["extent"] | layer["contrast_ring"]] = 255
    return mask


def restore_star_captions(output, source, current_frame, asset_name,
                          character_mask=None):
    mask = np.zeros(source.shape[:2], np.uint8)
    if not is_registered(current_frame, asset_name):
        return output, mask
    if source.shape != output.shape or source.shape[:2] != CANVAS_SHAPE:
        raise ValueError("Star caption images must share native dimensions")
    layer = caption_layer(_phase(current_frame))
    x0, y0, x1, y1 = layer["region"]
    target = output[y0:y1, x0:x1]
    original = source[y0:y1, x0:x1]
    alpha = layer["alpha"]
    ink = layer.get("ink_rgb", layer["foreground"])
    edited = np.any(target != original, axis=2)
    paint = (alpha > 0) & edited
    ring = np.zeros(alpha.shape, bool)
    if character_mask is not None:
        if character_mask.shape != CANVAS_SHAPE:
            raise ValueError("Star lyric character mask must use the native canvas")
        gap = np.max(np.abs(target.astype(np.float32) - ink), axis=2)
        ring = (layer["contrast_ring"] & edited & (gap < 60)
                & (character_mask[y0:y1, x0:x1] != 0))
        target[ring] = (54, 45, 65)
    blended = alpha[..., None] * ink + (1-alpha[..., None]) * target
    target[paint] = np.clip(np.rint(blended[paint]), 0, 255).astype(np.uint8)
    target[layer["core"] & paint] = original[layer["core"] & paint]
    mask[y0:y1, x0:x1][paint | ring] = 255
    return output, mask
