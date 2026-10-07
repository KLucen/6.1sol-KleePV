"""Private integrity checks; optional generated coverage-report refresh only."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
EXPECTED_SOURCE_MAP = "05de0751535d1c627171b81f41a0183bf3990b902d44435bfc8b3120a30caf76"
FIRST_ARCHIVE = ROOT / "qa/star1091-continuation-2026-10-05/full-root-builtin-promptset.json"
EXPECTED_FIRST_ARCHIVE = "28582f48abce8367395ad697a0198b9529a184f0708815f7d011b61aafd62714"
BASE_FRAMES = [1091, 1097, 1102, 1106, 1113, 1118, 1123, 1129, 2059, 2061, 2065, 2069, 2073]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def absolute(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def record(value):
    path = absolute(value)
    data = {"path": str(path), "exists": path.is_file()}
    if path.is_file():
        data["sha256"] = digest(path)
        if path.suffix.lower() == ".png":
            with Image.open(path) as image:
                image.load()
                data["dimensions"] = list(image.size)
    return data


def proof_records(alias):
    result = []
    for name, values in alias.items():
        if not name.startswith("proof_") or name == "proof_metrics":
            continue
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str):
                    result.append({"field": name, **record(value)})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--frames", type=int, nargs="+", default=BASE_FRAMES)
    parser.add_argument("--alias-pairs", type=int, nargs="+", default=[1100, 1097, 1117, 1113, 1125, 1123])
    parser.add_argument("--report-name", default="integrity-initial.json")
    args = parser.parse_args()
    if len(args.alias_pairs) % 2:
        raise ValueError("Alias arguments must be source/target pairs.")
    OUT.mkdir(parents=True, exist_ok=True)
    if args.refresh:
        subprocess.run([sys.executable, str(ROOT / "audit_full_pv_coverage.py")], cwd=ROOT, check=True)
    source = read(ROOT / "source_map.json")
    cels = {row["frame"]: row for row in source["cels"]}
    candidates = {row["frame"]: row for row in source["candidates"]}
    selections = read(ROOT / "asset_selections.json")["selections"]
    aliases = read(ROOT / "source_aliases.json")["aliases"]
    manifest = read(ROOT / "full-pv-progress-manifest.json")
    by_frame, by_path = defaultdict(list), defaultdict(list)
    for row in selections:
        by_frame[row["source_frame"]].append(row)
        if row.get("path"):
            by_path[row["path"]].append(row["source_frame"])
    duplicate_frames = {str(frame): rows for frame, rows in by_frame.items() if len(rows) > 1}
    duplicate_paths = {path: frames for path, frames in by_path.items() if len(frames) > 1}
    issues = []
    if duplicate_frames:
        issues.append("duplicate_explicit_selection_frames")
    job_checks = []
    for frame in args.frames:
        rows = by_frame[frame]
        if len(rows) != 1:
            job_checks.append({"source_frame": frame, "issues": ["expected_one_selected_row"]})
            issues.append(f"selection_count_f{frame}")
            continue
        selection = rows[0]
        failures = []
        output = record(selection["path"])
        job_path = absolute(selection["job"])
        job = read(job_path)
        origin_value = job.get("tool_output_path") or job.get("tool_output") or job.get("original_tool_output")
        origin = record(origin_value) if origin_value else {"exists": False}
        if not output["exists"] or not origin["exists"]:
            failures.append("workspace_or_builtin_origin_missing")
        else:
            if output["sha256"] != origin["sha256"]:
                failures.append("workspace_builtin_sha_mismatch")
            if output["dimensions"] != origin["dimensions"]:
                failures.append("workspace_builtin_dimensions_mismatch")
            if job.get("output_sha256") != output["sha256"]:
                failures.append("job_recorded_sha_mismatch_or_missing")
            recorded_dimensions = job.get("output_dimensions") or job.get("workspace_output_metadata", {}).get("canvas")
            if recorded_dimensions != output["dimensions"]:
                failures.append("job_recorded_dimensions_mismatch_or_missing")
            if selection.get("output_sha256") != output["sha256"]:
                failures.append("selection_recorded_sha_mismatch_or_missing")
        if job.get("source_frame") != frame or job.get("source_cel") != cels[frame]["cel"]:
            failures.append("job_original_source_frame_or_cel_mismatch")
        if job.get("mode") != "builtin_imagegen" and job.get("tool") != "built-in image_gen":
            failures.append("mode_not_builtin_imagegen")
        if job.get("output") != selection["path"]:
            failures.append("job_selection_output_path_mismatch")
        if job.get("accepted") is not False or selection.get("accepted") is not False:
            failures.append("job_or_selection_not_explicitly_unaccepted")
        if selection.get("artistic_accepted") is True:
            failures.append("unexpected_artistic_acceptance")
        if not job.get("prompt") or not job.get("reference_roles"):
            failures.append("missing_prompt_or_ordered_roles")
        ordered_roles = job.get("reference_roles", [])
        if ordered_roles and all(isinstance(row, dict) for row in ordered_roles):
            reference_paths = [row["path"] for row in ordered_roles]
        else:
            reference_paths = job.get("references", [])
            if len(reference_paths) != len(ordered_roles):
                failures.append("ordered_reference_path_role_count_mismatch")
        references = [record(value) for value in reference_paths]
        if any(not row["exists"] for row in references):
            failures.append("missing_job_reference")
        job_checks.append({"source_frame": frame, "selection": selection, "job_path": str(job_path),
                           "job_sha256": digest(job_path), "workspace_output": output,
                           "builtin_origin": origin, "references": references, "issues": failures})
        issues.extend(f"f{frame}:{failure}" for failure in failures)
    alias_checks = []
    for source_frame, target in zip(args.alias_pairs[::2], args.alias_pairs[1::2]):
        matching = [row for row in aliases if row["source_frame"] == source_frame]
        failures = []
        if len(matching) != 1:
            failures.append("expected_one_alias_record")
            alias_checks.append({"source_frame": source_frame, "issues": failures})
            issues.extend(f"alias_f{source_frame}:{failure}" for failure in failures)
            continue
        alias = matching[0]
        expected = {
            "source_candidate": candidates[source_frame]["id"], "source_cel": cels[source_frame]["cel"],
            "verified_target_frame": target, "verified_target_candidate": candidates[target]["id"],
            "verified_target_cel": cels[target]["cel"], "review": "manual_full_resolution_source_approved",
            "transform": {"kind": "identity", "matrix": [[1, 0, 0], [0, 1, 0]]},
        }
        for field, value in expected.items():
            if alias.get(field) != value:
                failures.append("incorrect_" + field)
        proofs = proof_records(alias)
        if not proofs or any(not row["exists"] for row in proofs):
            failures.append("missing_proof_file")
        target_rows = by_frame[target]
        if len(target_rows) != 1 or not target_rows[0].get("path") or not absolute(target_rows[0]["path"]).is_file():
            failures.append("current_target_art_not_explicitly_selected")
        alias_checks.append({"source_frame": source_frame, "alias": alias, "proofs": proofs,
                             "current_target_selection": target_rows, "issues": failures})
        issues.extend(f"alias_f{source_frame}:{failure}" for failure in failures)
    source_map_sha = digest(ROOT / "source_map.json")
    first_archive_sha = digest(FIRST_ARCHIVE)
    if source_map_sha != EXPECTED_SOURCE_MAP:
        issues.append("original_source_map_sha_changed")
    if first_archive_sha != EXPECTED_FIRST_ARCHIVE:
        issues.append("first_sealed_root_8call_archive_changed")
    report = {
        "snapshot_utc": datetime.now(timezone.utc).isoformat(), "scope": "private metadata/file integrity, not artwork acceptance",
        "coverage_refresh_run": args.refresh, "selection_row_count": len(selections),
        "duplicate_selection_frames": duplicate_frames, "duplicate_selected_paths": duplicate_paths,
        "duplicate_path_note": "Repeated source cels must normally use approved aliases; any direct duplicate is reported, never silently fixed.",
        "new_draft_job_checks": job_checks, "new_source_alias_checks": alias_checks,
        "source_map_sha256": source_map_sha, "source_map_unchanged": source_map_sha == EXPECTED_SOURCE_MAP,
        "first_sealed_root_8call_archive_sha256": first_archive_sha,
        "first_sealed_root_8call_archive_unchanged": first_archive_sha == EXPECTED_FIRST_ARCHIVE,
        "coverage_summary": manifest["summary"], "source_meta_sha256": digest(ROOT / "source_meta.json"),
        "shared_current_hashes": {name: digest(ROOT / name) for name in [
            "asset_selections.json", "source_aliases.json", "source_map.json", "full-pv-progress-manifest.json",
            "full-pv-coverage-report.json", "compose.py", "star_gestures_layers.py", "star_caption_alternate.py"]},
        "source_alias_record_count": len(aliases), "issues": issues,
        "manual_shared_files_written_by_worker": [],
        "worker_artistic_or_actual_speed_acceptance": False,
        "status": "integrity_metadata_pass" if not issues else "integrity_issues_need_root_review",
    }
    path = OUT / args.report_name
    if path.exists():
        raise FileExistsError("Keep earlier private snapshots; choose a new report name.")
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "sha256": digest(path), "issues": issues,
                      "duplicate_paths": duplicate_paths, "coverage": report["coverage_summary"]}, indent=2))


if __name__ == "__main__":
    main()
