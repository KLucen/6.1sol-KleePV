"""Private observed cool-fill repair for two exact exposures; no artwork edits."""

import cv2
import numpy as np

import middle_transition_layers_private as base

ORIGINAL_EXTRACT = base._matte_and_sky
REGISTERED = base.REGISTERED


def extract(image, frame, source=False):
    matte, sky = ORIGINAL_EXTRACT(image, frame, source)
    if source or frame not in (2143, 2144):
        return matte, sky
    h, s, v = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
    candidate = np.zeros(image.shape[:2], np.uint8)
    # In this observed all-night right-side ROI, sky is highly saturated.
    # Large low-saturation fills are the existing model's face/hair/collar;
    # tiny white stars and the moon are separate components, not anatomy.
    candidate[:, 1020:1630] = ((s[:, 1020:1630] < 150) & (v[:, 1020:1630] > 210)).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, 8)
    fill = np.zeros_like(candidate)
    for index in range(1, count):
        component = labels == index
        cool_anchor = component & (h >= 95) & (h <= 117) & (s >= 40)
        if stats[index, cv2.CC_STAT_AREA] >= 5000 and np.count_nonzero(cool_anchor) >= 500:
            fill[component] = 255
    fill = cv2.dilate(fill, np.ones((3, 3), np.uint8))
    matte = np.maximum(matte, fill)
    sky[fill != 0] = False
    return matte, sky


def compose_private(source, generated, frame, asset_name):
    base._matte_and_sky = extract
    try:
        return base.compose_private(source, generated, frame, asset_name)
    finally:
        base._matte_and_sky = ORIGINAL_EXTRACT
