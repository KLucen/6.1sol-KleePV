"""Pose-neutral diagnostic Klee head reference, not a new cel."""

from pathlib import Path
import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
image = cv2.imread(str(ROOT / "generated/late-next-f2911-oct6-v1.png"))
assert image is not None
path = HERE / "klee-f2911-head-only-identity.png"
if path.exists():
    raise FileExistsError("Preserve existing identity reference")
cv2.imwrite(str(path), image[130:330, 930:1170])
print(path)
