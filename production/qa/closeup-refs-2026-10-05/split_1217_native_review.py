"""Split only review panels; preserve each source pixel at 1:1."""
from pathlib import Path
import json
from PIL import Image

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'star-microcel-audit-2026-10-05'
records = []
for name, columns in [('f1216-f1217-character-rgb-contours.png', 2)] + [
    (f'f1216-f1217-locals-native-page-{n:02d}.png', 4) for n in range(1, 5)
]:
    img = Image.open(SOURCE / name)
    assert img.width % columns == 0
    width = img.width // columns
    groups = [[n] for n in range(columns)] if columns == 2 else [[0, 1], [2, 3]]
    for g, indices in enumerate(groups):
        out = Image.new('RGB', (width * len(indices), img.height))
        for k, n in enumerate(indices):
            out.paste(img.crop((n * width, 0, (n + 1) * width, img.height)), (k * width, 0))
        path = HERE / f'{Path(name).stem}-split-{g}-native.png'
        out.save(path)
        records.append({'path': str(path), 'source': str(SOURCE / name), 'columns': indices, 'size': list(out.size), 'resized': False})
(HERE / 'split-1217-native-index.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
print(json.dumps(records))
