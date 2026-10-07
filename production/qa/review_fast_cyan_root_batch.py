"""Bitmap-only source/art contacts for this bounded cyan draft batch."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa/fast-fullpv-cyan-2026-10-04/root-seven-adjacency"
FRAMES = [935, 938, 939, 942, 945, 948, 951, 954, 957, 960, 963]
NEW = {938: "fast-fullpv-cyan-f0938-position-v2.png",
       **{f: f"fast-fullpv-cyan-f{f:04d}-v1.png" for f in [942, 948, 954, 957, 960, 963]}}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    records = []
    panels = []
    for frame in FRAMES:
        row = next(r for r in manifest["cels"] if r["canonical_source_frame"] == frame)
        source_path = ROOT / row["source_reference"]
        asset_path = ROOT / "generated" / NEW[frame] if frame in NEW else ROOT / row["selected_asset"]["path"]
        source = cv2.imread(str(source_path))
        art = cv2.imread(str(asset_path))
        if source is None or art is None:
            raise ValueError(f"Missing source/art f{frame}")
        art = cv2.resize(art, (1920, 1080), interpolation=cv2.INTER_LANCZOS4)
        pair = cv2.hconcat([source, art])
        native = OUT / f"f{frame:04d}-source-art-native.png"
        cv2.imwrite(str(native), pair)
        thumbnail = cv2.resize(pair, (1280, 360), interpolation=cv2.INTER_AREA)
        panels.append((frame, Image.fromarray(cv2.cvtColor(thumbnail, cv2.COLOR_BGR2RGB))))
        records.append({"source_frame": frame, "source_path": str(source_path),
                        "source_sha256": digest(source_path), "asset_path": str(asset_path),
                        "asset_sha256": digest(asset_path), "native_contact": str(native),
                        "native_contact_sha256": digest(native)})
    pages = []
    for offset in range(0, len(panels), 4):
        group = panels[offset:offset + 4]
        page = Image.new("RGB", (1280, 4 * 392), "#202024")
        draw = ImageDraw.Draw(page)
        for i, (frame, panel) in enumerate(group):
            draw.text((8, i * 392 + 8), f"f{frame:04d} SOURCE | CURRENT ART, DRAFT ONLY", fill="white")
            page.paste(panel, (0, i * 392 + 30))
        path = OUT / f"sequence-page-{offset // 4 + 1:02d}.png"
        page.save(path)
        pages.append({"path": str(path), "sha256": digest(path), "frames": [f for f, _ in group]})
    report = {"scope": "Static original source/art only; not final composite or actual-speed review",
              "frames": records, "pages": pages, "artistic_acceptance": False,
              "normalization": "Evidence contacts only, existing Lanczos canvas normalization; no new artwork or motion"}
    path = OUT / "inputs.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"record": str(path), "pages": pages}))


if __name__ == "__main__":
    main()
