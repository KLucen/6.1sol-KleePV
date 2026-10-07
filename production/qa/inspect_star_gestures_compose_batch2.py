"""Private static evidence for existing compose behavior; no production edits."""

from pathlib import Path
import hashlib
import json
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compose import compose, graphics_mask, read_image, subject_mask

OUT = ROOT / "qa/fast-fullpv-star-gestures-2026-10-04/compose-static"
CAPTION_RECT = (740, 850, 1260, 1065)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label_panel(image, label):
    panel = Image.new("RGB", (image.width, image.height + 26), "#202024")
    panel.paste(image, (0, 26))
    ImageDraw.Draw(panel).text((8, 7), label, fill="white")
    return panel


def main():
    cv2.setNumThreads(2)
    OUT.mkdir(parents=True, exist_ok=True)
    shared = [ROOT / "compose.py", ROOT / "asset_selections.json"]
    shared_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in shared}
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text())
    proposal = json.loads((OUT.parent / "draft-proposal.json").read_text())
    private = {s["source_frame"]: s for s in proposal["selections"]}
    cels = []
    first_missing = None
    for cel in manifest["cels"]:
        frame = cel["canonical_source_frame"]
        if frame < 1008:
            continue
        selected = private.get(frame) or cel["selected_asset"]
        if not selected:
            first_missing = frame
            break
        cels.append((cel, selected))
    rows, panels, caption_panels = [], [], []
    for cel, selected in cels:
        frame = cel["canonical_source_frame"]
        source = read_image(ROOT / cel["source_reference"])
        generated = read_image(ROOT / selected["path"])
        result, diagnostic, masks = compose(
            source, source, generated,
            asset_source_frame=frame,
            asset_name=Path(selected["path"]).name,
            current_frame=frame,
        )
        path = OUT / f"f{frame:04d}-existing-compose.png"
        mask_path = OUT / f"f{frame:04d}-existing-masks.png"
        cv2.imwrite(str(path), result)
        cv2.imwrite(str(mask_path), masks)
        original = subject_mask(source) != 0
        new = subject_mask(generated) != 0
        overlay = graphics_mask(source) != 0
        source_only = original & ~new
        restored_old_candidate = source_only & overlay
        exact_source = np.all(source == result, axis=2)
        x0, y0, x1, y1 = CAPTION_RECT
        caption_pair = np.concatenate([
            source[y0:y1, x0:x1], result[y0:y1, x0:x1]
        ], axis=1)
        caption_path = OUT / f"f{frame:04d}-native-caption-pair.png"
        cv2.imwrite(str(caption_path), caption_pair)
        caption_large = cv2.resize(caption_pair, None, fx=2, fy=2,
                                   interpolation=cv2.INTER_NEAREST)
        caption_panels.append(label_panel(
            Image.fromarray(cv2.cvtColor(caption_large, cv2.COLOR_BGR2RGB)),
            f"f{frame:04d} source | existing compose, native caption crop x2",
        ))
        pair = Image.fromarray(cv2.cvtColor(diagnostic, cv2.COLOR_BGR2RGB))
        pair.thumbnail((1440, 405))
        panels.append(label_panel(pair, f"f{frame:04d} source | existing compose UNACCEPTED"))
        rows.append({
            "source_cel": cel["cel"], "source_frame": frame,
            "source_exposures": cel["source_exposures"],
            "asset": selected["path"],
            "selection_origin": "private_proposal" if frame in private else "existing_manifest",
            "source_reference": cel["source_reference"],
            "source_sha256": sha256(ROOT / cel["source_reference"]),
            "asset_sha256": sha256(ROOT / selected["path"]),
            "composite": str(path.relative_to(ROOT)),
            "composite_sha256": sha256(path),
            "masks": str(mask_path.relative_to(ROOT)),
            "native_caption_pair": str(caption_path.relative_to(ROOT)),
            "original_only_graphics_restored_pixels": int(np.count_nonzero(restored_old_candidate & exact_source)),
            "note": "Candidate pixels are diagnostic only, not proof of old-subject residue; manual crop review required.",
        })
    pages = {"source_composite": [], "native_caption": []}
    for kind, items in (("source_composite", panels), ("native_caption", caption_panels)):
        for start in range(0, len(items), 4):
            group = items[start:start + 4]
            page = Image.new("RGB", (group[0].width, sum(p.height for p in group)), "#202024")
            top = 0
            for panel in group:
                page.paste(panel, (0, top))
                top += panel.height
            path = OUT / f"{kind}-page-{start // 4 + 1:02d}.png"
            page.save(path)
            pages[kind].append(str(path.relative_to(ROOT)))
    report = {
        "owner": "star_gestures_batch2", "accepted": False,
        "interval": [1008, first_missing], "first_missing_after_private_proposal": first_missing,
        "canonical_static_cels_checked": len(rows),
        "private_proposal_only": True,
        "public_mapping_mutated": False, "compose_mutated": False,
        "shared_files_sha256_before": shared_hashes,
        "shared_files_sha256_after": {str(p.relative_to(ROOT)): sha256(p) for p in shared},
        "temporal_review": "not_performed", "encoded_video_review": "not_performed",
        "artistic_acceptance": "not_granted", "manual_review": "pending",
        "scope": "Canonical source refs only; no all-exposure actual-video caption guarantee.",
        "rows": rows, "pages": pages,
    }
    (OUT / "evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"static_cels": len(rows), "interval": report["interval"],
                      "pages": pages, "report": str(OUT / "evidence.json")}))


if __name__ == "__main__":
    main()
