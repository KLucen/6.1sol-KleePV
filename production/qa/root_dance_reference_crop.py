"""Crop only identity/evidence references; never construct character artwork."""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "qa/root-dance-continuation"


def main():
    OUTPUT.mkdir(exist_ok=True)
    hat = Image.open(ROOT / "style_refs/face-reaction-hat-only-f0310.png")
    hat.crop((210, 0, 1000, 205)).save(OUTPUT / "hat-color-clover-feather-only.png")
    print(OUTPUT / "hat-color-clover-feather-only.png")


if __name__ == "__main__":
    main()
