"""Exact registrations for the retained Oct 6 star composition checkpoints."""

from functools import lru_cache
import importlib.util
from pathlib import Path

import numpy as np

from star_extended_captions import compose_with_clear_captions

ROOT = Path(__file__).resolve().parent
CHECKPOINTS = (
    (1043, 1162, "standing-layers-private-2026-10-05", "standing_layers_private"),
    (1162, 1225, "closeup-layers-2026-10-06", "closeup_layers_private"),
)


@lru_cache(maxsize=2)
def _checkpoint(directory, name):
    path = ROOT / "qa" / directory / (name + ".py")
    spec = importlib.util.spec_from_file_location("_star_checkpoint_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compose_registered_star_extended(source, generated, frame, asset_name, transform):
    if frame is None:
        return None
    for start, end, directory, name in CHECKPOINTS:
        if not start <= frame < end:
            continue
        module = _checkpoint(directory, name)
        if not module.is_registered(frame, asset_name):
            return None
        if not np.array_equal(transform, [[1, 0, 0], [0, 1, 0]]):
            raise ValueError("Registered star checkpoints require the original identity transform")
        output, detail = compose_with_clear_captions(module, source, generated, frame)
        diagnostic = np.concatenate([source, output], axis=1)
        masks = np.zeros_like(source)
        masks[detail["old"] != 0] = (220, 90, 50)
        masks[detail["new"] != 0] = (30, 160, 250)
        masks[detail["vacated"]] = (180, 100, 220)
        masks[detail["effects"]] = (80, 245, 90)
        masks[detail["caption"]] = (245, 95, 180)
        return output, diagnostic, masks
    return None
