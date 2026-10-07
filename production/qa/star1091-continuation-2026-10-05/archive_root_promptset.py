"""Snapshot root jobs privately; sealing requires root batch-completion notice."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FRAMES = {1091, 1097, 1102, 1106, 1113}


def digest_bytes(data):
    return sha256(data).hexdigest()


def digest(path):
    return digest_bytes(path.read_bytes())


def absolute(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def file_record(path):
    path = absolute(path)
    result = {"path": str(path), "exists": path.is_file()}
    if not path.is_file():
        return result
    result.update({"sha256": digest(path), "bytes": path.stat().st_size})
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        with Image.open(path) as image:
            result.update({"dimensions": list(image.size), "mode": image.mode})
    return result


def exposure_signature(exposures):
    return [{key: item.get(key) for key in ("start", "end", "pts", "end_pts", "family", "source_transform")}
            for item in exposures]


def inspect_job(path, raw, job, cels, selected, declaration, sealed):
    issues, warnings = [], []
    frame = job["source_frame"]
    output_path = job.get("output")
    output = file_record(output_path) if output_path else None
    origin_value = job.get("tool_output_path") or job.get("tool_output")
    origin = file_record(origin_value) if origin_value else None
    completed = bool(output and output["exists"] and origin and origin["exists"])
    if job.get("mode") != "builtin_imagegen":
        issues.append("mode_not_builtin_imagegen")
    if not job.get("prompt"):
        issues.append("missing_full_prompt")
    refs = []
    for index, ref in enumerate(job.get("reference_roles", []), 1):
        record = file_record(ref["path"])
        record.update({"order": index, "role_original": ref.get("role")})
        if not record["exists"]:
            issues.append(f"missing_reference_{index}")
        if not ref.get("role"):
            issues.append(f"missing_reference_role_{index}")
        refs.append(record)
    if not refs:
        issues.append("missing_ordered_reference_roles")
    cel = cels.get(frame)
    if cel is None:
        issues.append("no_original_canonical_cel")
    else:
        if job.get("source_cel") != cel["cel"]:
            issues.append("source_cel_mismatch")
        if job.get("source_reference") != cel["source_reference"]:
            issues.append("canonical_source_reference_mismatch")
        if exposure_signature(job.get("source_exposures", [])) != exposure_signature(cel["source_exposures"]):
            issues.append("original_source_exposure_mismatch")
    canonical = file_record(job["source_reference"]) if job.get("source_reference") else None
    if canonical is None or not canonical["exists"]:
        issues.append("missing_canonical_source_reference")
    other_evidence = job.get("source_delta_evidence", [])
    if isinstance(other_evidence, str):
        other_evidence = [other_evidence]
    supporting_evidence = [file_record(value) for value in other_evidence]
    if job.get("reference_queue"):
        supporting_evidence.append(file_record(job["reference_queue"]))
    for record in supporting_evidence:
        if not record["exists"]:
            issues.append("missing_recorded_supporting_source_evidence")
    if job.get("accepted") is not False:
        issues.append("accepted_field_not_explicit_false")
    if completed:
        if origin["sha256"] != output["sha256"]:
            issues.append("workspace_png_does_not_match_builtin_tool_output")
        if origin["dimensions"] != output["dimensions"]:
            issues.append("builtin_workspace_dimension_mismatch")
        if job.get("output_dimensions") and job["output_dimensions"] != output["dimensions"]:
            issues.append("recorded_output_dimensions_mismatch")
        if job.get("output_sha256") and job["output_sha256"] != output["sha256"]:
            issues.append("recorded_output_sha256_mismatch")
        if not job.get("output_dimensions"):
            warnings.append("job_omits_output_dimensions_archive_measured_real_png")
        if not job.get("output_sha256"):
            warnings.append("job_omits_output_sha256_archive_hashed_real_png")
    else:
        warnings.append("tool_or_workspace_output_pending_or_missing")
        if sealed:
            issues.append("cannot_seal_job_without_complete_builtin_origin_and_workspace_png")
    variant_match = re.search(r"-v(\d+)$", job.get("id", ""))
    variant = int(variant_match.group(1)) if variant_match else None
    selection_rows = [row for row in selected if row.get("source_frame") == frame]
    observed_selected = any(row.get("path") == output_path for row in selection_rows)
    declared_path = declaration.get(str(frame)) if declaration else None
    status = job.get("status", "")
    known_failed = bool("unselected" in status or "failed" in status or "blocking" in status)
    if sealed:
        chosen = declared_path == output_path
        if chosen and not observed_selected:
            issues.append("root_declared_candidate_not_in_current_explicit_selection")
        if chosen and known_failed:
            issues.append("root_declared_candidate_has_failed_or_blocking_job_status")
        disposition = "root_declared_selected_draft_unaccepted" if chosen else (
            "failed_variant_unselected" if known_failed else "other_variant_unselected")
    else:
        disposition = "pending_root_batch_completion_and_final_adoption"
    return {
        "job_path": str(path), "job_json_sha256": digest_bytes(raw), "job_json_bytes": len(raw),
        "job_original_complete": job, "id": job.get("id"), "source_frame": frame,
        "source_cel": job.get("source_cel"), "variant_number": variant,
        "full_prompt_original": job.get("prompt"), "ordered_reference_roles": refs,
        "canonical_source_reference": canonical, "original_exposures": job.get("source_exposures"),
        "supporting_source_delta_evidence": supporting_evidence,
        "builtin_tool_origin": origin, "workspace_output": output,
        "output_sha_and_dimensions_measured_not_tool_thumbnail": True,
        "completed_builtin_output_call_evidence": completed,
        "job_status_original": status, "job_reports_failed_or_blocking_unselected": known_failed,
        "observed_explicit_selection_records": selection_rows,
        "observed_selected_at_snapshot_not_acceptance": observed_selected,
        "root_declared_final_candidate": declared_path,
        "final_disposition": disposition,
        "accepted": False, "original_speed_review_performed_by_archivist": False,
        "issues": issues, "metadata_warnings": warnings,
    }


def atomic_report(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal", action="store_true")
    parser.add_argument("--completion-note", default="")
    parser.add_argument("--declaration", type=Path)
    args = parser.parse_args()
    if args.seal and (not args.completion_note or args.declaration is None):
        raise ValueError("Sealing requires the actual root completion notice and a root-confirmed final-candidate declaration.")
    declaration = json.loads(args.declaration.read_text(encoding="utf-8")) if args.declaration else None
    if args.seal and set(map(int, declaration)) != FRAMES:
        raise ValueError("Final declaration must cover exactly the five original missing cels in this bounded root batch.")
    manifest_bytes = (ROOT / "full-pv-progress-manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    cels = {row["canonical_source_frame"]: row for row in manifest["cels"]}
    selection_path = ROOT / "asset_selections.json"
    selection_bytes = selection_path.read_bytes()
    selected = json.loads(selection_bytes)["selections"]
    jobs, unreadable = [], []
    for path in sorted((ROOT / "jobs").glob("star-f*-2026-10-05*.json")):
        if not any(f"star-f{frame}-" in path.name for frame in FRAMES):
            continue
        try:
            raw = path.read_bytes()
            job = json.loads(raw)
        except (OSError, ValueError) as error:
            unreadable.append({"path": str(path), "error": str(error), "retry_or_edit_attempted": False})
            continue
        if job.get("source_frame") not in FRAMES:
            continue
        jobs.append(inspect_job(path, raw, job, cels, selected, declaration, args.seal))
    jobs.sort(key=lambda item: (item["source_frame"], item["variant_number"] or 0, item["id"]))
    completed = [row for row in jobs if row["completed_builtin_output_call_evidence"]]
    generated_cels = sorted({row["source_cel"] for row in completed})
    flaws = [{"job": row["id"], "issues": row["issues"]} for row in jobs if row["issues"]]
    expected_missing = sorted(FRAMES - {row["source_frame"] for row in completed})
    source_path = Path(manifest["source"])
    auth_path = OUT / "caption-authorization.json"
    report = {
        "snapshot_utc": datetime.now(timezone.utc).isoformat(),
        "archive_phase": "final_after_generation" if args.seal else "pending_after_observed_generation",
        "frozen": bool(args.seal), "root_batch_completion_notice_original": args.completion_note or None,
        "bounded_original_source_frames": sorted(FRAMES),
        "source": file_record(source_path),
        "original_source_map": file_record(ROOT / "source_map.json"),
        "original_pts_metadata": file_record(ROOT / "source_meta.json"),
        "source_reference_queue": file_record(OUT / "missing-source-reference-queue.json"),
        "coverage_manifest_observed_sha256": digest_bytes(manifest_bytes),
        "explicit_selection_observed_sha256": digest_bytes(selection_bytes),
        "caption_authorization_original": json.loads(auth_path.read_text(encoding="utf-8")),
        "caption_authorization_file": file_record(auth_path),
        "job_count_observed": len(jobs), "completed_builtin_output_calls_observed": len(completed),
        "unique_original_missing_cels_with_any_output_observed": len(generated_cels),
        "multiple_variant_calls_not_additional_missing_cels": len(completed) - len(generated_cels),
        "expected_source_frames_still_without_complete_output": expected_missing,
        "failed_or_blocking_variants_observed": [row["id"] for row in completed if row["job_reports_failed_or_blocking_unselected"]],
        "calls": jobs, "unreadable_job_files": unreadable,
        "job_validation_issues": flaws,
        "archivist_did_not_modify_jobs_or_shared_files": True,
        "archive_does_not_claim_pre_generation_immutable_freeze": True,
        "archive_does_not_claim_artistic_or_composite_or_original_speed_acceptance": True,
        "status": "pending_root_batch_completion_and_final_candidate_confirmation",
    }
    if args.seal:
        if unreadable or flaws or expected_missing:
            raise ValueError(json.dumps({"unreadable": unreadable, "issues": flaws, "missing": expected_missing}))
        for frame, path in declaration.items():
            if not any(row["source_frame"] == int(frame) and row["job_original_complete"].get("output") == path for row in jobs):
                raise ValueError(f"Final declaration has no matching recorded builtin job f{frame}: {path}")
        report["status"] = "sealed_complete_builtin_promptset_draft_unaccepted"
        report["final_selected_missing_cels"] = len(declaration)
        report["final_candidate_declaration"] = declaration
        path = OUT / "full-root-builtin-promptset.json"
        if path.exists():
            raise FileExistsError("Preserve the existing frozen archive. Create a separate extension instead.")
    else:
        path = OUT / "prompt-archive-pending.json"
    atomic_report(path, report)
    print(json.dumps({"report": str(path), "sha256": digest(path), "phase": report["archive_phase"],
                      "builtin_calls": len(completed), "unique_source_cels": len(generated_cels),
                      "variant_overhead_calls": len(completed) - len(generated_cels),
                      "missing_expected_frames": expected_missing, "issues": flaws,
                      "unreadable_jobs": unreadable, "frozen": args.seal}, indent=2))


if __name__ == "__main__":
    main()
