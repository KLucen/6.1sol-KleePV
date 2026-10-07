"""63 source exposures, native all-caption and every-cel body evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from compose import read_image
import closeup_layers_private as private
from prepare_private import label, sha


def main():
    cv2.setNumThreads(2)
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, nargs="+")
    args = parser.parse_args()
    timeline = json.loads((HERE / "timeline-private-1162-1225.json").read_text(encoding="utf-8"))
    provenance = json.loads((HERE / "source-provenance.json").read_text(encoding="utf-8"))
    frames = args.sample or list(range(1162, 1225))
    canonical = {e["start"] for e in timeline["output_exposures"]}
    assets, outputs, records, bodies = {}, {}, [], []
    output_dir = HERE / "output"
    output_dir.mkdir(exist_ok=True)
    for frame in frames:
        source = cv2.imread(str(HERE / "source" / f"f{frame:04d}.png"))
        exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = timeline["assets"][exposure["cel"]]
        assert np.array_equal(np.array(exposure["source_matrix"]), [[1, 0, 0], [0, 1, 0]]), frame
        if asset["path"] not in assets:
            assets[asset["path"]] = read_image(ROOT / asset["path"])
        generated = assets[asset["path"]]
        output, masks = private.compose_private(source, generated, frame, Path(asset["path"]).name)
        output_path = output_dir / f"f{frame:04d}-private.png"
        cv2.imwrite(str(output_path), output)
        outputs[frame] = output
        outside = int(np.count_nonzero(np.any(output != source, axis=2) & ~masks["ownership"]))
        interior = cv2.erode(masks["new"], np.ones((5, 5), np.uint8)) != 0
        interior &= ~masks["caption"]
        new_errors = int(np.count_nonzero(np.any(output != generated, axis=2) & interior))
        x0, y0, x1, y1 = masks["caption_region"]
        text_errors = int(np.count_nonzero(np.any(output[y0:y1, x0:x1] != masks["expected_text"], axis=2) & masks["paint"]))
        assert outside == new_errors == text_errors == 0, (frame, outside, new_errors, text_errors)
        records.append({"frame": frame, "pts": timeline["source_pts"][frame-1162], "cel": exposure["cel"],
                        "asset": asset["path"], "asset_source_frame": asset["source_frame"],
                        "source_alias": asset.get("verified_source_alias"), "output_path": str(output_path),
                        "output_sha256": sha(output_path), "output_bgr_sha256": hashlib.sha256(output.tobytes()).hexdigest(),
                        "old_pixels": int(np.count_nonzero(masks["old"])), "new_pixels": int(np.count_nonzero(masks["new"])),
                        "vacated_pixels": int(masks["vacated"].sum()), "outside_ownership_changed": outside,
                        "new_interior_errors": new_errors, "caption_oracle_errors": text_errors,
                        "caption_phase": "pain" if frame < 1217 else "magic", "accepted": False})
        if frame in canonical or args.sample:
            cv2.imwrite(str(HERE / f"f{frame:04d}-private-full-ab.png"), np.concatenate((source, output), axis=1))
            # One whole output plus native face and both wrists are visible
            # even when the open palms are clipped at the canvas edges.
            for kind, image in (("source", source), ("output", output)):
                path = HERE / f"f{frame:04d}-full-{kind}.png"
                cv2.imwrite(str(path), image)
                bodies.append(str(path))
            for name, box in {"face": (620, 40, 1320, 720), "left-wrist": (0, 0, 640, 960),
                              "right-wrist": (1280, 0, 1920, 960)}.items():
                xx0, yy0, xx1, yy1 = box
                pair = np.concatenate((source[yy0:yy1, xx0:xx1], output[yy0:yy1, xx0:xx1]), axis=1)
                path = HERE / f"f{frame:04d}-native-{name}-source-output.png"
                cv2.imwrite(str(path), label(pair, f"f{frame} SOURCE | PRIVATE, native 1:1 {name}"))
                bodies.append(str(path))
        print(json.dumps({"frame": frame, "outside": outside, "new": new_errors, "caption": text_errors}), flush=True)
    pages = []
    for offset in range(0, len(frames), 9):
        rows = []
        for frame in frames[offset:offset+9]:
            source = cv2.imread(str(HERE / "source" / f"f{frame:04d}.png"))
            row = np.concatenate((source[945:1047, 650:1250], outputs[frame][945:1047, 650:1250]), axis=1)
            rows.append(label(row, f"f{frame} SOURCE | PRIVATE, native 1:1; {'pain' if frame < 1217 else 'magic'}"))
        path = HERE / f"all-caption-native-page-{offset//9+1:02d}.png"
        cv2.imwrite(str(path), np.concatenate(rows))
        pages.append(str(path))
    if args.sample:
        return
    unchanged = {name: sha(ROOT / name) == digest for name, digest in provenance["shared_code_freeze"].items()}
    report = {"accepted": False, "interval": [1162, 1225], "source_frames": len(frames),
              "cels": len(canonical), "exposures": len(timeline["output_exposures"]), "unique_images": len(assets),
              "source_pts_unchanged": True, "identity_source_transforms": True,
              "outside_ownership_bgr_exact": all(r["outside_ownership_changed"] == 0 for r in records),
              "new_interior_generated_exact": all(r["new_interior_errors"] == 0 for r in records),
              "caption_estimated_alpha_oracle_exact": all(r["caption_oracle_errors"] == 0 for r in records),
              "shared_code_unchanged": unchanged, "caption_native_pages": pages, "canonical_body_files": bodies,
              "native_static_review": "pending actual viewing", "original_speed_review": "not performed",
              "encoded_review": "not performed", "frames": records,
              "limitations": ["Source gradient under vacated anatomy is estimated from current visible source, not an unseen clean original.",
                              "Original visible stars outside new character are retained, hidden portions are not invented.",
                              "Real donor glyph palette and antialias are reconstructed; donor strokes are not claimed pixel-identical to obscured target glyphs."],
              "files": {name: sha(HERE / name) for name in ("closeup_layers_private.py", "pain-real-caption.npz",
                       "magic-real-caption.npz", "caption-provenance.json", "timeline-private-1162-1225.json")}}
    (HERE / "private-63frame-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
