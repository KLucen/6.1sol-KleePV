"""Crop bitmap topology references without carrying a whole-face pose."""

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "generated/fast-fullpv-cyan-f0980-v1.png"
    image = Image.open(source).convert("RGB")
    width, height = image.size
    regions = [
        ("BERET / FEATHER COLORS ONLY - NO FACE POSE", (0.31, 0.0, 0.78, 0.34)),
        ("SHORT PONY / EAR ROOT ONLY - CURRENT ROOT POSITION NOT INHERITED", (0.26, 0.42, 0.57, 0.78)),
        ("PLAIN TWO-LEAF COLLAR / COAT ONLY - NO POSE", (0.44, 0.68, 0.66, 1.0)),
    ]
    crops = [(label, image.crop(tuple(round(v * (width if i % 2 == 0 else height))
                                     for i, v in enumerate(region))))
             for label, region in regions]
    board = Image.new("RGB", (max(c.width for _, c in crops) + 16,
                              sum(c.height + 34 for _, c in crops)), "white")
    draw = ImageDraw.Draw(board)
    y = 0
    for label, crop in crops:
        draw.text((8, y + 6), label, fill="black")
        board.paste(crop, (8, y + 26))
        y += crop.height + 34
    target = ROOT / "qa/fast-fullpv-cyan-2026-10-04/f0980-topology-no-face-reference.png"
    if target.exists():
        raise FileExistsError(target)
    board.save(target)
    print(target)


if __name__ == "__main__":
    main()
