"""Private exact-source and bounded composition evidence for the cyan shot."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compose import compose, read_image

OUT = ROOT / "qa/fast-fullpv-cyan-layers-2026-10-04"
FROZEN = list(range(897, 911)) + list(range(1225, 1285))
CYAN = list(range(911, 1008))
CHECK = [911, 938, 954, 963]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def exposure_map(manifest):
    result = {}
    for row in manifest["cels"]:
        for exposure in row["source_exposures"]:
            for frame in range(exposure["start"], exposure["end"]):
                result[frame] = (row, exposure)
    return result


def compose_frame(source, row, exposure):
    selected = row["selected_asset"]
    asset = ROOT / selected["path"]
    return compose(source, read_image(ROOT / row["source_reference"]), read_image(asset),
                   exposure["source_transform"]["matrix"], selected["source_frame"],
                   asset.name, exposure["actual_frame"])


def caption_pages(images, prefix):
    records = []
    for offset in range(0, len(images), 8):
        group = images[offset:offset + 8]
        page = Image.new("RGB", (800, len(group)*148), "#222226")
        draw = ImageDraw.Draw(page)
        for i, (frame, image) in enumerate(group):
            draw.text((8, i*148+5), f"source f{frame:04d}, native 800x120 crop x560:y940", fill="white")
            page.paste(Image.fromarray(cv2.cvtColor(image[940:1060, 560:1360], cv2.COLOR_BGR2RGB)), (0, i*148+25))
        path = OUT / f"{prefix}-page-{offset//8+1:02d}.png"
        page.save(path)
        records.append({"path": str(path), "sha256": digest(path), "frames": [x[0] for x in group]})
    return records


def main():
    cv2.setNumThreads(2)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "actual-source").mkdir(exist_ok=True)
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    exposures = exposure_map(manifest)
    cap = cv2.VideoCapture(metadata["source"])
    sources, frozen = [], []
    for frame in range(1285):
        ok, source = cap.read()
        if not ok:
            raise ValueError(f"Source stopped at actual frame {frame}")
        if frame in CYAN:
            path = OUT / "actual-source" / f"f{frame:04d}.png"
            cv2.imwrite(str(path), source)
            row, exposure = exposures[frame]
            sources.append((frame, source))
            if frame in CHECK:
                exposure = {**exposure, "actual_frame": frame}
                output, diagnostic, masks = compose_frame(source, row, exposure)
                selected = read_image(ROOT / row["selected_asset"]["path"])
                cv2.imwrite(str(OUT / f"before-f{frame:04d}-source-art-composite-native.png"),
                            cv2.vconcat([source, selected, output]))
                cv2.imwrite(str(OUT / f"before-f{frame:04d}-composite.png"), output)
                cv2.imwrite(str(OUT / f"before-f{frame:04d}-masks.png"), masks)
        if frame in FROZEN:
            row, exposure = exposures[frame]
            exposure = {**exposure, "actual_frame": frame}
            output, _, _ = compose_frame(source, row, exposure)
            frozen.append({"source_frame": frame, "cel": row["cel"],
                           "source_bgr_sha256": sha256(source.tobytes()).hexdigest(),
                           "asset": row["selected_asset"]["path"],
                           "asset_sha256": digest(ROOT / row["selected_asset"]["path"]),
                           "composite_bgr_sha256": sha256(output.tobytes()).hexdigest()})
    cap.release()
    records = [{"frame": frame, "pts": metadata["pts"][frame],
                "decoded_bgr_sha256": sha256(source.tobytes()).hexdigest(),
                "png": str(OUT / "actual-source" / f"f{frame:04d}.png"),
                "png_sha256": digest(OUT / "actual-source" / f"f{frame:04d}.png")}
               for frame, source in sources]
    save_json(OUT / "source-decode.json", {"source": metadata["source"],
              "source_sha256": metadata["sha256"], "decode": "sequential actual frames 0..1284",
              "cyan_saved_interval": [911, 1008], "frames": records,
              "native_source_caption_pages": caption_pages(sources, "actual-source-caption")})
    save_json(OUT / "frozen-before-hashes.json", {"scope": [[897, 911], [1225, 1285]],
              "frames": frozen, "compose_sha256": digest(ROOT / "compose.py")})
    print(json.dumps({"decoded_cyan": len(records), "frozen_baseline": len(frozen), "out": str(OUT)}))


if __name__ == "__main__":
    main()
