"""Read production inputs and write only this private audit directory."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRIOR = ROOT / "qa/fast-fullpv-batch2-integrity-2026-10-04"
SEALED_SHA = "173f36b5ee4b9fd280b91db09db77c845789ddd5f39a67f58fb9675ae6eef32a"
CODE_FILES = [
    "compose.py", "cyan_profile_layers.py", "cyan_caption_layers.py",
    "make_timeline.py", "verify_preview.py", "qa/verify_cyan_layers_batch2.py",
]
DATA_FILES = [
    "source_meta.json", "source_map.json", "source_aliases.json",
    "asset_selections.json", "timeline-cyan-911-1008-fast-draft-v1.json",
    "full-pv-coverage-report.json", "full-pv-progress-manifest.json",
    "qa/fast-fullpv-batch-2026-10-04-progress-snapshot.json",
]
TECHNICAL_CHECKS = {
    "source_identity", "one_video_one_audio_stream", "decoded_frame_count",
    "all_frame_dimensions", "explicit_video_pts", "strict_source_frame_pts",
    "strictly_increasing_pts", "strict_video_end_boundary", "aac_stream_configuration",
    "aac_interval_packet_count", "aac_packet_payload_hashes",
    "aac_packet_timestamps_and_durations", "aac_origin_nearest_tick_only",
    "aac_priming_side_data", "audio_covers_boundary_without_extra_packet",
    "full_video_audio_decode", "preview_unchanged_during_verification",
}


def load_base():
    spec = importlib.util.spec_from_file_location("batch2_integrity", PRIOR / "audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_input_names(base, metadata):
    timeline = base.read(ROOT / "timeline-cyan-911-1008-fast-draft-v1.json")
    names = CODE_FILES + DATA_FILES + [metadata["source"]]
    used_cels = sorted({exposure["cel"] for exposure in timeline["output_exposures"]})
    names += [timeline["assets"][cel]["path"] for cel in used_cels]
    tree = ast.parse((ROOT / "cyan_caption_layers.py").read_text(encoding="utf-8-sig"))
    phases = next(ast.literal_eval(statement.value) for statement in tree.body
                  if isinstance(statement, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == "PHASES" for target in statement.targets))
    names += [f"source_refs/{donor}" for phase in phases for donor in phase["donors"]]
    return list(dict.fromkeys(names))


def freeze_record(base, value, expected_sha, metadata):
    path = base.resolve(value)
    frozen = base.read(path)
    supplemental_checks = {}
    if "helpers_sha256" in frozen:
        entries = dict(frozen["helpers_sha256"])
        entries["timeline-cyan-911-1008-fast-draft-v1.json"] = frozen["timeline_sha256"]
        sidecars = {
            "raw-final-batch-audit.json": "raw_audit_sha256",
            "source-origin-verify.json": "source_origin_audit_sha256",
            "frozen-after-hashes.json": "frozen_after_audit_sha256",
        }
        for name, field in sidecars.items():
            entries[str(path.parent / name)] = frozen[field]
        for phase in frozen["caption_donor_sha256"].values():
            entries.update(phase)
        for name in ("native_caption_pages_viewed", "canonical_body_pages_viewed"):
            entries.update({record["path"]: record["sha256"] for record in frozen[name]})
        raw = base.read(path.parent / "raw-final-batch-audit.json")
        for row in raw["rows"]:
            entries[row["asset"]] = row["asset_sha256"]
            entries[row["composite"]] = row["composite_sha256"]
        timeline = base.read(ROOT / "timeline-cyan-911-1008-fast-draft-v1.json")
        by_frame = {frame: exposure for exposure in timeline["output_exposures"]
                    for frame in range(exposure["start"], exposure["end"])}

        def row_matches(row):
            exposure = by_frame.get(row["source_frame"])
            if exposure is None or exposure["cel"] != row["cel"]:
                return False
            asset = timeline["assets"][row["cel"]]
            return (base.resolve(asset["path"]).resolve() == base.resolve(row["asset"]).resolve()
                    and asset["source_frame"] == row["canonical_source_frame"]
                    and exposure["source_matrix"] == row["matrix"]
                    and base.digest(base.resolve(asset["path"])) == row["asset_sha256"])

        origin = base.read(path.parent / "source-origin-verify.json")
        supplemental_checks = {
            "freeze_and_raw_interval_exact": frozen["source_interval"] == raw["source_interval"] == [911, 1008],
            "all97_frozen_raw_rows_match_current_timeline_assets_source_frames_matrices":
                [row["source_frame"] for row in raw["rows"]] == list(range(911, 1008))
                and all(row_matches(row) for row in raw["rows"]),
            "source_origin_report_sha_matches_expected_source": origin["actual_source_file_sha256"] == metadata["sha256"],
            "source_origin_report_records_all_checks_true": origin["all_source_origin_checks"] is True,
            "freeze_does_not_claim_artistic_acceptance": frozen["artistic_acceptance"] is False,
        }
        schema = "existing_raw_layer_freeze"
        scope = "The parent's identified pre-render record: three compositor helpers, exact timeline, used assets, caption donors, raw composites and hashed sidecar evidence."
        timing = "Parent explicitly identified this existing record as pre-render; auditor compares it after rendering."
    else:
        entries = frozen.get("file_sha256", frozen)
        schema = "file_sha256"
        scope = frozen.get("scope", "Explicit file hashes only")
        timing = "Snapshot timing is whatever its recorded producer established; this audit does not infer it from file time."
    comparisons = {name: {"recorded_sha256": recorded, "current_sha256": base.digest(base.resolve(name))}
                   for name, recorded in entries.items()}
    checks = {f"sha256_matches: {name}": record["recorded_sha256"] == record["current_sha256"]
              for name, record in comparisons.items()}
    checks.update(supplemental_checks)
    if expected_sha:
        checks["freeze_document_sha_matches_parent_provided_identity"] = base.digest(path) == expected_sha
    return {"document": base.file_record(str(path)), "schema": schema, "scope": scope,
            "timing_basis": timing, "file_comparisons": comparisons, "checks": checks}


def appendix_archive_record(base, value, expected_sha, appendix):
    path = base.resolve(value)
    archived = base.read(path)
    current_by_path = {Path(record["job_document"]["absolute_path"]).resolve(): record for record in appendix}
    archived_by_path = {base.resolve(record["job_path"]).resolve(): record for record in archived["records"]}
    checks = {
        "provided_archive_identity_matches": base.digest(path) == expected_sha,
        "seven_recorded_calls": archived["recorded_calls"] == len(archived["records"]) == len(appendix) == 7,
        "six_missing_one_repair_recorded": archived["new_previously_missing_cels"] == 6 and archived["mapped_blocker_repairs"] == 1,
        "archive_accepted_false": archived["accepted"] is False,
        "all_job_paths_exact": set(archived_by_path) == set(current_by_path),
    }
    for job_path, current in current_by_path.items():
        sealed = archived_by_path[job_path]
        name = job_path.name
        current_refs = [{"path": reference["path"], "role": reference["role"],
                         "sha256": reference["file"]["sha256"], "dimensions": reference["file"]["dimensions"]}
                        for reference in current["ordered_reference_roles"]]
        checks[f"{name}: full_original_job_and_document_sha_exact"] = (
            sealed["complete_original_job"] == current["job_fields"]
            and sealed["job_sha256"] == current["job_document"]["sha256"])
        checks[f"{name}: ordered_refs_roles_sha_dimensions_exact"] = current_refs == sealed["references_in_original_order"]
        checks[f"{name}: output_and_tool_origin_path_sha_dimensions_exact"] = all(
            base.resolve(sealed[field]["path"]).resolve() == Path(current[current_field]["absolute_path"]).resolve()
            and all(sealed[field][key] == current[current_field][key] for key in ("sha256", "dimensions"))
            for field, current_field in (("output", "workspace_output"), ("tool_origin", "original_tool_output")))
        checks[f"{name}: actual_source_cel_reference_full_exposures_exact"] = (
            sealed["actual_cel"] == current["source_cel"]
            and sealed["actual_source_reference"] == current["job_fields"]["source_reference"]
            and sealed["actual_source_exposures"] == current["expected_full_source_exposures"])
        checks[f"{name}: selected_unaccepted_draft_recorded"] = sealed["selected_as_unaccepted_draft"] is True
    return {"document": base.file_record(str(path)), "recorded_calls": archived["recorded_calls"], "checks": checks}


def encoded_freeze_record(base, value, expected_sha, verifications):
    path = base.resolve(value)
    frozen = base.read(path)
    raw = base.read(base.resolve(frozen["raw_freeze"]))
    entries = {frozen["raw_freeze"]: frozen["raw_freeze_sha256"], **frozen["helpers_sha256"]}
    for review in frozen["encoded_reviews"]:
        entries[review["video"]] = review["video_sha256"]
        entries[review["audit"]] = review["audit_sha256"]
        entries[review["static_review"]] = review["static_review_sha256"]
        entries.update({page["path"]: page["sha256"] for page in review["native_caption_pages_viewed"]})
    comparisons = {name: {"recorded_sha256": recorded, "current_sha256": base.digest(base.resolve(name))}
                   for name, recorded in entries.items()}
    checks = {f"sha256_matches: {name}": record["recorded_sha256"] == record["current_sha256"]
              for name, record in comparisons.items()}
    checks.update({
        "provided_encoded_freeze_identity_matches": base.digest(path) == expected_sha,
        "encoded_interval_exact": frozen["source_interval"] == [911, 1008],
        "two_expected_encoded_roles": {record["role"] for record in frozen["encoded_reviews"]}
            == {"encoded-single", "encoded-comparison-right"},
        "helper_sha_exactly_matches_raw_freeze": frozen["helpers_sha256"] == raw["helpers_sha256"],
        "same_two_videos_as_technical_verifications": {
            base.resolve(record["video"]).resolve() for record in frozen["encoded_reviews"]}
            == {Path(record["video"]["absolute_path"]).resolve() for record in verifications},
        "encoded_freeze_records_static_only_unaccepted": frozen["artistic_acceptance"] is False
            and frozen["original_speed_artistic_review"] == "pending",
        "each_role_records_all97_frames_and13_native_pages": all(
            record["native_frames_reviewed"] == 97 and len(record["native_caption_pages_viewed"]) == 13
            and [frame for page in record["native_caption_pages_viewed"] for frame in page["frames"]] == list(range(911, 1008))
            for record in frozen["encoded_reviews"]),
    })
    return {"document": base.file_record(str(path)), "scope": frozen["scope"],
            "file_comparisons": comparisons, "checks": checks,
            "reported_static_metrics": [{key: value for key, value in record.items()
                                         if key in ("role", "mean_core_rgb_abs_error", "max_core_rgb_abs_error",
                                                    "max_core_luma_drop", "caption_layer_blockers")}
                                        for record in frozen["encoded_reviews"]],
            "auditor_independent_visual_review": "not_performed"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verification", action="append", default=[])
    parser.add_argument("--appendix-job", action="append", default=[])
    parser.add_argument("--appendix-archive")
    parser.add_argument("--appendix-archive-sha")
    parser.add_argument("--encoded-freeze")
    parser.add_argument("--encoded-freeze-sha")
    parser.add_argument("--freeze", help="Read a root-provided JSON of code/data SHA256 values")
    parser.add_argument("--freeze-sha", help="Expected SHA256 identity supplied by the parent")
    parser.add_argument("--freeze-only", action="store_true", help="Capture render inputs here before rendering")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    base = load_base()
    meta = base.read(ROOT / "source_meta.json")
    if args.freeze_only:
        frozen = {"snapshot_utc": datetime.now(timezone.utc).isoformat(),
                  "scope": "Pre-render cyan code, data, timeline assets, caption donors and actual source video.",
                  "file_sha256": {name: base.digest(base.resolve(name)) for name in render_input_names(base, meta)}}
        destination = HERE / "render-input-freeze.json"
        destination.write_text(json.dumps(frozen, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        print(json.dumps({"freeze": str(destination), "files": len(frozen["file_sha256"])}))
        return
    source = base.read(ROOT / "source_map.json")
    selections = base.read(ROOT / "asset_selections.json")["selections"]
    sealed_path = PRIOR / "batch2-full-27call-promptset.json"
    sealed = base.read(sealed_path)
    records = [base.capture_job(identifier, "root_cyan", source, selections) for identifier in base.ROOT_IDS]
    records += [base.capture_job(identifier, "star_gestures", source, selections) for identifier in base.STAR_IDS]
    sealed_by_id = {record["job_id"]: record for record in sealed["jobs"]}
    previous_manifest = base.read(ROOT / "qa/fast-fullpv-batch-2026-10-04-progress-snapshot.json")
    previous_cels = {item["cel"]: item for item in previous_manifest["cels"]}
    archive_checks = {
        "sealed_archive_sha_exact": base.digest(sealed_path) == SEALED_SHA,
        "27_calls_25_selected": sealed["calls"] == 27 and sealed["selected"] == 25,
        "job_identifiers_exact": set(sealed_by_id) == {record["job_id"] for record in records},
        "current_full_prompts_refs_exposures_match": all(
            all(sealed_by_id[record["job_id"]][key] == record[key]
                for key in ("prompt", "source_exposures", "ordered_reference_roles"))
            for record in records),
        "27_current_calls_25_selected": len(records) == 27 and sum(record["selected"] for record in records) == 25,
        "25_distinct_selected_source_cels": len({record["source_cel"] for record in records if record["selected"]}) == 25,
        "sealed_and_current_outputs_match": all(
            sealed_by_id[record["job_id"]]["workspace_output"]["sha256"] == record["workspace_output"]["sha256"]
            and sealed_by_id[record["job_id"]]["original_tool_output"]["sha256"] == record["original_tool_output"]["sha256"]
            for record in records),
        "all_jobs_builtin_image_gen": all(record["original_job_fields"].get("tool") in ("builtin_image_gen", "builtin_imagegen") for record in records),
        "star_jobs_record_one_call": all(record["original_job_fields"].get("generation_calls") == 1
                                         for record in records if record["group"] == "star_gestures"),
        "all25_selected_cels_previously_missing": all(
            not previous_cels[record["source_cel"]]["selected_asset"] for record in records if record["selected"]),
    }
    checks = {
        "source_sha_exact": meta["sha256"] == base.SOURCE_SHA256 and base.digest(base.resolve(meta["source"])) == base.SOURCE_SHA256,
        "15_root_selected": sum(record["selected"] for record in records if record["group"] == "root_cyan") == 15,
        "10_star_selected": sum(record["selected"] for record in records if record["group"] == "star_gestures") == 10,
        "rejected_baselines_unselected": not any(base.norm(item.get("path", "")) in base.FORBIDDEN for item in selections),
    }
    timeline = base.timeline_record(source, meta, records)
    coverage = base.coverage_record(source, selections)
    new_selected_cels = {record["source_cel"] for record in records if record["selected"]}
    new_source_frames = sum(cel in new_selected_cels for cel in source["frame_to_cel"])
    checks["sealed_batch2_has_25_previously_missing_cels_63_source_frames"] = (
        len(new_selected_cels) == 25 and new_source_frames == 63)
    star_proposal = base.star_proposal_record(records)
    verifications = [base.verification_record(value) for value in args.verification]
    for record in verifications:
        document = base.read(Path(record["path"]))
        record["full_technical_document"] = document
        record["checks"].update({
            "exact_expected_17_technical_checks_present": set(document["checks"]) == TECHNICAL_CHECKS,
            "technical_report_source_is_current_source": Path(document["source"]).resolve() == base.resolve(meta["source"]).resolve(),
            "technical_report_metadata_is_current_metadata": Path(document["metadata"]).resolve() == (ROOT / "source_meta.json").resolve(),
            "technical_report_does_not_claim_artistic_review": document["artistic_review"] == "not_performed_by_this_technical_verifier",
        })
    probes = []
    for verification in verifications:
        video = verification["video"]["absolute_path"]
        output = subprocess.run([
            "ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format",
            "-of", "json", video,
        ], check=True, text=True, capture_output=True)
        probe = json.loads(output.stdout)
        streams = [stream for stream in probe["streams"] if stream["codec_type"] == "video"]
        probes.append({"video": video, "ffprobe": probe,
                       "checks": {"97_frames_independently_counted": len(streams) == 1 and streams[0]["nb_read_frames"] == "97",
                                  "ffprobe_clean_stderr": not output.stderr.strip(),
                                  "video_unchanged_during_independent_probe": base.digest(Path(video)) == verification["video"]["sha256"],
                                  "dimensions_match_technical_document": len(streams) == 1 and
                                  [streams[0]["width"], streams[0]["height"]] == verification["full_technical_document"]["video_timing"]["dimensions"]}})
    if args.final:
        checks["one_single_and_one_comparison_dimensions"] = sorted(
            record["full_technical_document"]["video_timing"]["dimensions"] for record in verifications
        ) == [[1920, 1080], [3840, 1080]]
    appendix = []
    for value in args.appendix_job:
        path = base.resolve(value)
        job = base.read(path)
        output = job.get("output") or job.get("output_path") or job.get("expected_output")
        origin = job.get("original_tool_output") or job.get("generated_origin") or job.get("tool_output_path")
        selected = [item for item in selections if base.norm(item.get("path", "")) == base.norm(output)]
        cel = job.get("source_cel") or job.get("canonical_cel")
        ordered_refs = job.get("ordered_reference_roles") or job.get("reference_roles") or []
        if ordered_refs and isinstance(ordered_refs[0], str):
            ordered_refs = [{"path": reference, "role": role}
                            for reference, role in zip(job["references"], ordered_refs)]
        refs = [{"order": index, **reference, "file": base.file_record(reference["path"], image=True)}
                for index, reference in enumerate(ordered_refs, start=1)]
        workspace = base.file_record(output, image=True)
        tool_output = base.file_record(origin, image=True)
        expected_exposures = base.source_exposures(source, cel)
        exposures = job["source_exposures"]
        appendix_checks = {
            "full_prompt_present": len(job.get("prompt", "")) > 500,
            "source_frame_matches_cel": source["frame_to_cel"][job["source_frame"]] == cel,
            "source_exposure_count_exact": len(exposures) == len(expected_exposures),
            "required_source_exposure_fields_present": all(
                all(key in recorded for key in ("start", "end", "pts", "end_pts")) for recorded in exposures),
            "all_recorded_source_exposure_fields_exact": len(exposures) == len(expected_exposures)
            and all(all(expected.get(key) == value for key, value in recorded.items())
                    for recorded, expected in zip(exposures, expected_exposures)),
            "ordered_refs_present_and_decode": bool(refs) and all(reference.get("role") and reference["file"].get("decodes") for reference in refs),
            "all_recorded_reference_hashes_match": all(not reference.get("sha256") or reference["sha256"] == reference["file"].get("sha256") for reference in refs),
            "output_and_tool_output_decode": workspace.get("decodes", False) and tool_output.get("decodes", False),
            "workspace_matches_tool_output": workspace.get("sha256") == tool_output.get("sha256"),
            "workspace_matches_job_hash": workspace.get("sha256") == (job.get("output_sha256") or job.get("asset_sha256")),
            "recorded_output_dimensions_match": workspace.get("dimensions") == job.get("output_dimensions"),
            "builtin_generator_recorded": job.get("mode") == "builtin_imagegen" or job.get("tool") in ("builtin_image_gen", "builtin_imagegen"),
            "job_accepted_false": job.get("accepted") is False,
            "selected_unique_and_correct_frame": len(selected) == 1 and selected[0]["source_frame"] == job["source_frame"],
            "selection_accepted_false": bool(selected) and all(item.get("accepted") is False for item in selected),
        }
        appendix.append({"job_document": base.file_record(str(path)), "job_fields": job,
                         "source_cel": cel, "source_frame": job["source_frame"],
                         "expected_full_source_exposures": expected_exposures,
                         "prompt_sha256_utf8": base.hashlib.sha256(job.get("prompt", "").encode("utf-8")).hexdigest(),
                         "ordered_reference_roles": refs, "workspace_output": workspace,
                         "original_tool_output": tool_output, "checks": appendix_checks,
                         "selection_records": selected,
                         "excluded_from_sealed_27_call_archive": True})
    appendix_new_cels = {record["source_cel"] for record in appendix if record["selection_records"]
                        and not previous_cels[record["source_cel"]]["selected_asset"]} - new_selected_cels
    appendix_new_frames = sum(cel in appendix_new_cels for cel in source["frame_to_cel"])
    if args.final:
        checks["final_global_mapping_gain_explained_by_sealed_batch_and_appendix"] = (
            coverage["independent_recomputed_counts"]["mapped_cels_including_source_reuse"]
            == previous_manifest["summary"]["mapped_cels_including_source_reuse"] + len(new_selected_cels) + len(appendix_new_cels))
        checks["final_global_frame_gain_explained_by_sealed_batch_and_appendix"] = (
            coverage["independent_recomputed_counts"]["covered_frames_draft_plus_source_reuse"]
            == previous_manifest["summary"]["covered_frames_draft_plus_source_reuse"] + new_source_frames + appendix_new_frames)
    snapshots = {name: base.file_record(name) for name in render_input_names(base, meta)}
    freeze = None
    if args.freeze:
        freeze = freeze_record(base, args.freeze, args.freeze_sha, meta)
    appendix_archive = appendix_archive_record(base, args.appendix_archive, args.appendix_archive_sha, appendix) if args.appendix_archive else None
    encoded_freeze = encoded_freeze_record(base, args.encoded_freeze, args.encoded_freeze_sha, verifications) if args.encoded_freeze else None
    f967 = next(record for record in records if record["source_frame"] == 967)
    caption_note = f967["original_job_fields"].get("post_generation_source_audit", "")
    checks["original_f967_prompt_preserved_with_f966_boundary_correction"] = (
        "original lyric phase switches at967" in f967["prompt"]
        and "at966 inside cel965 exposure, not967" in caption_note)
    failures = []
    for group, group_checks in [("archive", archive_checks), ("source_and_selections", checks),
                                 ("timeline", timeline["checks"]), ("coverage", coverage["checks"]),
                                 ("star_proposal", star_proposal["checks"])]:
        failures += [f"{group}: {name}" for name, passed in group_checks.items() if not passed]
    for record in records:
        failures += [f"{record['job_id']}: {name}" for name, passed in record["checks"].items() if not passed]
    for record in verifications + probes + appendix:
        failures += [f"{record.get('path', record.get('video'))}: {name}" for name, passed in record["checks"].items() if not passed]
    if freeze:
        failures += [f"output_freeze: {name}" for name, passed in freeze["checks"].items() if not passed]
    for name, record in (("appendix_archive", appendix_archive), ("encoded_freeze", encoded_freeze)):
        if record:
            failures += [f"{name}: {check}" for check, passed in record["checks"].items() if not passed]
    if args.final and len(verifications) != 2:
        failures.append("final audit requires exactly two technical verification JSONs")
    report = {
        "snapshot_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "final" if args.final else "before_outputs",
        "scope": "File integrity, provenance, exact source timeline, global coverage, and technical reports. No artistic or actual-speed acceptance.",
        "auditor_code": {"private_auditor": base.file_record(str(Path(__file__).resolve())),
                         "imported_integrity_helpers": base.file_record(str(PRIOR / "audit.py"))},
        "sealed_archive": {"path": str(sealed_path.resolve()), "sha256": base.digest(sealed_path), "checks": archive_checks},
        "source_video": base.file_record(meta["source"]), "source_and_selection_checks": checks,
        "historical_batch_gain": {"selected_previously_missing_cels": len(new_selected_cels),
                                  "new_source_frames": new_source_frames,
                                  "previous_manifest_sha256": base.digest(ROOT / "qa/fast-fullpv-batch-2026-10-04-progress-snapshot.json")},
        "appendix_gain": {"selected_previously_missing_cels": len(appendix_new_cels),
                          "new_source_frames": appendix_new_frames},
        "jobs": records, "cyan_timeline": timeline, "coverage": coverage, "star_proposal": star_proposal,
        "technical_verifications": verifications, "independent_video_probes": probes,
        "repair_appendix": appendix, "code_and_data_snapshot": snapshots, "root_output_freeze": freeze,
        "appendix_archive": appendix_archive, "encoded_layer_freeze": encoded_freeze,
        "code_and_data_snapshot_stage": "after_render" if args.final else "before_outputs",
        "outputs_pending": len(verifications) != 2, "failed_checks": failures,
        "integrity_checks_pass": not failures,
        "artistic_accepted": False, "actual_speed_review_performed_by_auditor": False,
        "limitations": [
            "Recorded job calls are not independent proof of generation invocation count.",
            "Hash and numerical checks do not establish visual quality or artistic acceptance.",
            "No original-speed playback was performed by this auditor.",
            "Final code/data hashes are captured after render; equality to the earlier freeze applies only to files it actually records.",
        ],
    }
    destination = HERE / ("final-integrity-audit.json" if args.final else "before-output-integrity-audit.json")
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"audit": str(destination), "integrity_checks_pass": not failures, "failed_checks": failures,
                      "archive": report["sealed_archive"], "timeline": timeline,
                      "coverage": coverage["independent_recomputed_counts"], "outputs_pending": report["outputs_pending"]}, indent=2))


if __name__ == "__main__":
    main()
