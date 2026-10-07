"""Add full-width expanded-hand references without replacing the first queue."""

import json
from pathlib import Path

import cv2

from prepare_closeup_refs import OUT, ROOT, crop, digest, local_page, native


def main():
    original_path = OUT / "closeup-source-reference-queue.json"
    output = OUT / "corrected-closeup-source-reference-queue.json"
    if output.exists():
        raise FileExistsError("Corrected queue already saved.")
    report = json.loads(original_path.read_text(encoding="utf-8"))
    regions = [
        ("face", (800, 300, 1160, 685)),
        ("left-open-hand", (165, 80, 525, 480)),
        ("right-open-hand", (1505, 75, 1865, 475)),
        ("left-wide-cuff", (365, 235, 725, 645)),
        ("right-wide-cuff", (1315, 235, 1675, 645)),
        ("hat-left", (670, 45, 1030, 365)),
        ("hat-right", (1030, 45, 1390, 365)),
        ("collar-hair", (815, 595, 1175, 975)),
        ("left-sleeve-folds", (485, 480, 845, 945)),
        ("right-sleeve-folds", (1120, 470, 1480, 935)),
    ]
    for row in report["queue"]:
        frame = row["source_frame"]
        if frame < 1211:
            continue
        earlier = row["before_source_frame"]
        a = cv2.imread(row["before_source"]["path"])
        b = cv2.imread(row["current_source"]["path"])
        prefix = OUT / f"f{earlier:04d}-f{frame:04d}-expanded-v2"
        panels = {}
        for name, panel in zip(["before-wide", "current-wide", "actual-rgb-x4-wide", "dual-contours-wide"], native.panels(a, b)):
            path = prefix.with_name(prefix.name + f"-{name}-native.png")
            panels[name] = crop(panel, (0, 0, 1920, 1080), path)
        pages = []
        for idx, offset in enumerate(range(0, len(regions), 3), 1):
            entries = regions[offset:offset + 3]
            path = prefix.with_name(prefix.name + f"-locals-{idx}-native.png")
            local_page(a, b, earlier, frame, entries, path)
            pages.append({"path": str(path), "sha256": digest(path), "regions": dict(entries), "resized": False})
        row["superseded_crops"] = {"native_face_crop": row["native_face_crop"],
            "native_body_crop": row["native_body_crop"], "native_local_pages": row["native_local_pages"],
            "wide_native_panels": row["wide_native_panels"],
            "reason": "Open palms spread beyond earlier closeup hand ROIs; retained only as historical first preparation."}
        row["native_face_crop"] = crop(b, regions[0][1], OUT / f"f{frame:04d}-expanded-v2-source-face-native.png")
        row["native_body_crop"] = crop(b, (0, 0, 1920, 1080), OUT / f"f{frame:04d}-expanded-v2-source-hands-body-native.png")
        row["wide_native_panels"] = panels
        row["native_local_pages"] = pages
        row["crop_disposition"] = "Full-width expanded open hands, separate palms, wide cuffs and sleeves; original queue files preserved."
    report["first_preparation_queue"] = {"path": str(original_path), "sha256": digest(original_path)}
    report["superseded_targets_first_crop_only"] = [1211, 1216, 1221]
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"corrected_queue": str(output), "sha256": digest(output), "supplemented_frames": [1211, 1216, 1221]}))


if __name__ == "__main__":
    main()
