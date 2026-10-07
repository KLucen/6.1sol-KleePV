"""Only a diagnostic ponytail identity crop, never a final character patch."""
from pathlib import Path
import cv2

here = Path(__file__).resolve().parent
root = here.parents[1]
pixels = cv2.imread(str(root / "generated/middle-cold-f2149-oct6-v1.png"))
target = here / "klee-f2149-warm-ponytail-identity-only.png"
assert not target.exists()
assert cv2.imwrite(str(target), pixels[535:830, 655:980])
print(target)
