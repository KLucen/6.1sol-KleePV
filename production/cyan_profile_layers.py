"""Source-backed silhouettes and vacated-sky repair for registered cyan cels."""

from pathlib import Path

import cv2
import numpy as np

from night_transition_layers import _source_gradient

SOURCE_INTERVAL = (911, 1008)
REGISTERED = {
    "candidate-031-clean.png": (911, 914),
    "fine-f0914.png": (914, 915),
    "fine-f0915.png": (915, 919),
    "fine-f0919.png": (919, 921),
    "fine-f0921.png": (921, 925),
    "fine-f0925.png": (925, 927),
    "fine-f0927.png": (927, 931),
    "fine-f0931.png": (931, 933),
    "fine-f0933.png": (933, 935),
    "fine-f0935-repair.png": (935, 938),
    "fast-fullpv-cyan-f0938-position-v2.png": (938, 939),
    "fine-f0939.png": (939, 942),
    "fast-fullpv-cyan-f0942-v1.png": (942, 945),
    "fine-f0945.png": (945, 948),
    "fast-fullpv-cyan-f0948-v1.png": (948, 951),
    "fine-f0951.png": (951, 954),
    "fast-fullpv-cyan-f0954-v1.png": (954, 957),
    "fast-fullpv-cyan-f0957-v1.png": (957, 960),
    "fast-fullpv-cyan-f0960-v1.png": (960, 963),
    "fast-fullpv-cyan-f0963-v1.png": (963, 965),
    "fast-fullpv-cyan-f0965-v1.png": (965, 967),
    "fast-fullpv-cyan-f0967-v1.png": (967, 969),
    "fast-fullpv-cyan-f0969-v1.png": (969, 973),
    "fast-fullpv-cyan-f0973-v1.png": (973, 975),
    "fast-fullpv-cyan-f0975-hair-v2.png": (975, 980),
    "fast-fullpv-cyan-f0980-v1.png": (980, 981),
    "fast-fullpv-cyan-f0981-nod-v2.png": (981, 984),
    "fast-fullpv-cyan-f0984-v1.png": (984, 987),
    "fast-fullpv-cyan-f0987-v1.png": (987, 992),
    "fast-fullpv-cyan-f0992-v1.png": (992, 993),
    "fast-fullpv-cyan-f0993-v1.png": (993, 997),
    "fast-fullpv-cyan-f0997-v1.png": (997, 998),
    "fast-fullpv-cyan-f0998-v1.png": (998, 1002),
    "fast-fullpv-cyan-f1002-v1.png": (1002, 1003),
    "fast-fullpv-cyan-f1003-v1.png": (1003, 1006),
    "candidate-032-clean.png": (1006, 1008),
}
GENERATED_GRAPHICS_REGIONS = {
    "fast-fullpv-cyan-f0967-v1.png": (600, 945, 655, 1000),
}


def is_registered(current_frame, asset_name):
    interval = REGISTERED.get(Path(asset_name or "").name)
    return (interval is not None and current_frame is not None
            and interval[0] <= current_frame < interval[1])


def _generated_graphics_mask(image, asset_name):
    mask = np.zeros(image.shape[:2], np.uint8)
    region = GENERATED_GRAPHICS_REGIONS.get(Path(asset_name or "").name)
    if region is None:
        return mask
    x0, y0, x1, y1 = region
    _, saturation, value = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
    candidate = ((saturation[y0:y1, x0:x1] < 130)
                 & (value[y0:y1, x0:x1] > 190)).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, 8)
    for i in range(1, count):
        x, y, width, height, area = stats[i]
        # These detached coat-edge marks are generated stars, including their AA.
        if (3 <= area <= 150 and width <= 16 and height <= 20
                and x > 0 and y > 0 and x+width < x1-x0 and y+height < y1-y0):
            mask[y0:y1, x0:x1][labels == i] = 255
    fringe = ((cv2.dilate(mask, np.ones((5, 5), np.uint8)) != 0)
              & (saturation < 160) & (value > 190))
    mask[fringe] = 255
    return mask


