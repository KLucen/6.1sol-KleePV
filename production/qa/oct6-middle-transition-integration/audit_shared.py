"""Current frozen 206-frame regression and every newly registered exposure."""

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
    target = HERE / "shared-prior206-middle24-regression.json"
    if target.exists():
        raise FileExistsError("Keep the previous integration report")
    baseline_path = ROOT / "qa/caption-clear-v3-six-2026-10-06/shared-200-unchanged-plus-six-cn-v3-regression.json"
    baseline = read_json(baseline_path)
    assert baseline["all_expected_raw_checks_pass"] and len(baseline["rows"]) == 206
    oracle = {r["frame"]: r for r in baseline["rows"]}
    timelines = {key: read_json(ROOT / path) for key, path in {
        "star": "timeline-star-1008-1043-authorized-draft-v1.json",
        "cyan": "timeline-cyan-911-1008-fast-draft-v1.json",
        "dance": "timeline-dance-812-911-fast-draft-v11.json",
        "raised": "timeline-raised-1225-1285-fast-draft-v1.json",
        "middle": "timeline-middle-2121-2145-oct6-draft-v1.json"
    }.items()}
    private = ROOT / "qa/middle-transition-layers-private-2026-10-06"
    private_report = read_json(private / "v5-foreground-ownership-audit/private-24-frame-report.json")
    root_review = read_json(private / "root-v5-static-review.json")
    assert private_report["technical_oracle_pass"] and root_review["private_gate_ready_for_exact_draft_registration"]
    code = [ROOT / name for name in baseline["relevant_code_sha256_after"]]
    code += [ROOT / "compose.py", ROOT / "middle_transition_layers.py"]
    code += sorted(private.glob("middle_transition_layers*.py"))
    code += [private / "middle-same-line-f2141-real-caption.npz"]
    frozen = {str(path.relative_to(ROOT)): sha(path) for path in code}
    baseline_sha = sha(baseline_path)
    metadata = read_json(ROOT / "source_meta.json")
    capture = cv2.VideoCapture(metadata["source"])
    rows, cache = [], {}
    for frame in range(2145):
        ok, source = capture.read()
        if not ok:
            raise RuntimeError(frame)
        if frame not in oracle and frame < 2121:
            continue
        scope = oracle[frame]["scope"] if frame in oracle else "middle"
        timeline = timelines[scope]
        span = next(e for e in timeline["output_exposures"] if e["start"] <= frame < e["end"])
        asset = timeline["assets"][span["cel"]]
        if asset["path"] not in cache:
            cache[asset["path"]] = (read_image(ROOT / asset["source_reference"]), read_image(ROOT / asset["path"]))
        reference, generated = cache[asset["path"]]
        output, _, _ = compose(source, reference, generated, span["source_matrix"], asset["source_frame"], Path(asset["path"]).name, frame)
        row = {"frame": frame, "scope": scope, "asset": asset["path"],
               "source_bgr_sha256": bgr_sha(source), "asset_sha256": sha(ROOT / asset["path"]),
               "composite_bgr_sha256": bgr_sha(output), "accepted": False}
        if scope == "middle":
            expected_source = cv2.imread(str(private / "source" / f"f{frame:04d}.png"))
            expected = cv2.imread(str(private / "v5-foreground-ownership-audit" / f"f{frame:04d}-private.png"))
            row["original_source_exact"] = np.array_equal(source, expected_source)
            row["private_gate_output_exact"] = np.array_equal(output, expected)
            row["pass"] = bool(row["original_source_exact"] and row["private_gate_output_exact"])
        else:
            previous = oracle[frame]
            row["pass"] = all(row[key] == previous[key] for key in (
                "source_bgr_sha256", "asset_sha256", "composite_bgr_sha256"))
        rows.append(row)
        if len(rows) % 20 == 0:
            print(json.dumps({"processed": len(rows), "failed": sum(not r["pass"] for r in rows)}), flush=True)
    capture.release()
    after = {str(path.relative_to(ROOT)): sha(path) for path in code}
    prior = [r for r in rows if r["scope"] != "middle"]
    middle = [r for r in rows if r["scope"] == "middle"]
    assert len(prior) == 206 and len(middle) == 24
    failed = [r for r in rows if not r["pass"]]
    passed = not failed and frozen == after and baseline_sha == sha(baseline_path)
    report = {"accepted": False, "total_frames": 230, "unchanged_prior_frames": 206,
              "new_registered_middle_frames": 24, "all_raw_checks_pass": passed,
              "rows": rows, "failures": failed,
              "code_unchanged_during_audit": frozen == after,
              "relevant_sha256_before": frozen, "relevant_sha256_after": after,
              "historical_v3_oracle_unchanged": baseline_sha == sha(baseline_path),
              "historical_v3_oracle_sha256": baseline_sha,
              "private_gate_report_sha256": sha(private / "v5-foreground-ownership-audit/private-24-frame-report.json"),
              "root_static_review_sha256": sha(private / "root-v5-static-review.json"),
              "actual_speed_or_artistic_acceptance": False}
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"pass": passed, "frames": len(rows), "sha256": sha(target)}))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
