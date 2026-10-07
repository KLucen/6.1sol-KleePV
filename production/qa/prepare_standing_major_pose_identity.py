"""Crop topology/costume only so an upright face cannot freeze a tilted pose."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
source = Image.open(ROOT / "generated/standing-f1053-fast-v1.png").convert("RGB")
parts = [((695, 70, 990, 248), "Beret only"),
         ((659, 275, 779, 362), "Left short pony"),
         ((921, 276, 1004, 366), "Right short pony"),
         ((770, 354, 907, 430), "Plain collar"),
         ((757, 458, 919, 609), "Coat/hem/shorts"),
         ((694, 770, 989, 928), "Boots only")]
board = Image.new("RGB", (990, 465), "#242428")
draw = ImageDraw.Draw(board)
for index, (box, label) in enumerate(parts):
    x, y = (index % 3) * 330, (index // 3) * 232
    draw.text((x + 6, y + 6), label, fill="white")
    board.paste(source.crop(box), (x + 6, y + 31))
out = ROOT / "qa/standing-missing-2026-10-05/klee-topology-no-face-f1053.png"
board.save(out)
print(out)
