"""Retain enclosed cheek/ink pixels, never infer or paint character anatomy."""

import cv2
import numpy as np

import middle_transition_layers_private as base
import middle_transition_layers_v2_private as previous

REGISTERED = base.REGISTERED


def extract(image, frame, source=False):
    matte, sky = previous.extract(image, frame, source)
    if source or frame not in (2143, 2144):
        return matte, sky
    _, labels = cv2.connectedComponents((matte == 0).astype(np.uint8), 8)
    border = np.unique(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
    holes = (labels != 0) & ~np.isin(labels, border)
    actual_sky, _, _ = base._sky_color(image)
    roi = np.zeros(image.shape[:2], bool)
    roi[:, 1020:1630] = True
    # The observed cheek and small ink islands are closed holes in selected
    # existing face fill. Real highly saturated sky openings remain excluded.
    retain = holes & roi & ~actual_sky
    matte[retain] = 255
    sky[retain] = False
    return matte, sky


def compose_private(source, generated, frame, asset_name):
    base._matte_and_sky = extract
    try:
        return base.compose_private(source, generated, frame, asset_name)
    finally:
        base._matte_and_sky = previous.ORIGINAL_EXTRACT
