"""Crop a diagnostic locator; never change the generated PV artwork."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def main():
    path = ROOT / "generated/star-f1091-underarm-hair-v2.png"
    with Image.open(path) as image:
        crop = image.crop((720, 380, 775, 455))
        crop.save(OUT / "f1091-underarm-locator-native.png")
        crop.resize((330, 450), Image.Resampling.NEAREST).save(OUT / "f1091-underarm-locator-nearest6x.png")
    print("Saved unmodified native and nearest-neighbor diagnostic crops.")


if __name__ == "__main__":
    main()
