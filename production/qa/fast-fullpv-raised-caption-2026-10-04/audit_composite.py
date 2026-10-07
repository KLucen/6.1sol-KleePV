"""Affected sixty-frame composites and declared raised-caption support only."""

import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import compose as compositor
from raised_caption_layers import REGION, DONOR, raised_caption_layer, cream_glyph_candidate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bgrsha(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def write_pages(panels, stem, per_page=6):
    pages = []
    for start in range(0, len(panels), per_page):
        group = panels[start:start+per_page]
        canvas = Image.new("RGB", (max(p.width for p in group), sum(p.height for p in group)), "white")
        y = 0
        for panel in group:
            canvas.paste(panel, (0, y))
            y += panel.height
        file = OUT / f"{stem}-page-{start//per_page+1:02d}.png"
        canvas.save(file)
        pages.append({"path": str(file), "sha256": sha(file)})
    return pages


def panel(images, label, scale=2):
    pair = np.concatenate(images, axis=1)
    pair = cv2.resize(pair, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    image = Image.new("RGB", (pair.shape[1], pair.shape[0]+24), "white")
    ImageDraw.Draw(image).text((6, 5), label, fill="black")
    image.paste(Image.fromarray(cv2.cvtColor(pair, cv2.COLOR_BGR2RGB)), (0, 24))
    return image


def main():
    cv2.setNumThreads(2)
    timeline_path = ROOT / "timeline-raised-1225-1285-fast-draft-v1.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    source_audit = json.loads((OUT / "source-audit.json").read_text(encoding="utf-8"))
    layer = raised_caption_layer()
    x0, y0, x1, y1 = REGION
    raw = OUT / "raw"
    raw.mkdir(exist_ok=True)
    panels, underlay_panels, rows = [], [], []
    assets = {}
    for record in source_audit["rows"]:
        frame = record["frame"]
        source = cv2.imread(record["source_png"])
        if bgrsha(source) != record["actual_source_bgr_sha256"]:
            raise ValueError(f"Actual source evidence changed at {frame}")
        exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = timeline["assets"][exposure["cel"]]
        if exposure["cel"] not in assets:
            assets[exposure["cel"]] = (compositor.read_image(ROOT / asset["source_reference"]),
                                       compositor.read_image(ROOT / asset["path"]))
        reference, generated = assets[exposure["cel"]]
        source_crop = source[y0:y1, x0:x1]
        captured = {}
        restore = compositor.restore_raised_captions

        def wrapped(output, original, current_frame, character_mask=None):
            before = output[y0:y1, x0:x1].copy()
            edited = np.any(before != source_crop, axis=2)
            new_character = character_mask[y0:y1, x0:x1] != 0
            weights = np.array((.114, .587, .299), np.float32)
            luma = before.astype(np.float32) @ weights
            fg_luma = layer["foreground_bgr"] @ weights
            color_gap = np.max(np.abs(before.astype(np.float32)-layer["foreground_bgr"]), axis=2)
            halo = layer["contrast_edge_support"] & edited & new_character & (np.abs(luma-fg_luma) < 38) & (color_gap < 60)
            result, mask = restore(output, original, current_frame, character_mask)
            after = result[y0:y1, x0:x1]
            changed = np.any(before != after, axis=2)
            support = (layer["alpha"] > 0) | layer["contrast_edge_support"]
            npz = raw / f"f{frame:04d}-caption-masks.npz"
            np.savez_compressed(npz, source_core=layer["source_core"], donor_alpha=layer["alpha"],
                                actual_new_subject=new_character, predicted_fixed_1px_halo=halo,
                                actual_declared_caption_mask=mask[y0:y1, x0:x1],
                                caption_changed_pixels=changed, source_untouched_before_caption=~edited)
            captured.update({"caption_masks_npz": str(npz), "caption_masks_sha256": sha(npz),
                "caption_core_pixels": int(layer["source_core"].sum()),
                "caption_changed_pixels": int(changed.sum()), "halo_pixels": int(halo.sum()),
                "halo_outside_explicit_new_subject_pixels": int(np.count_nonzero(halo & ~new_character)),
                "caption_changed_outside_registered_alpha_or_1px_ring_pixels": int(np.count_nonzero(changed & ~support)),
                "caption_changed_previously_untouched_source_pixels": int(np.count_nonzero(changed & ~edited))})
            underlay_panels.append(panel([before, after], f"f{frame}: ACTUAL NEW SUBJECT BEFORE TEXT | SOURCE GLYPHS + BOUNDED 1px EDGE"))
            return result, mask

        with patch.object(compositor, "restore_raised_captions", side_effect=wrapped):
            output, _, masks = compositor.compose(source, reference, generated, exposure.get("source_matrix"),
                asset["source_frame"], Path(asset["path"]).name, frame)
        file = raw / f"f{frame:04d}-composite.png"
        cv2.imwrite(str(file), output)
        cv2.imwrite(str(raw / f"f{frame:04d}-masks.png"), masks)
        observed = layer["source_core"] & cream_glyph_candidate(source_crop)
        delta = np.max(cv2.absdiff(output[y0:y1, x0:x1], source_crop), axis=2)
        caption_declared = np.all(masks[y0:y1, x0:x1] == (245, 95, 180), axis=2)
        generic = np.all(masks == (80, 245, 90), axis=2)
        rows.append({**record, "cel": exposure["cel"], "asset": asset["path"],
            "asset_source_frame": asset["source_frame"], "asset_sha256": sha(ROOT / asset["path"]),
            "composite_png": str(file), "composite_png_sha256": sha(file), "composite_bgr_sha256": bgrsha(output),
            **captured, "observed_source_core_pixels": int(observed.sum()),
            "observed_source_core_not_exact_pixels": int(np.count_nonzero(observed & (delta != 0))),
            "declared_caption_outside_support_pixels": int(np.count_nonzero(caption_declared & ~((layer["alpha"] > 0) | layer["contrast_edge_support"]))),
            "generic_non_yellow_pixels": int(np.count_nonzero(generic & (cv2.dilate(compositor.yellow_graphics(source), np.ones((7,7), np.uint8)) == 0))),
            "composite_changes_outside_all_declared_masks_pixels": int(np.count_nonzero(np.any(output != source, axis=2) & np.all(masks == 0, axis=2)))})
        panels.append(panel([source_crop, output[y0:y1, x0:x1]], f"f{frame}: ACTUAL SOURCE | RAW CURRENT COMPOSITE {Path(asset['path']).name}"))
    report = {"scope_half_open": [1225, 1285], "actual_source_count": len(rows),
        "timeline": str(timeline_path), "timeline_sha256": sha(timeline_path),
        "source_audit_sha256": sha(OUT / "source-audit.json"), "donor": str(DONOR),
        "donor_sha256": layer["donor_sha256"], "phase_donor_sha256": layer["phase_donor_sha256"],
        "registered_region_xyxy": REGION, "foreground_bgr": layer["foreground_bgr"].tolist(),
        "source_core_pixels": int(layer["source_core"].sum()), "alpha_support_pixels": int(np.count_nonzero(layer["alpha"])),
        "contrast_ring_pixels": int(layer["contrast_edge_support"].sum()),
        "reconstruction": layer["reconstruction"], "contrast_policy": layer["contrast_edge_policy"],
        "generic_foreground_policy": "[1225,1285) only source yellow graphics; no generic pale clothing/collar source recovery.",
        "implementation_sha256": {str(p): sha(p) for p in [ROOT / "compose.py", ROOT / "raised_caption_layers.py", Path(__file__)]},
        "rows": rows, "source_and_composite_caption_pages": write_pages(panels, "raw-caption"),
        "new_subject_before_and_after_caption_pages": write_pages(underlay_panels, "new-subject-caption"),
        "artistic_acceptance": False, "encoded_caption_review": "not_yet_performed"}
    path = OUT / "composite-audit.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "count": len(rows),
        "source_core_nonexact_max": max(r["observed_source_core_not_exact_pixels"] for r in rows),
        "halo_range": [min(r["halo_pixels"] for r in rows), max(r["halo_pixels"] for r in rows)],
        "previously_untouched_source_changed_max": max(r["caption_changed_previously_untouched_source_pixels"] for r in rows),
        "changed_outside_all_declared_max": max(r["composite_changes_outside_all_declared_masks_pixels"] for r in rows)}, indent=2))


if __name__ == "__main__":
    main()
