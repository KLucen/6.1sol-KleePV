"""Registered matte repair for the dance-to-night exposures.

The sky under vacated source anatomy is reconstructed from visible pixels of
the current source frame. It is not a clean donor or generated background.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

REGISTERED = {
    "fast-fullpv-dance-f0900-rearhat-v2.png": (900, 902),
    "candidate-029-clean.png": (902, 903),
    "fast-fullpv-dance-f0903-v1.png": (903, 905),
    "candidate-030-clean.png": (905, 907),
    "fast-fullpv-dance-f0907-source-v2.png": (907, 908),
    "fast-fullpv-dance-f0908-v1.png": (908, 909),
    "fast-fullpv-dance-f0909-v1.png": (909, 911),
}
BACKVIEW_ASSET = "fast-fullpv-dance-f0900-rearhat-v2.png"
BACKVIEW_ROI = (1125, 0, 1490, 285)


def _is_backview(current_frame, asset_name):
    return (Path(asset_name or "").name == BACKVIEW_ASSET
            and current_frame is not None and 900 <= current_frame < 902)


def _backview_area(shape):
    area = np.zeros(shape[:2], bool)
    x0, y0, x1, y1 = BACKVIEW_ROI
    area[y0:y1, x0:x1] = True
    return area


def is_registered(current_frame, asset_name):
    interval = REGISTERED.get(Path(asset_name or "").name)
    return (interval is not None and current_frame is not None
            and interval[0] <= current_frame < interval[1])


def _sky_candidate(image):
    h, s, v = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
    cyan = (h >= 97) & (h <= 145) & (s >= 160) & (v >= 215)
    purple = (h >= 116) & (h <= 135) & (s >= 70) & (v >= 233)
    return cyan | purple


def _matte_and_sky(image):
    # Close small line gaps before the border flood, not the character's shape.
    barrier = (~_sky_candidate(image)).astype(np.uint8)
    barrier = cv2.morphologyEx(barrier, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(1 - barrier, 8)
    border = np.unique(np.concatenate((labels[0], labels[-1], labels[:, -1])))
    exterior = np.isin(labels, border[border != 0])
    count, components, stats, _ = cv2.connectedComponentsWithStats(
        (~exterior).astype(np.uint8), 8)
    matte = np.zeros(image.shape[:2], np.uint8)
    for i in range(1, count):
        x, y, width, height, area = stats[i]
        if area >= 8000 and width >= 60 and height >= 60:
            matte[components == i] = 255
    # Stars and the moon are small isolated non-sky components, not anatomy.
    sky = exterior & _sky_candidate(image)
    sky &= cv2.dilate(matte, np.ones((25, 25), np.uint8)) == 0
    return matte, sky


def night_subject_mask(image, current_frame, asset_name, existing_mask=None):
    """Return this image's own silhouette, or None outside the registration."""
    if not is_registered(current_frame, asset_name):
        return None
    if _is_backview(current_frame, asset_name):
        if existing_mask is None:
            raise ValueError("Back-view registration requires its existing generic matte")
        result = existing_mask.copy()
        area = _backview_area(image.shape)
        own = _matte_and_sky(image)[0]
        result[area] = own[area]
        return result
    return _matte_and_sky(image)[0]


def _basis(x, y, degree=4):
    return np.stack([x ** i * y ** j for i in range(degree + 1)
                     for j in range(degree + 1 - i)], axis=1)


def _source_gradient(source, sky, target):
    """Smooth current-source gradient with locally sourced boundary residuals."""
    height, width = sky.shape
    grid = np.zeros_like(sky)
    grid[::8, ::8] = True
    yy, xx = np.nonzero(sky & grid)
    if len(xx) < 400:
        raise ValueError("Registered night frame lacks source sky evidence")
    design = _basis(xx / (width - 1) * 2 - 1, yy / (height - 1) * 2 - 1)
    values = source[yy, xx].astype(np.float64)
    keep = np.ones(len(xx), bool)
    for _ in range(3):
        coefficients = np.linalg.lstsq(design[keep], values[keep], rcond=None)[0]
        error = np.max(np.abs(design @ coefficients - values), axis=1)
        keep = error < max(4.0, float(np.percentile(error, 93)))
    ty, tx = np.nonzero(target)
    target_design = _basis(tx / (width - 1) * 2 - 1, ty / (height - 1) * 2 - 1)
    prediction = target_design @ coefficients

    # Nearest measured sky residual anchors the extrapolation to the visible
    # source boundary; only the invisible target is replaced, never the sky.
    _, nearest_labels = cv2.distanceTransformWithLabels(
        (~sky).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    sy, sx = np.nonzero(sky)
    measured = source[sy, sx].astype(np.float64)
    measured_prediction = _basis(sx / (width - 1) * 2 - 1,
                                sy / (height - 1) * 2 - 1) @ coefficients
    residual_table = np.zeros((len(sx) + 1, 3), np.float32)
    residual_table[nearest_labels[sy, sx]] = measured - measured_prediction
    residual = residual_table[nearest_labels]
    residual = cv2.GaussianBlur(residual, (31, 31), 8)
    prediction += residual[ty, tx]
    lower = np.percentile(values[keep], 0.2, axis=0) - 4
    upper = np.percentile(values[keep], 99.8, axis=0) + 4
    colors = np.rint(np.clip(prediction, lower, upper)).clip(0, 255).astype(np.uint8)
    plate = source.copy()
    plate[ty, tx] = colors
    return plate


def restore_night_transition(output, source, generated, original_subject,
                             new_subject, current_frame, asset_name=None):
    """Replace registered anatomy, reconstruct only its vacated source support.

    Call before captions. The returned mask includes restoration of previous
    generic-matte mistakes and is a diagnostic support, not acceptance proof.
    """
    if not is_registered(current_frame, asset_name):
        return output, np.zeros(source.shape[:2], np.uint8)
    if source.shape != generated.shape or source.shape != output.shape:
        raise ValueError("Registered night images must share native dimensions")
    source_matte, sky = _matte_and_sky(source)
    generated_matte, _ = _matte_and_sky(generated)
    if _is_backview(current_frame, asset_name):
        area = _backview_area(source.shape)
        old = (cv2.dilate(source_matte, np.ones((17, 17), np.uint8)) != 0) & area
        new = (generated_matte != 0) & area
        repair = area & (old | new | (original_subject != 0) | (new_subject != 0))
        vacated = old & ~new
        # Only actual neighboring source sky supports this small top-right
        # reconstruction. The frame's unrelated left purple field is excluded.
        local_sky = np.zeros_like(sky)
        local_sky[:535, 1000:1740] = sky[:535, 1000:1740]
        plate = _source_gradient(source, local_sky, vacated)
        fixed = output.copy()
        fixed[repair] = source[repair]
        fixed[vacated] = plate[vacated]
        fixed[new] = generated[new]
        return fixed, repair.astype(np.uint8) * 255
    # Source linework has a broad compressed blue/green fringe. It is part of
    # the old silhouette's removal support, not the new hat's crop boundary.
    old_support = cv2.dilate(source_matte, np.ones((17, 17), np.uint8)) != 0
    new_support = generated_matte != 0
    repair = old_support | new_support | (original_subject != 0) | (new_subject != 0)
    vacated = old_support & ~new_support
    plate = _source_gradient(source, sky, vacated)
    fixed = output.copy()
    fixed[repair] = source[repair]
    fixed[vacated] = plate[vacated]
    fixed[new_support] = generated[new_support]
    return fixed, repair.astype(np.uint8) * 255
