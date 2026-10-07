"""Identity-only diagnostic crop; no generated pixels are altered."""
from pathlib import Path
import cv2

here = Path(__file__).resolve().parent
root = here.parents[1]
source = cv2.imread(str(root / "generated/middle-next-f2143-oct6-v1.png"))
assert source.shape == (941, 1672, 3)
target = here / "klee-f2143-warm-head-identity-only.png"
assert not target.exists()
assert cv2.imwrite(str(target), source[:820, :810])
print(target)
