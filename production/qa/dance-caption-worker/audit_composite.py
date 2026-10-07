"""Inspect actual selected cels and source-derived caption integration at native size."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import compose as compositor
from dance_caption_layers import REGION
from test_dance_caption_integration import REFERENCES, selected_cases

OUT = Path(__file__).resolve().parent
PHASE_REPORT = OUT/"phase-and-layer-audit.json"
BOTTOM = (700, 890, 1260, 1075)
SUSPECT = (778, 924, 800, 951)
DETAIL = (750, 910, 850, 960)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crop(image, rect):
    x0, y0, x1, y1 = rect
    return image[y0:y1, x0:x1]


def board(images, labels, zoom=1):
    panels = []
    for image, label in zip(images, labels):
        if zoom != 1:
            image = cv2.resize(image, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_NEAREST)
        panel = Image.new("RGB", (image.shape[1], image.shape[0]+24), "white")
        panel.paste(Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)), (0, 24))
        ImageDraw.Draw(panel).text((4, 5), label, fill="black")
        panels.append(panel)
    out = Image.new("RGB", (sum(p.width for p in panels), panels[0].height), "white")
    left = 0
    for panel in panels:
        out.paste(panel, (left, 0))
        left += panel.width
    return out


def main():
    cv2.setNumThreads(2)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = json.loads((ROOT/"asset_selections.json").read_text(encoding="utf-8"))["selections"]
    selected = {r["source_frame"]: r for r in rows}
    paths = [ROOT/name for name in ("compose.py", "dance_caption_layers.py", "test_dance_caption_integration.py", "asset_selections.json")]
    for frame, name in REFERENCES.items():
        paths.extend([ROOT/"source_refs"/name, ROOT/selected[frame]["path"]])
    provenance = {str(path): sha(path) for path in paths}
    metrics = []
    real_graphics = compositor.graphics_mask

    def without_bottom_graphics(source):
        mask = real_graphics(source).copy()
        mask[910:] = 0
        return mask

    for frame, source, generated, name in selected_cases():
        args = dict(asset_source_frame=frame, asset_name=name, current_frame=frame)
        actual, _, declared = compositor.compose(source, source, generated, **args)
        with patch.object(compositor, "graphics_mask", side_effect=without_bottom_graphics):
            without_band, _, _ = compositor.compose(source, source, generated, **args)
        native = [crop(image, BOTTOM) for image in (source, generated, actual)]
        labels = [f"f{frame:04d} SOURCE NATIVE", f"f{frame:04d} CURRENT SELECTED CEL", f"f{frame:04d} ACTUAL COMPOSITE"]
        native_path = OUT/f"f{frame:04d}-native-bottom-three-panel.png"
        board(native, labels).save(native_path)
        for label, image in zip(("source", "selected", "composite"), native):
            cv2.imwrite(str(OUT/f"f{frame:04d}-native-bottom-{label}.png"), image)
        detail_path = OUT/f"f{frame:04d}-old-boot-overlay-detail-4x.png"
        board([crop(image, DETAIL) for image in (source, generated, actual, without_band)],
              ["SOURCE 4X", "SELECTED 4X", "ACTUAL 4X", "NO BOTTOM OVERLAY 4X"], 4).save(detail_path)
        graphics = real_graphics(source) != 0
        original_subject = compositor.subject_mask(source) != 0
        generated_subject = compositor.subject_mask(generated) != 0
        current_eq_source = np.all(actual == source, axis=2)
        changed = np.any(actual != source, axis=2)
        band_delta = np.max(cv2.absdiff(actual, without_band), axis=2)
        metrics.append({"frame": frame, "selected_path": selected[frame]["path"],
                        "native_crop_rectangle": list(BOTTOM), "native_crop_three_panel": str(native_path),
                        "suspect_rectangle": list(SUSPECT), "old_boot_detail": str(detail_path),
                        "suspect_generic_graphics_pixels": int(np.count_nonzero(crop(graphics, SUSPECT))),
                        "suspect_original_subject_pixels": int(np.count_nonzero(crop(original_subject, SUSPECT))),
                        "suspect_generated_subject_pixels": int(np.count_nonzero(crop(generated_subject, SUSPECT))),
                        "suspect_generic_pixels_equal_original_source": int(np.count_nonzero(crop(graphics & current_eq_source, SUSPECT))),
                        "suspect_pixels_changed_by_disabling_bottom_graphics": int(np.count_nonzero(crop(band_delta > 0, SUSPECT))),
                        "suspect_pixels_changed_gt20_by_disabling_bottom_graphics": int(np.count_nonzero(crop(band_delta > 20, SUSPECT))),
                        "all_frame_pixels_changed_by_disabling_bottom_graphics": int(np.count_nonzero(band_delta > 0)),
                        "undeclared_changed_pixels": int(np.count_nonzero(changed & np.all(declared == 0, axis=2)))})
    tests = subprocess.run([sys.executable, "-m", "unittest", "test_dance_caption_integration", "-v"],
                           cwd=ROOT, capture_output=True, text=True)
    (OUT/"integration-focused-tests.txt").write_text(tests.stdout+tests.stderr, encoding="utf-8")
    report = {"source_frames": list(REFERENCES), "cases": metrics, "provenance_sha256": provenance,
              "inputs_unchanged": all(sha(Path(path)) == digest for path, digest in provenance.items()),
              "integration_tests": {"count": 5, "exit_code": tests.returncode,
                                    "transcript": str(OUT/"integration-focused-tests.txt")},
              "all_32_current_warm_core_inside_donor_alpha": False,
              "full_phase_report": str(PHASE_REPORT),
              "full_phase_report_sha256": sha(PHASE_REPORT),
              "artistic_acceptance": False, "original_speed_watch": "not_performed",
              "manual_observations": "pending_native_crop_inspection",
              "limitations": ["The integration tests do not validate all glyph shapes or final readability.",
                              "The 32-frame warm-core support false item remains; stable donor subsets are not a substitute.",
                              "Comparing with a locally disabled overlay isolates only the generic overlay path, not every possible old-character residue."]}
    (OUT/"actual-composite-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(OUT/"actual-composite-audit.json"), "cases": metrics,
                      "integration_tests": report["integration_tests"],
                      "inputs_unchanged": report["inputs_unchanged"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output.resolve()
    main()