def _matte_and_sky(image, source=False, asset_name=None):
    h, s, v = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
    # Actual cyan-shot sky is more saturated than the lavender anatomy fill.
    sky_saturation = 110 if source else 160
    sky_color = (h >= 95) & (h <= 145) & (s >= sky_saturation) & (v >= 200)
    line_gap = 17 if source else 5
    barrier = cv2.morphologyEx((~sky_color).astype(np.uint8), cv2.MORPH_CLOSE,
                              np.ones((line_gap, line_gap), np.uint8))
    _, labels, _, _ = cv2.connectedComponentsWithStats(1-barrier, 8)
    # Original long hair is cropped at the bottom. Its blue shaded fill must
    # not seed the exterior-sky flood from that canvas edge.
    borders = (labels[0], labels[:, -1]) if source else (labels[0], labels[-1], labels[:, -1])
    border = np.unique(np.concatenate(borders))
    exterior = np.isin(labels, border[border != 0])
    count, components, stats, _ = cv2.connectedComponentsWithStats((~exterior).astype(np.uint8), 8)
    matte = np.zeros(image.shape[:2], np.uint8)
    anchor = np.zeros(image.shape[:2], bool)
    anchor[150:1000, 850:1500] = True
    warm = (h < 22) & (s > 35) & (v > 60)
    for i in range(1, count):
        x, y, width, height, area = stats[i]
        if area < 8000 or width < 60 or height < 60:
            continue
        component = components == i
        main = np.count_nonzero(component & anchor) >= 8000
        cropped_foreground = x == 0 and y+height == image.shape[0] and np.count_nonzero(component & warm) >= 1000
        if main or cropped_foreground:
            matte[component] = 255
    if source:
        # All observed sky in this registered shot is bright. Detached dark
        # hair/neck strokes are source anatomy, even across a compressed gap.
        matte[v < 180] = 255
        matte[(h >= 45) & (h <= 95) & (s >= 100) & (v < 210)] = 255
    # Enclosed blue gaps between hair groups are visible sky, not opaque cels.
    # This excludes vivid bright sky, while pale cyan anatomy and dark ink stay.
    visible_gap = (h >= 95) & (h <= 145) & (s >= 160) & (v >= 200)
    matte[visible_gap] = 0
    if not source:
        matte[_generated_graphics_mask(image, asset_name) != 0] = 0
        # Closing the silhouette can catch isolated generated star pixels near
        # a coat edge. Only detached tiny bright islands are excluded.
        count, islands, stats, _ = cv2.connectedComponentsWithStats(matte, 8)
        for i in range(1, count):
            if stats[i, cv2.CC_STAT_AREA] > 150:
                continue
            island = islands == i
            if np.all((s[island] < 80) & (v[island] > 220)):
                matte[island] = 0
    sky = exterior & sky_color & (cv2.dilate(matte, np.ones((25, 25), np.uint8)) == 0)
    return matte, sky


def cyan_subject_mask(image, current_frame, asset_name, source=False):
    if not is_registered(current_frame, asset_name):
        return None
    if image.shape[:2] != (1080, 1920):
        raise ValueError("Cyan silhouettes require the native source canvas")
    return _matte_and_sky(image, source=source, asset_name=asset_name)[0]


def restore_cyan_profile(output, source, generated, original_subject,
                         new_subject, current_frame, asset_name):
    mask = np.zeros(source.shape[:2], np.uint8)
    if not is_registered(current_frame, asset_name):
        return output, mask
    if source.shape != generated.shape or source.shape != output.shape:
        raise ValueError("Registered cyan images must share native dimensions")
    _, sky = _matte_and_sky(source, source=True)
    old = cv2.dilate(original_subject, np.ones((17, 17), np.uint8)) != 0
    new = new_subject != 0
    support = old | new
    vacated = old & ~new
    plate = _source_gradient(source, sky, vacated)
    fixed = source.copy()
    fixed[vacated] = plate[vacated]
    fixed[new] = generated[new]
    mask[support] = 255
    return fixed, mask
