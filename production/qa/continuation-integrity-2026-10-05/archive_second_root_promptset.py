"""Private root continuation archive; seal only on an explicit final-frame notice."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FROZEN_PRIOR_ARCHIVES = {
    "qa/fast-fullpv-batch2-integrity-2026-10-04/batch2-full-27call-promptset.json": "173f36b5ee4b9fd280b91db09db77c845789ddd5f39a67f58fb9675ae6eef32a",
    "qa/standing-missing-2026-10-05/oct5-full-7call-promptset.json": "1e6372e9e88024bfac931dc462b0f7f5993e7a823b80236b5ca2b6346e814608",
    "qa/star1091-continuation-2026-10-05/full-root-builtin-promptset.json": "28582f48abce8367395ad697a0198b9529a184f0708815f7d011b61aafd62714",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, nargs="+", required=True)
    parser.add_argument("--seal", action="store_true")
    parser.add_argument("--completion-note", default="")
    args = parser.parse_args()
    frames = set(args.frames)
    prior_archive_checks = [{"path": str(ROOT / name), "expected_sha256": expected,
                             "observed_sha256": digest(ROOT / name),
                             "unchanged": digest(ROOT / name) == expected}
                            for name, expected in FROZEN_PRIOR_ARCHIVES.items()]
    if args.seal and not all(row["unchanged"] for row in prior_archive_checks):
        raise ValueError("A prior frozen prompt archive changed; do not seal over unresolved provenance.")
    if len(frames) != len(args.frames):
        raise ValueError("Root frame list must not contain duplicates.")
    if args.seal and not args.completion_note:
        raise ValueError("Sealing requires the actual root final-frame completion notice.")
    helper_path = ROOT / "qa/star1091-continuation-2026-10-05/archive_root_promptset.py"
    spec = importlib.util.spec_from_file_location("first_root_archive_helpers", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    manifest_bytes = (ROOT / "full-pv-progress-manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    cels = {row["canonical_source_frame"]: row for row in manifest["cels"]}
    selection_bytes = (ROOT / "asset_selections.json").read_bytes()
    selected = json.loads(selection_bytes)["selections"]
    declaration = {}
    if args.seal:
        for frame in frames:
            rows = [row for row in selected if row["source_frame"] == frame and row.get("path")]
            if len(rows) != 1:
                raise ValueError(f"Root final frame f{frame} does not have one explicit selected output.")
            declaration[str(frame)] = rows[0]["path"]
    calls, unreadable = [], []
    for path in sorted((ROOT / "jobs").glob("star-f*-2026-10-05*.json")):
        if not any(f"star-f{frame}-" in path.name for frame in frames):
            continue
        try:
            raw = path.read_bytes()
            job = json.loads(raw)
            if job.get("source_frame") in frames:
                calls.append(helper.inspect_job(path, raw, job, cels, selected, declaration, args.seal))
        except (OSError, ValueError) as error:
            unreadable.append({"path": str(path), "error": str(error), "edit_attempted": False})
    calls.sort(key=lambda row: (row["source_frame"], row["variant_number"] or 0, row["id"]))
    completed = [row for row in calls if row["completed_builtin_output_call_evidence"]]
    unique = {row["source_frame"] for row in completed}
    missing = sorted(frames - unique)
    issues = [{"job": row["id"], "issues": row["issues"]} for row in calls if row["issues"]]
    if args.seal:
        if unreadable or missing or issues:
            raise ValueError(json.dumps({"unreadable": unreadable, "missing": missing, "issues": issues}))
        for frame, value in declaration.items():
            if not any(row["source_frame"] == int(frame) and row["job_original_complete"].get("output") == value for row in calls):
                raise ValueError(f"Selected f{frame} does not match a complete recorded root job.")
    auth = ROOT / "qa/star1091-continuation-2026-10-05/caption-authorization.json"
    queue = ROOT / "qa/star1118-continuation-2026-10-05/missing-source-reference-queue.json"
    report = {
        "snapshot_utc": datetime.now(timezone.utc).isoformat(),
        "archive_phase": "final_after_generation" if args.seal else "pending_after_observed_generation",
        "frozen": args.seal, "root_final_frame_notice_original": args.completion_note or None,
        "bounded_original_source_frames": sorted(frames),
        "source": helper.file_record(manifest["source"]),
        "original_source_map": helper.file_record(ROOT / "source_map.json"),
        "original_pts_metadata": helper.file_record(ROOT / "source_meta.json"),
        "source_reference_queue": helper.file_record(queue),
        "coverage_manifest_observed_sha256": sha256(manifest_bytes).hexdigest(),
        "explicit_selection_observed_sha256": sha256(selection_bytes).hexdigest(),
        "caption_authorization_original": read(auth), "caption_authorization_file": helper.file_record(auth),
        "completed_builtin_output_calls_observed": len(completed),
        "unique_original_missing_cels_with_any_output_observed": len(unique),
        "multiple_variant_calls_not_additional_missing_cels": len(completed) - len(unique),
        "failed_or_blocking_variants_observed": [row["id"] for row in completed if row["job_reports_failed_or_blocking_unselected"]],
        "expected_source_frames_still_without_complete_output": missing,
        "calls": calls, "unreadable_job_files": unreadable, "job_validation_issues": issues,
        "final_selected_missing_cels": len(declaration) if args.seal else None,
        "final_candidate_declaration": declaration if args.seal else None,
        "archivist_did_not_modify_jobs_or_shared_files": True,
        "archive_does_not_claim_pre_generation_immutable_freeze": True,
        "archive_does_not_claim_artistic_or_composite_or_original_speed_acceptance": True,
        "prior_frozen_prompt_archives": prior_archive_checks,
        "status": "sealed_complete_builtin_promptset_draft_unaccepted" if args.seal else "pending_root_final_frame_notice",
    }
    name = "full-second-root-builtin-promptset.json" if args.seal else (
        "prompt-archive-pending-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    path = OUT / name
    if path.exists():
        raise FileExistsError("Preserve earlier archive; choose a separate extension.")
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "sha256": digest(path), "calls": len(completed),
                      "unique_missing_cels": len(unique), "variant_overhead": len(completed) - len(unique),
                      "missing": missing, "issues": issues, "frozen": args.seal}, indent=2))


if __name__ == "__main__":
    main()
