"""Package existing raster crops as references, never draw or alter PV artwork."""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "qa/fast-fullpv-dance-2026-10-04"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(ROOT / "generated/root-continuation-f0843-v1.png")
    boxes = {
        "identity-head-short-hair-f0843.png": (0.27, 0.06, 0.515, 0.40),
        "identity-two-leaf-collar-continuous-hem-f0843.png": (0.325, 0.335, 0.495, 0.635),
    }
    for name, ratios in boxes.items():
        box = tuple(round(value * (source.width if index % 2 == 0 else source.height))
                    for index, value in enumerate(ratios))
        source.crop(box).save(OUTPUT / name)
        print(OUTPUT / name)
    eyes = Image.open(ROOT / "qa/title-klee-identity-crop.png")
    eyes.crop((102, 124, 272, 224)).save(OUTPUT / "identity-red-eyes-only.png")
    print(OUTPUT / "identity-red-eyes-only.png")


if __name__ == "__main__":
    main()
