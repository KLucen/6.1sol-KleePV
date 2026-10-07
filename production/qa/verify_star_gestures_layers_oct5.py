"""Private native-frame ownership, lyric phase, and static art evidence."""

from pathlib import Path
import argparse
import hashlib
import io
import json
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import star_gestures_layers as layers

SOURCE = ROOT / "qa/fast-fullpv-star-gestures-2026-10-04/actual-audit"
OUT = ROOT / "qa/star-gestures-layers-2026-10-05"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_read(path, resize=False):
    im = cv2.imread(str(path))
    if im is None:
        raise FileNotFoundError(path)
    return cv2.resize(im, (1920, 1080), interpolation=cv2.INTER_LANCZOS4) if resize else im


def panel(images, labels, width=640, height=360):
    out = Image.new("RGB", (len(images)*width, height+26), "#202024")
    draw = ImageDraw.Draw(out)
    for col, (im, label) in enumerate(zip(images, labels)):
        im = Image.fromarray(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
        im.thumbnail((width, height))
        out.paste(im, (col*width, 26))
        draw.text((col*width+8, 7), label, fill="white")
    return out


def pages(panels, kind, per_page):
    paths = []
    for start in range(0, len(panels), per_page):
        group = panels[start:start+per_page]
        im = Image.new("RGB", (group[0].width, sum(p.height for p in group)), "#202024")
        y = 0
        for p in group:
            im.paste(p, (0, y))
            y += p.height
        path = OUT / f"{kind}-page-{start//per_page+1:02d}.png"
        buffer = io.BytesIO()
        im.save(buffer, format="PNG")
        if not path.exists() or path.read_bytes() != buffer.getvalue():
            path.write_bytes(buffer.getvalue())
        paths.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-from", type=int, default=1008)
    args = parser.parse_args()
    cv2.setNumThreads(2)
    OUT.mkdir(parents=True, exist_ok=True)
    previous = json.loads((OUT / "report.json").read_text(encoding="utf-8")) if args.resume_from > 1008 else None
    previous_rows = {row["frame"]: row for row in previous["rows"]} if previous else {}
    retained = {str(path.relative_to(ROOT)).replace("\\", "/"): digest(path)
                for frame in range(1008, min(args.resume_from, 1043))
                for path in (OUT / f"f{frame:04d}-private-compose.png",
                             OUT / f"f{frame:04d}-native-caption-pair.png")}
    prior_caption_hashes = {frame: digest(OUT / f"f{frame:04d}-native-caption-pair.png")
                           for frame in range(1008, 1037)} if previous else {}
    names = {f: name for name, (start, end) in layers.REGISTERED.items() for f in range(start, end)}
    cels = {start: name for name, (start, _) in layers.REGISTERED.items()}
    character_panels, caption_panels, matte_panels, rows = [], [], [], []
    generated_cache = {}
    for frame in range(*layers.SOURCE_INTERVAL):
        name = names[frame]
        source_path = SOURCE / f"actual-f{frame:04d}.png"
        asset_path = ROOT / "generated" / name
        source = image_read(source_path)
        if frame < args.resume_from:
            result = image_read(OUT / f"f{frame:04d}-private-compose.png")
            cap = image_read(OUT / f"f{frame:04d}-native-caption-pair.png")
            cap = cv2.resize(cap, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
            caption_panels.append(panel([cap], [f"f{frame:04d} source | private layered composite, native x2"], 2800, 210))
            if frame in cels:
                generated = image_read(asset_path, resize=True)
                matte = image_read(OUT / f"f{frame:04d}-ownership.png")
                character_panels.append(panel([source, generated, result],
                                             [f"f{frame:04d} ACTUAL SOURCE", "SELECTED RAW PNG", "PRIVATE LAYERS / UNACCEPTED"]))
                matte_panels.append(panel([source, generated, matte],
                                         [f"f{frame:04d} SOURCE", "SELECTED RAW PNG", "OWN MATTE / LYRIC SUPPORT"]))
            rows.append(previous_rows[frame])
            continue
        if name not in generated_cache:
            generated = image_read(asset_path, resize=True)
            own = layers.star_subject_mask(generated, frame, name)
            generated_cache[name] = generated, own
        generated, new = generated_cache[name]
        old = layers.star_subject_mask(source, frame, name, source=True)
        result, repair = layers.restore_star_gestures(source.copy(), source, generated, old, new, frame, name)
        result, lyric = layers.restore_star_captions(result, source, frame, name, new)
        support = (repair | lyric) != 0
        outside_changed = int(np.count_nonzero(np.any(result != source, axis=2) & ~support))
        layer = layers.caption_layer(layers._phase(frame))
        x0, y0, x1, y1 = layer["region"]
        core_error = int(np.count_nonzero(np.any(result[y0:y1, x0:x1] != source[y0:y1, x0:x1], axis=2) & layer["core"]))
        assert outside_changed == 0, (frame, "outside ownership", outside_changed)
        assert core_error == 0, (frame, "registered observed core", core_error)
        result_path = OUT / f"f{frame:04d}-private-compose.png"
        cv2.imwrite(str(result_path), result)
        cap = np.concatenate([source[950:1055, 610:1310], result[950:1055, 610:1310]], axis=1)
        cap_path = OUT / f"f{frame:04d}-native-caption-pair.png"
        cv2.imwrite(str(cap_path), cap)
        cap = cv2.resize(cap, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
        caption_panels.append(panel([cap], [f"f{frame:04d} source | private layered composite, native x2"], 2800, 210))
        if frame in cels:
            matte = np.zeros_like(source)
            matte[old != 0] = (220, 90, 50)
            matte[new != 0] = (30, 160, 250)
            matte[lyric != 0] = (245, 95, 180)
            cv2.imwrite(str(OUT / f"f{frame:04d}-ownership.png"), matte)
            character_panels.append(panel([source, generated, result],
                                         [f"f{frame:04d} ACTUAL SOURCE", "SELECTED RAW PNG", "PRIVATE LAYERS / UNACCEPTED"]))
            matte_panels.append(panel([source, generated, matte],
                                     [f"f{frame:04d} SOURCE", "SELECTED RAW PNG", "OWN MATTE / LYRIC SUPPORT"]))
        rows.append({"frame": frame, "asset": str(asset_path.relative_to(ROOT)).replace("\\", "/"),
                     "asset_sha256": digest(asset_path), "source_sha256": digest(source_path),
                     "word_phase": layers._phase(frame), "source_subject_pixels": int(np.count_nonzero(old)),
                     "generated_subject_pixels": int(np.count_nonzero(new)),
                     "outside_ownership_changed": outside_changed, "registered_core_changed": core_error,
                     "raw_composite": str(result_path.relative_to(ROOT)).replace("\\", "/"),
                     "native_caption_pair": str(cap_path.relative_to(ROOT)).replace("\\", "/")})
    for path, old_hash in retained.items():
        assert digest(ROOT / path) == old_hash, (path, "previous frame must remain byte-identical")
    for frame, old_hash in prior_caption_hashes.items():
        assert digest(OUT / f"f{frame:04d}-native-caption-pair.png") == old_hash, (frame, "previous lyric evidence must remain byte-identical")
    for i in range(3):
        layer = layers.caption_layer(i)
        core = layer["core"].astype(np.uint8)*255
        cv2.imwrite(str(OUT / f"phase-{i}-registered-glyph-core.png"), core)
        cv2.imwrite(str(OUT / f"phase-{i}-registered-glyph-alpha.png"), np.rint(layer["alpha"]*255).astype(np.uint8))
    report = {"accepted": False, "owner": "star_finish_oct5", "source_interval": [1008, 1043],
              "actual_frames": len(rows), "canonical_raw_composite_comparisons": len(character_panels),
              "source_timing_mutated": False, "compose_mutated": False, "selections_mutated": False,
              "registered_assets": layers.REGISTERED, "rows": rows,
              "resume_from": args.resume_from, "reused_output_sha256": retained,
              "prior_29_caption_sha256_unchanged": prior_caption_hashes,
              "pages": {"source_raw_composite": pages(character_panels, "source-raw-composite", 4),
                        "own_mattes": pages(matte_panels, "own-mattes", 4),
                        "native_lyrics": pages(caption_panels, "native-lyrics", 7)},
              "gate": {"full_35_ready": False, "character_ownership_static": "reviewed; repaired f1017 and source-owned f1033+ adjacent star preserved",
                       "lyric_static_safe_interval": [1008, 1037], "blocked_lyric_interval": [1037, 1043],
                       "blocker": "Native Japanese middle strokes over the observed pale cuffs remain fragmented. Exact observed cores do not establish complete glyph recovery.",
                       "regions": [[846, 959, 946, 988], [1038, 959, 1102, 988]],
                       "evidence": ["qa/star-gestures-layers-2026-10-05/f1037-native-caption-pair.png",
                                    "qa/star-gestures-layers-2026-10-05/phase2-native-donor-all.png",
                                    "qa/star-gestures-layers-2026-10-05/phase2-later-native-scan.png"]},
              "limits": "Static native raw images only. Vacated sky, hidden lyric plate and AA are reconstructed. Complete phase-2 glyph support and final encoded review are pending; no numeric test constitutes artistic acceptance."}
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"frames": len(rows), "canonical_comparisons": len(character_panels), "all_registered_core_exact": True,
                      "all_outside_ownership_exact": True, "report": str(OUT / "report.json")}))


if __name__ == "__main__":
    main()
