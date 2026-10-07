"""Exact registration of the reviewed Oct 6 middle-transition draft checkpoint."""

from functools import lru_cache
import importlib.util
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE_INTERVAL = (2121, 2145)


@lru_cache(maxsize=1)
def _checkpoint():
    directory = ROOT / "qa" / "middle-transition-layers-private-2026-10-06"
    path = directory / "middle_transition_layers_v5_private.py"
    spec = importlib.util.spec_from_file_location("_middle_transition_checkpoint", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(directory))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(directory))
    return module


def compose_registered_middle_transition(source, generated, frame, asset_name, transform):
    if frame is None or not SOURCE_INTERVAL[0] <= frame < SOURCE_INTERVAL[1]:
        return None
    module = _checkpoint()
    if not module.is_registered(frame, asset_name):
        return None
    if not np.array_equal(transform, [[1, 0, 0], [0, 1, 0]]):
        raise ValueError("Registered middle checkpoint requires original identity registration")
    output, detail = module.compose_private(source, generated, frame, asset_name)
    diagnostic = np.concatenate([source, output], axis=1)
    masks = np.zeros_like(source)
    masks[detail["old"] != 0] = (220, 90, 50)
    masks[detail["new"] != 0] = (30, 160, 250)
    masks[detail["vacated"]] = (180, 100, 220)
    masks[detail["effects"]] = (80, 245, 90)
    masks[detail["caption"]] = (245, 95, 180)
    return output, diagnostic, masks
