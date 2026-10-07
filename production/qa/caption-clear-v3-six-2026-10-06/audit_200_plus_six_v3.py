"""Keep the frozen 206 oracle, accepting only six independently proved CN fixes."""

import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from compose import compose, read_image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bgr_sha(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    cv2.setNumThreads(2)
    oracle_path = ROOT / "qa/oct6-star-extended-integration/shared-35-cyan97-old74-regression.json"
    original = read_json(oracle_path)
    assert original["all_raw_checks_pass"] and len(original["rows"]) == 206
    oracle = {row["frame"]: row for row in original["rows"]}
    paths = {
        "star": ROOT / "timeline-star-1008-1043-authorized-draft-v1.json",
        "cyan": ROOT / "timeline-cyan-911-1008-fast-draft-v1.json",
        "dance": ROOT / "timeline-dance-812-911-fast-draft-v11.json",
        "raised": ROOT / "timeline-raised-1225-1285-fast-draft-v1.json",
    }
    timelines = {key: read_json(path) for key, path in paths.items()}
    proof_path = HERE / "six-v3-and-prior29-technical-report.json"
    proof = read_json(proof_path)
    assert proof["raw_technical_pass"] and proof["prior_29_frames_exact"]
    relevant = list(original["relevant_code_sha256_after"])
    relevant += ["star_extended_captions.py", "qa/caption-clear-v2-2026-10-06/long-f3402-cn-clear-real-caption-v2.npz"]
    before = {path: sha(ROOT / path) for path in relevant}
    old_oracle_sha = sha(oracle_path)
    metadata = read_json(ROOT / "source_meta.json")
    capture = cv2.VideoCapture(metadata["source"])
    rows, failed, cache = [], [], {}
    for frame in range(max(oracle) + 1):
        ok, source = capture.read()
        if not ok:
            raise RuntimeError(frame)
        if frame not in oracle:
            continue
        previous = oracle[frame]
        scope = previous["scope"]
        timeline = timelines[scope]
        span = next(row for row in timeline["output_exposures"] if row["start"] <= frame < row["end"])
        asset = timeline["assets"][span["cel"]]
        if asset["path"] not in cache:
            cache[asset["path"]] = (read_image(ROOT / asset["source_reference"]), read_image(ROOT / asset["path"]))
        reference, generated = cache[asset["path"]]
        result, _, _ = compose(source, reference, generated, span["source_matrix"], asset["source_frame"], Path(asset["path"]).name, frame)
        row = {"frame": frame, "scope": scope, "asset": asset["path"],
               "source_bgr_sha256": bgr_sha(source), "asset_sha256": sha(ROOT / asset["path"]),
               "composite_bgr_sha256": bgr_sha(result), "accepted": False}
        source_asset_exact = (row["source_bgr_sha256"] == previous["source_bgr_sha256"]
                              and row["asset_sha256"] == previous["asset_sha256"]
                              and asset["path"].replace("\\", "/") == previous["asset"].replace("\\", "/"))
        if 1037 <= frame < 1043:
            expected = cv2.imread(str(HERE / "v3-raw" / f"f{frame}-v3.png"))
            old_image = cv2.imread(str(ROOT / "qa/oct6-star-extended-integration" / f"f{frame}-shared-raw.png"))
            different = np.any(result != old_image, axis=2)
            caption_rows = np.zeros(different.shape, bool)
            caption_rows[1002:1047, 676:1213] = True
            outside_cn = int(np.count_nonzero(different & ~caption_rows))
            row.update(expectation="authorized six-frame complete original CN change", changed_pixels=int(different.sum()),
                       outside_registered_cn_errors=outside_cn, complete_cn_v3_exact=np.array_equal(result, expected),
                       japanese_and_body_exact=outside_cn == 0)
            row["pass"] = source_asset_exact and row["complete_cn_v3_exact"] and outside_cn == 0 and different.any()
        else:
            row.update(expectation="immutable frozen composite", exact_original_oracle=row["composite_bgr_sha256"] == previous["composite_bgr_sha256"])
            row["pass"] = source_asset_exact and row["exact_original_oracle"]
        row["pass"] = bool(row["pass"])
        rows.append(row)
        if not row["pass"]:
            failed.append(row)
        if len(rows) % 20 == 0:
            print(json.dumps({"processed": len(rows), "total": 206, "failed": len(failed)}), flush=True)
    capture.release()
    after = {path: sha(ROOT / path) for path in relevant}
    unchanged = [row for row in rows if row["expectation"] == "immutable frozen composite"]
    allowed = [row for row in rows if row["expectation"] != "immutable frozen composite"]
    assert len(unchanged) == 200 and len(allowed) == 6
    frozen_retained = old_oracle_sha == sha(oracle_path)
    passed = not failed and before == after and frozen_retained
    report = {"accepted": False, "total_frames": 206, "unchanged_frozen_frames": 200,
              "authorized_cn_changed_frames": 6, "rows": rows, "failed": failed,
              "all_expected_raw_checks_pass": passed,
              "shared_code_unchanged_during_audit": before == after,
              "relevant_code_sha256_before": before, "relevant_code_sha256_after": after,
              "historical_206_oracle": str(oracle_path), "historical_oracle_sha256": old_oracle_sha,
              "historical_oracle_not_modified": frozen_retained, "six_body_japanese_proof_sha256": sha(proof_path),
              "actual_speed_or_artistic_acceptance": False}
    path = HERE / "shared-200-unchanged-plus-six-cn-v3-regression.json"
    assert not path.exists(), "Retain the saved split regression evidence"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"total": 206, "unchanged": 200, "allowed_cn_changes": 6, "pass": passed, "sha256": sha(path)}))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
