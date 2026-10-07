"""Diagnostic identity crop only; no character artwork is synthesized."""

from pathlib import Path
import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
image = cv2.imread(str(ROOT / "generated/fast-fullpv-dance-f0900-rearhat-v2.png"))
assert image is not None
path = HERE / "klee-f0900-rear-head-identity-only.png"
if path.exists():
    raise FileExistsError("Preserve previous diagnostic reference")
cv2.imwrite(str(path), image[200:941, 450:1672])
print(path)
