"""Diagnostic cold Klee head crop; it is not a new animation cel."""

from pathlib import Path
import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
image = cv2.imread(str(ROOT / "generated/fast-fullpv-cyan-f0973-v1.png"))
assert image is not None
path = HERE / "klee-f0973-cold-head-identity-only.png"
if path.exists():
    raise FileExistsError("Preserve previous diagnostic reference")
cv2.imwrite(str(path), image[0:770, 390:1320])
print(path)
