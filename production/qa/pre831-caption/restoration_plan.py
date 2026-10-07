"""Private proposed source-exact rectangle, not integrated into production."""

import numpy as np

SAFE_INTERVAL = (812, 831)
PROPOSED_RECT = (870, 954, 1022, 1044)
JAPANESE_FIELD = (870, 954, 1022, 994)
CHINESE_FIELD = (881, 1002, 1010, 1044)


def apply_proposed_source_restore(output, source, frame):
    mask = np.zeros(source.shape[:2], np.uint8)
    if SAFE_INTERVAL[0] <= frame < SAFE_INTERVAL[1]:
        x0, y0, x1, y1 = PROPOSED_RECT
        output[y0:y1, x0:x1] = source[y0:y1, x0:x1]
        mask[y0:y1, x0:x1] = 255
    return output, mask
