"""Register inspected mattes and source-visible donor pixels, never painted glyphs."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from compose import read_image
from review_fullpv_root_repairs import REPAIRS
from title_layers import phase, title_character_mask

ROOT = Path(__file__).resolve().parent


def spatial_flat_donors(source, old, unresolved):
    hsv = cv2.cvtColor(source, cv2.COLOR_BGR2HSV)
    eligible = ((hsv[:, :, 0] >= 119) & (hsv[:, :, 0] <= 134)
                & (hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 210) & (old == 0))
    samples = source[eligible]
    if len(samples) < 300000 or np.max(np.std(samples.astype(float), axis=0)) >= 8:
        raise ValueError("Spatial background donors require a verified flat lavender shot")
    coordinates = np.zeros(old.shape, np.uint16)
    repaired = source.copy()
    for y in np.flatnonzero(np.any(unresolved, axis=1)):
        xs = np.flatnonzero(unresolved[y])
        visible = np.flatnonzero(eligible[y])
        if not len(visible):
            raise ValueError(f"No source-visible flat background on row {y}")
        right = np.searchsorted(visible, xs).clip(0, len(visible)-1)
        left = (right-1).clip(0, len(visible)-1)
        choose = np.where(abs(visible[left]-xs) < abs(visible[right]-xs), left, right)
        donor_x = visible[choose]
        repaired[y, xs] = source[y, donor_x]
        coordinates[y, xs] = donor_x
    return repaired, coordinates


def record(path):
    return {"path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    refs = {c["frame"]: ROOT / c["reference"] for c in source_map["cels"]}
    donors = {frame: (read_image(ref), title_character_mask(read_image(ref), margin=6))
              for frame, ref in refs.items() if 1296 <= frame <= 1497}
    target = ROOT / "qa/title-source-layers"
    target.mkdir(exist_ok=True)
    registry = {"version": 1, "accepted": False,
                "policy": "Exact current source outside character; nearest original visible background inside vacated silhouette. Generated reconstruction is limited to unobserved revealed pixels and separately identified.",
                "assets": {}}
    reconstruction_path = ROOT / "generated/title-background-reconstruction-v1.png"
    reconstruction = read_image(reconstruction_path)
    selected = {frame: name for frame, name in REPAIRS.items() if frame >= 1300}
    for frame in refs:
        asset = ROOT / "generated" / f"fine-f{frame:04d}.png"
        if 1296 <= frame <= 1497 and frame != 1380 and asset.exists():
            selected.setdefault(frame, asset.name)
    choices = json.loads((ROOT / "asset_selections.json").read_text(encoding="utf-8"))
    for choice in choices["selections"]:
        frame = choice["source_frame"]
        if 1296 <= frame <= 1497:
            if choice["path"]:
                selected[frame] = Path(choice["path"]).name
            else:
                selected.pop(frame, None)
    registrations = [(frame, name, frame, phase(frame)) for frame, name in sorted(selected.items())]
    if 1296 in selected:
        registrations.append((1296, selected[1296], 1299, "title"))
    for frame, name, background_frame, shot_phase in registrations:
        asset = ROOT / "generated" / name
        source, generated = read_image(refs[background_frame]), read_image(asset)
        old, new = title_character_mask(source, margin=6), title_character_mask(generated)
        background, known = source.copy(), (old == 0).astype(np.uint8)*255
        provenance = np.full(old.shape, background_frame, dtype=np.uint16)
        provenance[old != 0] = 65535
        same_phase = [f for f in donors if phase(f) == shot_phase]
        for donor_frame in sorted(same_phase, key=lambda value: abs(value-background_frame)):
            donor, mask = donors[donor_frame]
            take = (known == 0) & (mask == 0)
            background[take] = donor[take]
            known[take] = 255
            provenance[take] = donor_frame
        unresolved = (old != 0) & (new == 0) & (known == 0)
        diagnostic = source.copy()
        diagnostic[unresolved] = (0, 0, 255)
        cv2.imwrite(str(target / f"f{frame:04d}-{shot_phase}-unobserved.jpg"), diagnostic[570:810, 710:1190])
        reconstructed = np.zeros(old.shape, np.uint8)
        spatial_coordinates = np.zeros(old.shape, np.uint16)
        spatial_count = 0
        if shot_phase == "title":
            reconstructed[unresolved] = 255
            background[unresolved] = reconstruction[unresolved]
            known[unresolved] = 128
            provenance[unresolved] = 65534
        elif np.any(unresolved):
            # Preserve each source donor's exact row and column for audit.
            spatial, spatial_coordinates = spatial_flat_donors(source, old, unresolved)
            background[unresolved] = spatial[unresolved]
            known[unresolved] = 64
            provenance[unresolved] = 65533
            spatial_count = int(np.count_nonzero(unresolved))
        paths = {}
        for role, image in [("source_mask", old), ("new_mask", new),
                            ("background", background), ("background_known", known),
                            ("provenance", provenance), ("reconstructed", reconstructed),
                            ("spatial_donor_x", spatial_coordinates)]:
            path = target / f"f{frame:04d}-{shot_phase}-{role}.png"
            cv2.imwrite(str(path), image)
            paths[role] = record(path)
        entry = {"source_frame": frame, "asset": record(asset),
            **paths, "unobserved_visible_pixels": 0,
            "phase": shot_phase, "background_source_frame": background_frame,
            "reconstructed_visible_pixels": int(np.count_nonzero(reconstructed)),
            "spatial_donor_visible_pixels": spatial_count,
            "reconstruction_asset": record(reconstruction_path),
            "donor_frames": sorted(same_phase), "review": "source_donor_matte_static_pending",
            "accepted": False}
        if background_frame == frame:
            registry["assets"][name] = entry
        else:
            registry["assets"][name].setdefault("phase_variants", {})[shot_phase] = entry
    (ROOT / "title_layer_registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print(json.dumps({name: row["unobserved_visible_pixels"] for name, row in registry["assets"].items()}))


if __name__ == "__main__":
    main()
