"""Prepare private source-difference evidence, never production artwork."""

from pathlib import Path
import hashlib
import json
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta

OUT = ROOT / "qa/fast-fullpv-star-gestures-2026-10-04"
TARGETS = [1009, 1010, 1012, 1013, 1014, 1023, 1025, 1033, 1037, 1038]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text())
    cels = manifest["cels"]
    sources = {c["canonical_source_frame"]: c for c in cels}
    report = {
        "owner": "star_gestures_batch2",
        "mode": "strict_source",
        "accepted": False,
        "source_meta": "source_meta.json",
        "source_meta_sha256": sha256(ROOT / "source_meta.json"),
        "public_mapping_sha256_before": sha256(ROOT / "asset_selections.json"),
        "targets": [],
    }
    for frame in TARGETS:
        current = sources[frame]
        index = cels.index(current)
        before, after = cels[index - 1], cels[index + 1]
        delta = OUT / f"f{frame:04d}-source-delta.png"
        if not delta.exists():
            make_delta(ROOT / before["source_reference"], ROOT / current["source_reference"], delta)
        after_delta = OUT / f"f{frame:04d}-source-next-delta.png"
        if not after_delta.exists():
            make_delta(ROOT / current["source_reference"], ROOT / after["source_reference"], after_delta)
        report["targets"].append({
            "source_cel": current["cel"],
            "source_frame": frame,
            "source_reference": current["source_reference"],
            "source_sha256": sha256(ROOT / current["source_reference"]),
            "source_exposures": current["source_exposures"],
            "selected_asset_before": current["selected_asset"],
            "before_source": before["source_reference"],
            "after_source": after["source_reference"],
            "before_asset": before["selected_asset"],
            "after_asset": after["selected_asset"],
            "source_delta": str(delta.relative_to(ROOT)),
            "source_next_delta": str(after_delta.relative_to(ROOT)),
        })
    canvas = Image.new("RGB", (1920, 1180), "#202024")
    draw = ImageDraw.Draw(canvas)
    for i, frame in enumerate(TARGETS):
        x, y = (i % 4) * 480, (i // 4) * 390
        im = Image.open(ROOT / sources[frame]["source_reference"])
        im.thumbnail((480, 340))
        canvas.paste(im, (x, y + 25))
        draw.text((x + 8, y + 6), f"f{frame:04d} {sources[frame]['cel']}", fill="white")
    canvas.save(OUT / "ten-current-source-contact.jpg")
    (OUT / "source-evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"targets": len(report["targets"]), "path": str(OUT)}))


if __name__ == "__main__":
    main()
