"""Native donor and stored alpha diagnostics, with no stroke synthesis."""

from pathlib import Path
import sys
import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from star_extended_captions import _clear_short_layer
from star_gestures_layers import caption_layer

for name, layer in (("short", _clear_short_layer()), ("long", caption_layer(2))):
    alpha = layer["alpha"]
    ink = layer.get("ink_rgb", layer.get("foreground"))
    image = np.rint(alpha[..., None] * ink).clip(0, 255).astype(np.uint8)
    gray = cv2.cvtColor(np.rint(alpha * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    cv2.imwrite(str(HERE / f"{name}-native-ink-alpha-diagnostic.png"), np.concatenate((image, gray)))
source = cv2.imread(str(ROOT / "qa/closeup-layers-2026-10-06/source/f2420.png"))
cv2.imwrite(str(HERE / "short-f2420-native-current-donor.png"), source[954:992, 650:820])
cel = cv2.imread(str(ROOT / "generated/middle-next-f2132-oct6-v1.png"))
cv2.imwrite(str(ROOT / "qa/middle-next-2026-10-06/klee-f2132-foreground-head-only.png"), cel[0:715, 850:1672])
