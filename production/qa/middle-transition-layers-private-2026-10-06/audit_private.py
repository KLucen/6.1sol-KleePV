"""Private 24-frame composition evidence and narrowly scoped pixel oracles."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

import middle_transition_layers_private as layer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TIMELINE = ROOT / "timeline-middle-2121-2145-oct6-draft-v1.json"
BASELINE = ROOT / "qa/middle-next-2026-10-06/generic-baseline"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def page(rows, number):
    width, height = 530, 102
    output = np.full((35 + len(rows) * 127, width * 3, 3), 248, np.uint8)
    cv2.putText(output, "SOURCE / GENERIC BASELINE / PRIVATE CURRENT / NATIVE PIXELS", (12, 24),
                cv2.FONT_HERSHEY_SIMPLEX, .55, (25, 25, 25), 1, cv2.LINE_AA)
    for index, (frame, source, generic, private) in enumerate(rows):
        y = 35 + index * 127
        cv2.putText(output, f"f{frame:04d}", (12, y + 17), cv2.FONT_HERSHEY_SIMPLEX, .5,
                    (25, 25, 25), 1, cv2.LINE_AA)
        for column, image in enumerate((source, generic, private)):
            output[y + 23:y + 23 + height, column * width:(column + 1) * width] = image[950:1052, 695:1225]
    path = HERE / f"caption-native-page-{number:02d}.png"
    cv2.imwrite(str(path), output)
    return str(path.relative_to(ROOT))


def main():
    timeline = json.loads(TIMELINE.read_text(encoding="utf-8"))
    source_metadata = ROOT / "source_meta.json"
    metadata = json.loads(source_metadata.read_text(encoding="utf-8"))
    source_path = Path(metadata["source"])
    relevant_assets = {timeline["assets"][e["cel"]]["path"] for e in timeline["output_exposures"]}
    paths = [source_path, source_metadata, ROOT / "source_map.json", TIMELINE]
    paths.extend(ROOT / name for name in sorted(relevant_assets))
    frozen = {str(path): sha(path) for path in paths}
    if frozen[str(source_path)] != metadata["sha256"]:
        raise ValueError("Original identity changed")
    if timeline["source_pts"] != metadata["pts"][2121:2145]:
        raise ValueError("Original exposure PTS changed")
    for exposure in timeline["output_exposures"]:
        if exposure["source_matrix"] != [[1., 0., 0.], [0., 1., 0.]]:
            raise ValueError("Private layer only supports source identity registration")
    canonical = {e["start"] for e in timeline["output_exposures"]}
    cache = {}
    records, rows, pages = [], [], []
    for frame in range(2121, 2145):
        exposure = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = timeline["assets"][exposure["cel"]]
        name = Path(asset["path"]).name
        if name not in cache:
            cache[name] = cv2.resize(cv2.imread(str(ROOT / asset["path"])), (1920, 1080),
                                     interpolation=cv2.INTER_LANCZOS4)
        generated = cache[name]
        source = cv2.imread(str(HERE / "source" / f"f{frame:04d}.png"))
        generic = cv2.imread(str(BASELINE / f"f{frame:04d}-composite.png"))
        if generic is None:
            raise ValueError(f"Missing preserved generic baseline at {frame}")
        output, masks = layer.compose_private(source, generated, frame, name)
        cv2.imwrite(str(HERE / f"f{frame:04d}-private.png"), output)
        outside = ~masks["ownership"]
        interior = (cv2.erode(masks["new"], np.ones((5, 5), np.uint8)) != 0) & ~masks["caption"]
        # Actual original foreground effects own overlapping body pixels.
        interior &= ~masks.get("effects", np.zeros(interior.shape, bool))
        record = {
            "frame": frame, "asset": name, "cel": exposure["cel"],
            "outside_ownership_mismatched_pixels": int(np.any(output != source, axis=2)[outside].sum()),
            "generated_interior_mismatched_pixels": int(np.any(output != generated, axis=2)[interior].sum()),
            "old_pixels": int(np.count_nonzero(masks["old"])),
            "new_pixels": int(np.count_nonzero(masks["new"])),
            "reconstructed_vacated_pixels": int(np.count_nonzero(masks["vacated"])),
            "ownership_pixels": int(np.count_nonzero(masks["ownership"]))
        }
        if frame >= 2143:
            h, s, v = cv2.split(cv2.cvtColor(generated, cv2.COLOR_BGR2HSV))
            observed_face = np.zeros((1080, 1920), bool)
            observed_face[360:710, 1200:1490] = True
            observed_face &= (h >= 95) & (h <= 117) & (s >= 40) & (s < 150) & (v > 210)
            observed_face &= ~masks["caption"]
            record["observed_cold_face_pixels"] = int(observed_face.sum())
            record["observed_cold_face_missing_from_new_mask"] = int(np.count_nonzero(observed_face & (masks["new"] == 0)))
            record["observed_cold_face_generated_pixel_mismatches"] = int(np.any(output != generated, axis=2)[observed_face].sum())
        if frame in canonical:
            cv2.imwrite(str(HERE / f"f{frame:04d}-whole-source-generic-private.png"),
                        np.concatenate((source, generic, output), axis=1))
            support = np.zeros((1080, 1920, 3), np.uint8)
            support[..., 0] = masks["old"]
            support[..., 1] = masks["new"]
            support[..., 2] = masks["vacated"].astype(np.uint8)*255
            cv2.imwrite(str(HERE / f"f{frame:04d}-ownership-native.png"), support)
        rows.append((frame, source, generic, output))
        if len(rows) == 8 or frame == 2144:
            pages.append(page(rows, len(pages) + 1))
            rows = []
        records.append(record)
        print(json.dumps(record), flush=True)
    failures = [r for r in records if r["outside_ownership_mismatched_pixels"]
                or r["generated_interior_mismatched_pixels"]
                or r.get("observed_cold_face_missing_from_new_mask", 0)
                or r.get("observed_cold_face_generated_pixel_mismatches", 0)]
    after = {str(path): sha(path) for path in paths}
    report = {
        "accepted": False, "source_interval": [2121, 2145], "frames": 24,
        "registered_cels": len(canonical), "registration": layer.REGISTERED,
        "original_pts_verified": True, "frozen_input_hashes": frozen,
        "frozen_inputs_unchanged": frozen == after,
        "technical_oracle_pass": not failures and frozen == after,
        "failures": failures, "frame_records": records, "caption_pages": pages,
        "reconstruction": "Only vacated original character support and old glyph extent. Sky is a fitted current-source gradient, not an observed clean plate; wipe sky populations are estimated separately from actual visible source sky.",
        "outside_ownership_oracle": "Every byte outside declared ownership equals the actual source. This does not prove the ownership boundary itself is correct.",
        "body_oracle": "Generated eroded interior excluding foreground caption/effect support equals the selected wholecel. An additional observed cool-face native ROI oracle detects the known bright-sky hole failure.",
        "native_static_review": "pending actual view of 10 whole/private canonical frames and all 24 caption crops",
        "actual_speed_review": "not performed", "shared_hook": "not installed by this private audit"
    }
    (HERE / "private-24-frame-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"technical_oracle_pass": report["technical_oracle_pass"], "failures": len(failures)}))


if __name__ == "__main__":
    main()
