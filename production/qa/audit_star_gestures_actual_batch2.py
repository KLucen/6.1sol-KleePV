"""Actual-frame lyric and raw-PNG provenance evidence for the local star span."""

from pathlib import Path
import hashlib
import json

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa/fast-fullpv-star-gestures-2026-10-04/actual-audit"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    proposal = json.loads((OUT.parent / "draft-proposal.json").read_text(encoding="utf-8"))
    private = {s["source_frame"]: s for s in proposal["selections"]}
    cels = [c for c in manifest["cels"] if 1008 <= c["canonical_source_frame"] < 1043]
    cap = cv2.VideoCapture(meta["source"])
    for frame in range(1008):
        if not cap.grab():
            raise ValueError(f"Source ended at {frame}")
    rows, panels = [], []
    try:
        for frame in range(1008, 1043):
            ok, source = cap.read()
            if not ok:
                raise ValueError(f"Source ended at {frame}")
            path = OUT / f"actual-f{frame:04d}.png"
            cv2.imwrite(str(path), source)
            crop = source[950:1055, 610:1310]
            native = OUT / f"actual-f{frame:04d}-native-caption.png"
            cv2.imwrite(str(native), crop)
            enlarged = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
            panel = Image.new("RGB", (1400, 235), "#202024")
            panel.paste(Image.fromarray(cv2.cvtColor(enlarged, cv2.COLOR_BGR2RGB)), (0, 25))
            ImageDraw.Draw(panel).text((8, 7), f"actual source f{frame:04d}, native glyph crop x2", fill="white")
            panels.append(panel)
            rows.append({"frame": frame, "actual_source": str(path.relative_to(ROOT)),
                         "decoded_rgb_sha256": digest(source.tobytes()),
                         "file_sha256": digest(path.read_bytes()),
                         "native_caption": str(native.relative_to(ROOT))})
    finally:
        cap.release()
    for start in range(0, len(panels), 7):
        group = panels[start:start+7]
        page = Image.new("RGB", (1400, sum(p.height for p in group)), "#202024")
        for i, panel in enumerate(group):
            page.paste(panel, (0, i*235))
        page.save(OUT / f"actual-caption-page-{start//7+1:02d}.png")
    raw_rows, triples = [], []
    for cel in cels:
        frame = cel["canonical_source_frame"]
        asset = private.get(frame) or cel["selected_asset"]
        raw = Image.open(ROOT / asset["path"]).convert("RGB")
        actual = Image.open(OUT / f"actual-f{frame:04d}.png").convert("RGB")
        composite = Image.open(OUT.parent / f"compose-static/f{frame:04d}-existing-compose.png").convert("RGB")
        panel = Image.new("RGB", (1920, 386), "#202024")
        draw = ImageDraw.Draw(panel)
        for i, (im, role) in enumerate(((actual, "ACTUAL SOURCE"), (raw, "RAW PNG"), (composite, "EXISTING COMPOSE"))):
            original_size = im.size
            im = im.copy()
            im.thumbnail((640, 360))
            panel.paste(im, (i*640, 26))
            draw.text((i*640+8, 7), f"f{frame:04d} {role} {original_size}", fill="white")
        triples.append(panel)
        raw_rows.append({"frame": frame, "path": asset["path"], "dimensions": raw.size,
                         "sha256": digest((ROOT / asset["path"]).read_bytes())})
    for start in range(0, len(triples), 4):
        group = triples[start:start+4]
        page = Image.new("RGB", (1920, sum(p.height for p in group)), "#202024")
        for i, panel in enumerate(group):
            page.paste(panel, (0, i*386))
        page.save(OUT / f"source-raw-compose-page-{start//4+1:02d}.png")
    raw = Image.open(ROOT / "generated/candidate-035.png")
    raw.crop((140, 770, 480, 941)).save(OUT / "f1017-raw-old-rear-contour-native.png")
    actual = Image.open(OUT / "actual-f1017.png")
    actual.crop((160, 880, 551, 1080)).save(OUT / "f1017-source-old-rear-contour-native.png")
    composite = Image.open(OUT.parent / "compose-static/f1017-existing-compose.png")
    composite.crop((160, 880, 551, 1080)).save(OUT / "f1017-compose-old-rear-contour-native.png")
    report = {"owner": "star_gestures_batch2", "accepted": False,
              "source_interval": [1008, 1043], "actual_frames_decoded": len(rows),
              "source_video_sha256": meta["sha256"],
              "phase_review": "pending", "raw_original_subject_review": "pending",
              "actual_frames": rows, "raw_assets": raw_rows,
              "scope": "Local source decoding and static evidence only; no video export, source timing edits or public mapping mutation."}
    (OUT / "evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"actual_frames": len(rows), "canonical_triples": len(raw_rows), "path": str(OUT)}))


if __name__ == "__main__":
    main()
