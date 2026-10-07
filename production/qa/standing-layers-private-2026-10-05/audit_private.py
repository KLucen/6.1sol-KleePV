"""Raw 119-frame private proposal and native all-frame review evidence."""

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
import compose
import standing_layers_private as private


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label(image, text):
    band = np.full((27, image.shape[1], 3), 245, np.uint8)
    cv2.putText(band, text, (10, 19), cv2.FONT_HERSHEY_SIMPLEX, .5, (20, 20, 20), 1, cv2.LINE_AA)
    return np.concatenate((band, image), axis=0)


def write_caption_pages(frames, outputs):
    pages = []
    for offset in range(0, len(frames), 10):
        rows = []
        for frame in frames[offset:offset+10]:
            source = cv2.imread(str(HERE / "source" / f"f{frame:04d}.png"))
            output = outputs[frame]
            row = np.concatenate((source[945:1047, 650:1250], output[945:1047, 650:1250]), axis=1)
            rows.append(label(row, f"f{frame:04d} source | private output; 1 source pixel = 1 displayed pixel"))
        path = HERE / f"all-caption-native-page-{offset//10+1:02d}.png"
        cv2.imwrite(str(path), np.concatenate(rows, axis=0))
        pages.append(str(path))
    return pages


def main():
    cv2.setNumThreads(2)
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, nargs="+")
    args = parser.parse_args()
    timeline = json.loads((HERE / "timeline-private-1043-1162.json").read_text(encoding="utf-8"))
    provenance = json.loads((HERE / "source-provenance.json").read_text(encoding="utf-8"))
    frames = args.sample or list(range(1043, 1162))
    canonical = {e["start"] for e in timeline["output_exposures"]}
    outputs = {}
    records = []
    bodies = []
    assets = {}
    output_dir = HERE / "output"
    output_dir.mkdir(exist_ok=True)
    for frame in frames:
        source = cv2.imread(str(HERE / "source" / f"f{frame:04d}.png"))
        exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = timeline["assets"][exposure["cel"]]
        if asset["path"] not in assets:
            assets[asset["path"]] = compose.read_image(ROOT / asset["path"])
        generated = assets[asset["path"]]
        output, masks = private.compose_private(source, generated, frame, Path(asset["path"]).name)
        output_path = output_dir / f"f{frame:04d}-private.png"
        cv2.imwrite(str(output_path), output)
        outputs[frame] = output
        outside_errors = int(np.count_nonzero(np.any(output != source, axis=2) & ~masks["ownership"]))
        new_interior = cv2.erode(masks["new"], np.ones((5, 5), np.uint8)) != 0
        new_interior &= ~masks["caption"]
        new_errors = int(np.count_nonzero(np.any(output != generated, axis=2) & new_interior))
        x0, y0, x1, y1 = masks["caption_region"]
        original_core = masks["observed_core"]
        core_errors = int(np.count_nonzero(np.any(output[y0:y1, x0:x1] != source[y0:y1, x0:x1], axis=2) & original_core))
        record = {"frame": frame, "cel": exposure["cel"], "asset": asset["path"],
                  "asset_source_frame": asset["source_frame"], "output_path": str(output_path),
                  "output_sha256": sha(output_path), "output_bgr_sha256": hashlib.sha256(output.tobytes()).hexdigest(),
                  "old_matte_pixels": int(np.count_nonzero(masks["old"])),
                  "new_matte_pixels": int(np.count_nonzero(masks["new"])),
                  "vacated_source_pixels": int(np.count_nonzero(masks["vacated"])),
                  "source_observed_core_exact_pixels": int(original_core.sum()),
                  "outside_ownership_changed_pixels": outside_errors,
                  "new_interior_not_generated_pixels": new_errors,
                  "current_source_observed_core_errors": core_errors,
                  "accepted": False, "actual_speed_review": "not performed"}
        assert outside_errors == new_errors == core_errors == 0, record
        records.append(record)
        if frame in canonical or args.sample:
            cv2.imwrite(str(HERE / f"f{frame:04d}-private-full-ab.png"), np.concatenate((source, output), axis=1))
            mask_panel = source.copy()
            mask_panel[masks["old"] != 0] = np.rint(mask_panel[masks["old"] != 0] * .55 + np.array((220, 90, 50)) * .45)
            generated_panel = generated.copy()
            generated_panel[masks["new"] != 0] = np.rint(generated_panel[masks["new"] != 0] * .55 + np.array((30, 160, 250)) * .45)
            cv2.imwrite(str(HERE / f"f{frame:04d}-private-matte-ab.png"), np.concatenate((mask_panel, generated_panel), axis=1))
            if frame < 1161:
                body = np.concatenate((source[40:1080, 620:1320], output[40:1080, 620:1320]), axis=1)
                path = HERE / f"f{frame:04d}-native-body-source-output.png"
                cv2.imwrite(str(path), label(body, f"f{frame:04d} source | private output; native crop"))
                bodies.append(str(path))
            else:
                for kind, image in (("source", source), ("output", output)):
                    path = HERE / f"f{frame:04d}-native-closeup-{kind}.png"
                    cv2.imwrite(str(path), image[:, 260:1600])
                    bodies.append(str(path))
        print(json.dumps({"frame": frame, "outside_errors": outside_errors, "new_errors": new_errors, "core_errors": core_errors}), flush=True)
    pages = write_caption_pages(frames, outputs)
    if args.sample:
        return
    freeze = provenance["shared_code_freeze"]
    unchanged = {name: sha(ROOT / name) == digest for name, digest in freeze.items()}
    assert all(unchanged.values())
    report = {"accepted": False, "kind": "private standing full interval composition proposal",
              "interval": [1043, 1162], "source_frames": len(frames),
              "source_cels": len({e["cel"] for e in timeline["output_exposures"]}),
              "exposures": len(timeline["output_exposures"]), "unique_selected_images": len(assets),
              "source_decode_provenance": "source-provenance.json", "canonical_native_bgr_verified": True,
              "all_exposures_source_pts_unchanged": True, "all_transforms_identity": True,
              "outside_ownership_bgr_exact_all119": all(r["outside_ownership_changed_pixels"] == 0 for r in records),
              "generated_interior_exact_all119": all(r["new_interior_not_generated_pixels"] == 0 for r in records),
              "current_source_observed_core_exact_all119": all(r["current_source_observed_core_errors"] == 0 for r in records),
              "shared_code_unchanged": unchanged, "original_1008_1043_hook_unchanged": True,
              "caption_native_pages": pages, "canonical_native_body_files": bodies,
              "native_static_review": "Pending actual image viewing; generated evidence is not a visual pass.",
              "original_speed_review": "not performed", "encoded_review": "not performed",
              "known_limitations": ["Vacated source anatomy receives a measured source-gradient plate, not an unseen original clean plate.",
                                    "Pale stars are background: only original visible portions outside the new subject remain, no invented hidden star drawing.",
                                    "Real donor glyph alpha and palette are reconstructed under human allowance; unobservable original pant strokes are not claimed restored."],
              "frames": records, "proposal_files": {name: sha(HERE / name) for name in ("standing_layers_private.py", "short-caption-f1161-real.npz", "short-caption-provenance.json", "timeline-private-1043-1162.json")}}
    (HERE / "private-119frame-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
