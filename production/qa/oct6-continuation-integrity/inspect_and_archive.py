"""Private cross-date prompt provenance and selection integrity snapshots only."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ROOT_FRAMES = [1154, 1164, 1172, 1187, 1195, 1199, 1203, 1211, 1216, 1221]
SEALED_ROOT_THIRD_SHA256 = "00e045b0cf53e3b3ea276cb56ba43b748b044c9dddb40a7cbc8863af02466767"
FROZEN = {
    "qa/fast-fullpv-batch2-integrity-2026-10-04/batch2-full-27call-promptset.json": "173f36b5ee4b9fd280b91db09db77c845789ddd5f39a67f58fb9675ae6eef32a",
    "qa/standing-missing-2026-10-05/oct5-full-7call-promptset.json": "1e6372e9e88024bfac931dc462b0f7f5993e7a823b80236b5ca2b6346e814608",
    "qa/star1091-continuation-2026-10-05/full-root-builtin-promptset.json": "28582f48abce8367395ad697a0198b9529a184f0708815f7d011b61aafd62714",
    "qa/continuation-integrity-2026-10-05/full-second-root-builtin-promptset.json": "88bb464617a31ec7b16e5f10b914a2fb0b72827eb820e918154e65467f1313cf",
    "qa/middle-next-missing-2026-10-05/full-builtin-promptset.json": "4161b32cd9e5d698348d5e3ee17838d46795b739e11d6dc1f7d03818d20f6893",
    "source_map.json": "05de0751535d1c627171b81f41a0183bf3990b902d44435bfc8b3120a30caf76",
    "source_meta.json": "a1db00c0d6a74330a72f0aa18e1a8cc34f824c29cf6d4e02e9d7cee7a51232eb",
}
HASH_AUTHORITY = "Historical archive notices/helper constants and previous middle handoff; second7/source-map/meta frozen hashes explicitly reconfirmed by root message on 2026-10-06."
ROOT_NOTICE = "Root confirms third group contains old f1154 plus nine adopted closeup true cels f1164,f1172,f1187,f1195,f1199,f1203v2,f1211,f1216,f1221. Exactly 10 selected true cels, 11 successful builtin calls including unselected f1203v1, across Oct5/6. Root closeups already shared adopted accepted=false."

spec = importlib.util.spec_from_file_location("frozen_root_archive_reader", ROOT / "qa/star1091-continuation-2026-10-05/archive_root_promptset.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def absolute(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def protected_checks():
    return [{"path": str(ROOT / name), "expected_sha256": expected,
             "observed_sha256": digest(ROOT / name), "unchanged": digest(ROOT / name) == expected}
            for name, expected in FROZEN.items()]


def write_new(path, data):
    if path.exists():
        raise FileExistsError("Preserve all earlier sealed archives/snapshots")
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"path": str(path), "sha256": digest(path)}


def check_source_inputs(jobs, manifest, by_frame):
    wanted = {job["source_frame"] for job in jobs}
    decoded = {}
    cap = cv2.VideoCapture(manifest["source"])
    for frame in range(max(wanted) + 1):
        ok, image = cap.read()
        if not ok:
            raise ValueError(f"Sequential source failed f{frame}")
        if frame in wanted:
            canonical = cv2.imread(str(ROOT / by_frame[frame]["source_reference"]))
            decoded[frame] = {"sequential_original_matches_canonical_bgr_exact": bool(np.array_equal(image, canonical)),
                              "canonical_reference": helper.file_record(ROOT / by_frame[frame]["source_reference"]),
                              "decoded_bgr_sha256": sha256(image.tobytes()).hexdigest()}
    cap.release()
    for job in jobs:
        image = cv2.imread(str(absolute(job["reference_roles"][0]["path"])))
        frame = job["source_frame"]
        source = cv2.imread(str(ROOT / by_frame[frame]["source_reference"]))
        decoded[frame].setdefault("whole_current_source_input_checks", []).append(
            {"job": job["id"], "path": job["reference_roles"][0]["path"],
             "canonical_pixels_exact": bool(np.array_equal(image, source))})
    return {"sequential_decode": [0, max(wanted) + 1], "frames": decoded}


def seal_root():
    frozen = protected_checks()
    if not all(row["unchanged"] for row in frozen):
        raise ValueError("Frozen prior/source artifact changed; do not seal")
    manifest = read(ROOT / "full-pv-progress-manifest.json")
    by_frame = {row["canonical_source_frame"]: row for row in manifest["cels"]}
    selections = read(ROOT / "asset_selections.json")["selections"]
    declaration = {}
    for frame in ROOT_FRAMES:
        matching = [row for row in selections if row["source_frame"] == frame and row.get("path")]
        if len(matching) != 1 or matching[0].get("accepted") is not False:
            raise ValueError(f"Expected one unaccepted explicit root selection f{frame}")
        declaration[str(frame)] = matching[0]["path"]
    calls, original_jobs = [], []
    # Deliberately span Oct5/6 rather than filter jobs by a single date.
    for path in sorted((ROOT / "jobs").glob("star-f*.json")):
        if not any(path.name.startswith(f"star-f{frame}-") for frame in ROOT_FRAMES):
            continue
        raw = path.read_bytes()
        job = json.loads(raw)
        original_jobs.append(job)
        calls.append(helper.inspect_job(path, raw, job, by_frame, selections, declaration, True))
    calls.sort(key=lambda c: (c["source_frame"], c["variant_number"] or 0))
    issues = [{"job": c["id"], "issues": c["issues"]} for c in calls if c["issues"]]
    if len(calls) != 11 or len({c["source_frame"] for c in calls}) != 10:
        raise ValueError("Third group must archive exactly 11 outputs / 10 true cels")
    for c in calls:
        if not c["completed_builtin_output_call_evidence"] or len(c["ordered_reference_roles"]) > 5:
            raise ValueError("Missing builtin provenance or invalid reference count")
        if c["observed_selected_at_snapshot_not_acceptance"]:
            s = c["observed_explicit_selection_records"][0]
            if s.get("output_sha256") != c["workspace_output"]["sha256"]:
                issues.append({"job": c["id"], "issues": ["selected_output_sha_mismatch"]})
    source_checks = check_source_inputs(original_jobs, manifest, by_frame)
    if any(not c["sequential_original_matches_canonical_bgr_exact"] or
           any(not r["canonical_pixels_exact"] for r in c["whole_current_source_input_checks"])
           for c in source_checks["frames"].values()):
        issues.append({"scope": "source", "issues": ["source_decode_or_input_mismatch"]})
    if issues:
        path = OUT / "root-third-prompt-archive-validation-issues.json"
        print(json.dumps(write_new(path, {"issues": issues, "calls": calls, "source_checks": source_checks})))
        raise ValueError(json.dumps(issues))
    chosen_exposure_frames = sum(e["end"] - e["start"] for f in ROOT_FRAMES for e in by_frame[f]["source_exposures"])
    report = {"snapshot_utc": datetime.now(timezone.utc).isoformat(), "frozen": True,
              "archive_phase": "final_after_generation_and_root_adoption",
              "root_final_notice_original": ROOT_NOTICE,
              "frozen_hash_authority": HASH_AUTHORITY, "prior_frozen_artifact_checks": frozen,
              "bounded_original_source_frames": ROOT_FRAMES,
              "completed_builtin_output_calls": 11, "selected_true_cels": 10,
              "variant_overhead": 1, "unselected_successful_variant": "star-f1203-closeup-2026-10-06-v1",
              "source_exposure_frames_for_selected_cels": chosen_exposure_frames,
              "final_candidate_declaration": declaration, "calls": calls,
              "sequential_source_checks": source_checks,
              "source": helper.file_record(manifest["source"]),
              "source_map": helper.file_record(ROOT / "source_map.json"),
              "source_meta": helper.file_record(ROOT / "source_meta.json"),
              "selection_sha256_observed_at_root_seal": digest(ROOT / "asset_selections.json"),
              "coverage_manifest_sha256_observed_at_root_seal": digest(ROOT / "full-pv-progress-manifest.json"),
              "accepted": False, "artistic_or_composite_or_original_speed_acceptance_claimed": False,
              "all_reference_sha_and_dimensions_are_final_archive_measurements": True,
              "pre_generation_immutable_freeze_claimed": False, "shared_files_written": []}
    path = OUT / "root-third-full-11call-promptset.json"
    result = write_new(path, report)
    print(json.dumps({**result, "calls": 11, "true_cels": 10,
                      "selected_exposure_frames": chosen_exposure_frames, "issues": []}, indent=2))


def selection_snapshot(name, frames, note):
    frozen = protected_checks()
    source = read(ROOT / "source_map.json")
    source_cels = {row["frame"]: row for row in source["cels"]}
    selections = read(ROOT / "asset_selections.json")["selections"]
    manifest = read(ROOT / "full-pv-progress-manifest.json")
    manifest_cels = {r["canonical_source_frame"]: r for r in manifest["cels"]}
    by_frame, by_path = defaultdict(list), defaultdict(list)
    for row in selections:
        by_frame[row["source_frame"]].append(row)
        if row.get("path"):
            by_path[str(absolute(row["path"]).resolve())].append(row["source_frame"])
    checks, issues = [], []
    for f in frames:
        matches = by_frame[f]
        failures = []
        if len(matches) != 1:
            issues.append(f"f{f}: expected one explicit selection")
            continue
        s = matches[0]
        jobpath = absolute(s["job"])
        job = read(jobpath)
        output = helper.file_record(s["path"])
        origin = helper.file_record(job.get("tool_output") or job.get("tool_output_path") or job.get("original_tool_output"))
        references = job.get("reference_roles") or []
        if not references or not job.get("prompt"):
            failures.append("incomplete_prompt_or_roles")
        elif all(isinstance(r, str) for r in references):
            paths = job.get("references", [])
            if len(paths) != len(references):
                failures.append("ordered_path_role_count_mismatch")
                references = []
            else:
                references = [{"path": p, "role": r} for p, r in zip(paths, references)]
        elif not all(isinstance(r, dict) and r.get("path") and r.get("role") for r in references):
            failures.append("unsupported_reference_schema")
        mode = job.get("mode") or job.get("tool")
        if mode not in {"builtin_imagegen", "built-in image_gen"}:
            failures.append("not_builtin")
        if not output["exists"] or not origin["exists"] or output.get("sha256") != origin.get("sha256"):
            failures.append("origin_workspace_missing_or_mismatch")
        if output.get("sha256") != job.get("output_sha256") or output.get("sha256") != s.get("output_sha256"):
            failures.append("recorded_job_or_selection_sha_mismatch")
        dims = job.get("output_dimensions") or job.get("dimensions") or job.get("workspace_output_metadata", {}).get("canvas")
        if output.get("dimensions") != dims:
            failures.append("recorded_dimensions_mismatch")
        if job.get("source_frame") != f or job.get("source_cel") != source_cels[f]["cel"]:
            failures.append("source_frame_or_cel_mismatch")
        if helper.exposure_signature(job.get("source_exposures", [])) != helper.exposure_signature(manifest_cels[f]["source_exposures"]):
            failures.append("original_source_exposure_mismatch")
        if job.get("source_reference") and absolute(job["source_reference"]).resolve() != absolute(manifest_cels[f]["source_reference"]).resolve():
            failures.append("canonical_source_reference_mismatch")
        if job.get("accepted") is not False or s.get("accepted") is not False or s.get("artistic_accepted") is True:
            failures.append("unexpected_acceptance")
        if absolute(job["output"]).resolve() != absolute(s["path"]).resolve():
            failures.append("selected_output_mismatch")
        refs = [helper.file_record(r["path"]) for r in references or [] if isinstance(r, dict) and "path" in r]
        if any(not r["exists"] for r in refs):
            failures.append("missing_reference")
        before_metadata = job.get("ordered_reference_metadata", [])
        reference_metadata_checks = []
        if before_metadata:
            if len(before_metadata) != len(refs):
                failures.append("recorded_reference_metadata_count_mismatch")
            for original, measured, role in zip(before_metadata, refs, references):
                exact = (absolute(original["path"]).resolve() == absolute(measured["path"]).resolve()
                         and original.get("sha256") == measured.get("sha256")
                         and original.get("canvas") == measured.get("dimensions")
                         and original.get("role") == role["role"])
                reference_metadata_checks.append({"recorded": original, "measured": measured, "exact": exact})
                if not exact:
                    failures.append("recorded_reference_metadata_mismatch")
        checks.append({"source_frame": f, "selection": s, "job_path": str(jobpath), "job_sha256": digest(jobpath),
                       "workspace_output": output, "builtin_origin": origin, "references": refs,
                       "ordered_reference_metadata_checks": reference_metadata_checks, "issues": failures})
        issues.extend(f"f{f}:{failure}" for failure in failures)
    duplicates = {str(f): len(rows) for f, rows in by_frame.items() if len(rows) > 1}
    duplicate_paths = {p: fs for p, fs in by_path.items() if len(fs) > 1}
    if duplicates:
        issues.append("duplicate_explicit_source_frame_selections")
    if not all(c["unchanged"] for c in frozen):
        issues.append("frozen_artifact_changed")
    root_archive = OUT / "root-third-full-11call-promptset.json"
    root_archive_unchanged = digest(root_archive) == SEALED_ROOT_THIRD_SHA256
    if not root_archive_unchanged:
        issues.append("root_third_sealed_promptset_changed")
    report = {"snapshot_utc": datetime.now(timezone.utc).isoformat(), "root_notice_original": note,
              "scope": "metadata/file integrity only, no actual-speed or artistic acceptance",
              "requested_adopted_frames": frames, "checks": checks, "selection_row_count": len(selections),
              "duplicate_selection_frames": duplicates, "duplicate_explicit_paths": duplicate_paths,
              "duplicate_paths_do_not_automatically_imply_bad_alias": True,
              "prior_frozen_artifact_checks": frozen, "root_third_archive": helper.file_record(root_archive),
              "root_third_expected_frozen_sha256": SEALED_ROOT_THIRD_SHA256,
              "root_third_sealed_promptset_unchanged": root_archive_unchanged,
              "coverage_summary_observed_may_require_parent_refresh": manifest["summary"],
              "coverage_manifest_snapshot_utc": manifest["snapshot_utc"],
              "shared_current_hashes": {name: digest(ROOT / name) for name in ["asset_selections.json", "source_aliases.json", "source_map.json", "source_meta.json", "compose.py", "star_gestures_layers.py", "star_caption_alternate.py", "full-pv-progress-manifest.json"]},
              "shared_files_written": [], "accepted": False, "issues": issues,
              "status": "metadata_integrity_pass" if not issues else "metadata_issues_need_root_review"}
    print(json.dumps({**write_new(OUT / name, report), "checked_frames": frames, "issues": issues,
                      "selection_row_count": len(selections), "duplicate_explicit_paths": duplicate_paths}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal-root", action="store_true")
    parser.add_argument("--snapshot")
    parser.add_argument("--frames", type=int, nargs="+", default=ROOT_FRAMES)
    parser.add_argument("--notice", default="Root third group adopted; middle and late new groups not yet included.")
    args = parser.parse_args()
    if args.seal_root:
        seal_root()
    elif args.snapshot:
        selection_snapshot(args.snapshot, args.frames, args.notice)
