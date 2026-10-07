"""Split existing native source evidence without changing the source pixels."""

import json
from pathlib import Path

from PIL import Image


OUT = Path(__file__).resolve().parent


def main():
    pages = []
    for start, end in [(1080, 1085), (1085, 1091)]:
        source = OUT / f"exposure-f{start:04d}-f{end - 1:04d}-all-native.png"
        with Image.open(source) as contact:
            assert contact.size == (700 * (end - start), 1007)
            for offset in range(0, end - start, 2):
                stop = min(offset + 2, end - start)
                path = OUT / f"exposure-f{start + offset:04d}-f{start + stop - 1:04d}-native-review.png"
                contact.crop((offset * 700, 0, stop * 700, 1007)).save(path)
                pages.append({"path": str(path), "frames": list(range(start + offset, start + stop)),
                              "source_contact": str(source), "scale": 1, "interpolation": None})
    (OUT / "native-exposure-review-pages.json").write_text(json.dumps(pages, indent=2), encoding="utf-8")
    print(json.dumps(pages, indent=2))


if __name__ == "__main__":
    main()
