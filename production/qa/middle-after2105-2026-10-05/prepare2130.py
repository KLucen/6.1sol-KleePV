"""Shot-specific source crops for the foreground-actor cut; no generated art."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


QA = Path(__file__).resolve().parent
ROOT = QA.parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=("source", "review"), default="source", nargs="?")
args = parser.parse_args()
source = Image.open(ROOT / "source_refs/src-1200-f2130.png").convert("RGB")
if args.mode == "review":
    draft = Image.open(ROOT / "generated/middle-after-f2130-2026-10-05-source-v1.png").convert("RGB")
    draft = draft.resize(source.size, Image.Resampling.LANCZOS)
    for name, box in {"foreground": (1060, 0, 1920, 1080),
                      "background": (670, 100, 1285, 1060)}.items():
        a, b = source.crop(box), draft.crop(box)
        target = QA / f"f2130-source-new-{name}-shot-specific.png"
        if target.exists():
            raise FileExistsError(target)
        page = Image.new("RGB", (a.width * 2, a.height + 28), "#202024")
        draw = ImageDraw.Draw(page)
        draw.text((8, 8), "SOURCE left / normalized DRAFT right: " + name, fill="white")
        page.paste(a, (0, 28))
        page.paste(b, (a.width, 28))
        page.save(target)
        print(target)
    raise SystemExit(0)
foreground = source.crop((1060, 0, 1920, 1080))
background = source.crop((670, 100, 1285, 1060))
target = QA / "f2130-source-native-two-actor-keyparts.png"
if target.exists():
    raise FileExistsError(target)
page = Image.new("RGB", (1475, 1108), "#202024")
draw = ImageDraw.Draw(page)
draw.text((8, 8), "CURRENT foreground native 1:1, top/right clipped", fill="white")
draw.text((868, 8), "CURRENT background native 1:1", fill="white")
page.paste(foreground, (0, 28))
page.paste(background, (860, 28))
page.save(target)
print(target)
