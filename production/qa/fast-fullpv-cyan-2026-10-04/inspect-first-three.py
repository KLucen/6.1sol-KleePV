import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
FRAMES = [935, 938, 939, 942, 945, 948, 951]
ASSETS = {
    935: "generated/fine-f0935-repair.png",
    938: "generated/fast-fullpv-cyan-f0938-position-v2.png",
    939: "generated/fine-f0939.png",
    942: "generated/fast-fullpv-cyan-f0942-v1.png",
    945: "generated/fine-f0945.png",
    948: "generated/fast-fullpv-cyan-f0948-v1.png",
    951: "generated/fine-f0951.png",
}
OUT = QA / "first-three-adjacency"
OUT.mkdir(exist_ok=True)
rows = []
records = []
for frame in FRAMES:
    source_path = QA / f"f{frame:04d}-source-actual.png"
    art_path = ROOT / ASSETS[frame]
    source = Image.open(source_path).convert("RGB")
    original = Image.open(art_path).convert("RGB")
    art = original.resize(source.size, Image.Resampling.LANCZOS)
    pair = Image.new("RGB", (3840, 1080))
    pair.paste(source, (0, 0))
    pair.paste(art, (1920, 0))
    pair.save(OUT / f"f{frame:04d}-source-art-native.png")
    row = Image.new("RGB", (1440, 435), "#202020")
    ImageDraw.Draw(row).text((8, 6), f"f{frame:04d} SOURCE | {'NEW DRAFT' if frame in [938, 942, 948] else 'OLD ADJACENT'} {art_path.name}", fill="white")
    row.paste(pair.resize((1440, 405), Image.Resampling.LANCZOS), (0, 30))
    rows.append(row)
    records.append({"source_frame": frame, "source_path": str(source_path), "asset_path": str(art_path), "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(), "asset_sha256": hashlib.sha256(art_path.read_bytes()).hexdigest(), "asset_native_size": list(original.size), "evidence_normalization": "LANCZOS to source1920x1080 only for contact sheet; no artwork edited"})
for n, start in enumerate(range(0, len(rows), 4), 1):
    page = Image.new("RGB", (1440, 435 * len(rows[start:start + 4])), "#202020")
    for i, row in enumerate(rows[start:start + 4]):
        page.paste(row, (0, 435 * i))
    page.save(OUT / f"sequence-page-{n:02d}.png")
(OUT / "inputs.json").write_text(json.dumps({"scope": "Static source/art adjacency of first3 new cyan cels, not composite or original-speed playback", "records": records}, indent=2), encoding="utf-8")
print(json.dumps({"out": str(OUT), "rows": len(rows)}, indent=2))
