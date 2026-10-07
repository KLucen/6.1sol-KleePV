"""Private integrity audit. Reads shared production files and writes only here."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCE_SHA256 = "27b5b242fe6ea8f93ae3ce4d794451aa78a25d1796c45f3bbc3b46b17ed880b7"
ROOT_FRAMES = [965, 967, 969, 973, 975, 980, 981, 984, 987, 992, 993, 997, 998, 1002, 1003]
ROOT_IDS = [f"fast-fullpv-cyan-f{frame:04d}-v1" for frame in ROOT_FRAMES]
ROOT_IDS.insert(ROOT_IDS.index("fast-fullpv-cyan-f0975-v1") + 1, "fast-fullpv-cyan-f0975-hair-v2")
ROOT_IDS.insert(ROOT_IDS.index("fast-fullpv-cyan-f0981-v1") + 1, "fast-fullpv-cyan-f0981-nod-v2")
STAR_FRAMES = [1009, 1010, 1012, 1013, 1014, 1023, 1025, 1033, 1037, 1038]
STAR_IDS = [f"star-gestures-f{frame:04d}-fast-v1" for frame in STAR_FRAMES]
FORBIDDEN = {"generated/fast-fullpv-cyan-f0975-v1.png", "generated/fast-fullpv-cyan-f0981-v1.png"}
EXPOSURE_KEYS = ("start", "end", "pts", "end_pts", "family", "source_transform")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def resolve(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def norm(value):
    return str(value).replace("\\", "/")


def file_record(value, image=False):
    path = resolve(value)
    record = {"recorded_path": value, "absolute_path": str(path.resolve()), "exists": path.is_file()}
    if record["exists"]:
        record.update({"bytes": path.stat().st_size, "sha256": digest(path)})
        if image:
            with Image.open(path) as picture:
                record["dimensions"] = list(picture.size)
                picture.verify()
            record["decodes"] = True
    return record


def source_exposures(source, cel):
    return [{key: span[key] for key in EXPOSURE_KEYS} for span in source["source_exposures"] if span["cel"] == cel]


def capture_job(identifier, group, source, selections):
    path = ROOT / "jobs" / f"{identifier}.json"
    job = read(path)
    workspace_path = job.get("output") or job.get("output_path") or job.get("expected_output")
    origin_path = job.get("original_tool_output") or job.get("generated_origin")
    workspace = file_record(workspace_path, image=True)
    origin = file_record(origin_path, image=True)
    expected_hash = job.get("asset_sha256") or job.get("output_sha256")
    if group == "root_cyan":
        ordered_refs = [{"path": value, "role": role} for value, role in zip(job["references"], job["reference_roles"])]
        role_count_matches = len(job["references"]) == len(job["reference_roles"])
        cel = job["canonical_cel"]
    else:
        ordered_refs = job["ordered_reference_roles"]
        role_count_matches = bool(ordered_refs)
        cel = job["source_cel"]
    refs = []
    for index, reference in enumerate(ordered_refs, start=1):
        record = {"order": index, **reference, "file": file_record(reference["path"], image=True)}
        if reference.get("sha256"):
            record["recorded_hash_matches"] = reference["sha256"] == record["file"].get("sha256")
        refs.append(record)
    selected = [item for item in selections if norm(item.get("path", "")) == norm(workspace_path)]
    prompt = job.get("prompt", "")
    checks = {
        "full_prompt_present": bool(prompt and len(prompt) > 500),
        "ordered_reference_roles_present": role_count_matches and all(ref["role"] for ref in refs),
        "all_references_exist_and_decode": all(ref["file"].get("decodes") for ref in refs),
        "all_recorded_reference_hashes_match": all(ref.get("recorded_hash_matches", True) for ref in refs),
        "workspace_exists_and_decodes": workspace.get("decodes", False),
        "original_tool_output_exists_and_decodes": origin.get("decodes", False),
        "workspace_matches_original_tool_output": workspace.get("sha256") == origin.get("sha256"),
        "workspace_matches_job_hash": bool(expected_hash) and expected_hash == workspace.get("sha256"),
        "source_frame_matches_cel": source["frame_to_cel"][job["source_frame"]] == cel,
        "source_exposures_unchanged": job["source_exposures"] == source_exposures(source, cel),
        "job_accepted_false": job.get("accepted") is False,
        "selected_records_accepted_false": all(item.get("accepted") is False for item in selected),
        "selected_as_expected": bool(selected) == (norm(workspace_path) not in FORBIDDEN),
        "selected_record_unique_and_correct_frame": not selected or (
            len(selected) == 1 and selected[0]["source_frame"] == job["source_frame"]),
    }
    if job.get("source_meta_sha256"):
        checks["source_meta_recorded_hash_matches"] = job["source_meta_sha256"] == digest(ROOT / "source_meta.json")
    if job.get("source_reference") and job.get("source_sha256"):
        checks["source_reference_recorded_hash_matches"] = job["source_sha256"] == digest(resolve(job["source_reference"]))
    return {
        "job_id": identifier,
        "group": group,
        "job_document": str(path.resolve()),
        "job_document_sha256": digest(path),
        "source_frame": job["source_frame"],
        "source_cel": cel,
        "prompt": prompt,
        "prompt_sha256_utf8": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "ordered_reference_roles": refs,
        "workspace_output": workspace,
        "original_tool_output": origin,
        "recorded_output_sha256": expected_hash,
        "selected": bool(selected),
        "selection_records": selected,
        "source_exposures": job["source_exposures"],
        "checks": checks,
        "original_job_fields": job,
    }


def timeline_record(source, metadata, records):
    path = ROOT / "timeline-cyan-911-1008-fast-draft-v1.json"
    timeline = read(path)
    expected = []
    for span in source["source_exposures"]:
        start, end = max(span["start"], 911), min(span["end"], 1008)
        if start < end:
            expected.append({"start": start, "end": end, "cel": span["cel"],
                             "family": span["family"], "source_matrix": span["source_transform"]["matrix"]})
    actual = [{key: item[key] for key in ("start", "end", "cel", "family", "source_matrix")}
              for item in timeline["output_exposures"]]
    frames = [frame for span in actual for frame in range(span["start"], span["end"])]
    cels = {span["cel"] for span in actual}
    selected_paths = [norm(timeline["assets"][cel]["path"]) for cel in cels]
    root_paths_match = all(norm(timeline["assets"][item["source_cel"]]["path"])
                           == norm(item["workspace_output"]["recorded_path"])
                           for item in records if item["group"] == "root_cyan" and item["selected"])
    return {"path": str(path.resolve()), "sha256": digest(path), "frames": timeline["frames"],
            "unique_cels": len(cels), "source_exposures": len(actual),
            "checks": {"97_source_frames": timeline["frames"] == 97 and frames == list(range(911, 1008)),
                       "source_start_911": timeline["source_start"] == 911,
                       "source_pts_exact": timeline["source_pts"] == metadata["pts"][911:1008],
                       "source_exposures_exact": actual == expected,
                       "36_cels_53_exposures": len(cels) == 36 and len(actual) == 53,
                       "selected_assets_exist": all(resolve(value).is_file() for value in selected_paths),
                       "all15_selected_root_versions_used": root_paths_match,
                       "rejected_baselines_unused": not (set(selected_paths) & FORBIDDEN)}}


def coverage_record(source, selections):
    path = ROOT / "full-pv-coverage-report.json"
    coverage = read(path)
    manifest = read(ROOT / "full-pv-progress-manifest.json")
    generated = list((ROOT / "generated").glob("*.png"))
    jobs = list((ROOT / "jobs").glob("*.json"))
    rows = []
    for anchor in read(ROOT / "generation_jobs.json")["old_anchor_to_cel"]:
        choices = [ROOT / "generated" / f"candidate-{anchor['old_id']}{suffix}.png" for suffix in ("-red-eyes", "-clean", "")]
        chosen = next((item for item in choices if item.is_file()), None)
        if chosen:
            rows.append((anchor["old_source_frame"], chosen))
    for item in generated:
        match = re.fullmatch(r"(?:fine|opening)-f(\d+)\.png", item.name)
        if match:
            rows.append((int(match[1]), item))
    for selection in selections:
        rows = [(frame, item) for frame, item in rows if frame != selection["source_frame"]]
        if selection["path"]:
            rows.append((selection["source_frame"], resolve(selection["path"])))
    assets = {source["frame_to_cel"][frame]: item for frame, item in rows}
    direct_count = len(assets)
    for alias in read(ROOT / "source_aliases.json")["aliases"]:
        if alias["review"] == "manual_full_resolution_source_approved" and alias["verified_target_cel"] in assets:
            assets[alias["source_cel"]] = assets[alias["verified_target_cel"]]
    flags = [cel in assets for cel in source["frame_to_cel"]]
    mapped = [record for record in manifest["cels"] if record["selected_asset"]]
    recomputed = {
        "source_frames": source["frames"], "source_cel_upper_bound": len(source["cels"]),
        "raw_generated_png_files": len(generated), "job_json_files": len(jobs),
        "direct_selected_asset_cels": direct_count, "verified_alias_expansion_cels": len(assets) - direct_count,
        "mapped_cels_including_source_reuse": len(assets), "missing_selected_cels": len(source["cels"]) - len(assets),
        "covered_frames_draft_plus_source_reuse": sum(flags),
        "coverage_percent_draft_plus_source_reuse": 100 * sum(flags) / source["frames"],
        "contiguous_available_prefix_frames": next((index for index, flag in enumerate(flags) if not flag), source["frames"]),
        "drafts_with_structured_flaws_or_cleanup": sum(item["status"] == "draft_with_recorded_flaws" for item in manifest["cels"]),
        "accepted_character_cels": sum(item["artistic_accepted"] is True and item["cel"] != "cel-0064" for item in manifest["cels"]),
        "mapped_artistic_acceptance_status_counts": dict(Counter(item["artistic_acceptance_status"] for item in mapped)),
    }
    provenance = {name: {"recorded_sha256": value, "current_sha256": digest(ROOT / name),
                         "matches": digest(ROOT / name) == value} for name, value in coverage["provenance"].items()}
    return {"path": str(path.resolve()), "sha256": digest(path), "summary": coverage["summary"],
            "independent_recomputed_counts": recomputed, "provenance": provenance,
            "checks": {"recomputed_counts_match": all(coverage["summary"][key] == value for key, value in recomputed.items()),
                       "manifest_summary_matches": coverage["summary"] == manifest["summary"],
                       "all_mapped_assets_exist": all(item.is_file() for item in assets.values()),
                       "zero_artistic_acceptance": recomputed["accepted_character_cels"] == 0,
                       "coverage_provenance_current": all(item["matches"] for item in provenance.values())}}


def verification_record(value):
    path = resolve(value)
    document = read(path)
    video = file_record(document["video"])
    return {"path": str(path.resolve()), "sha256": digest(path), "video": video,
            "source_interval": document["source_interval"], "expected_frames": document["expected_frames"],
            "technical_pass": document["technical_pass"], "reported_checks": document["checks"],
            "artistic_review": document["artistic_review"],
            "checks": {"technical_pass_true": document["technical_pass"] is True,
                       "all_reported_checks_true": all(value is True for value in document["checks"].values()),
                       "output_hash_matches_verification": document["video_sha256"] == video.get("sha256"),
                       "97_frames_source_interval": document["source_interval"] == [911, 1008] and document["expected_frames"] == 97}}


def star_proposal_record(records):
    path = ROOT / "qa/fast-fullpv-star-gestures-2026-10-04/draft-proposal.json"
    proposal = read(path)
    by_frame = {item["source_frame"]: item for item in proposal["selections"]}
    checks = {"ten_star_frames_exact": sorted(by_frame) == STAR_FRAMES,
              "proposal_accepted_false": proposal.get("accepted") is False,
              "source_meta_hash_matches": proposal["source_meta_sha256"] == digest(ROOT / "source_meta.json")}
    for record in records:
        if record["group"] != "star_gestures":
            continue
        item = by_frame[record["source_frame"]]
        checks[f"f{record['source_frame']}_selected_path_hash_exposures_match"] = (
            norm(item["path"]) == norm(record["workspace_output"]["recorded_path"])
            and item["sha256"] == record["workspace_output"]["sha256"]
            and item["source_exposures"] == record["source_exposures"]
            and item.get("accepted") is False
            and item["source_cel"] == record["source_cel"]
            and item["source_sha256"] == digest(resolve(item["source_reference"])))
    return {"path": str(path.resolve()), "sha256": digest(path), "checks": checks}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verification", action="append", default=[])
    args = parser.parse_args()
    metadata = read(ROOT / "source_meta.json")
    source = read(ROOT / "source_map.json")
    selections = read(ROOT / "asset_selections.json")["selections"]
    records = [capture_job(identifier, "root_cyan", source, selections) for identifier in ROOT_IDS]
    records += [capture_job(identifier, "star_gestures", source, selections) for identifier in STAR_IDS]
    stamp = datetime.now(timezone.utc).isoformat()
    prompt_archive = HERE / "batch2-full-27call-promptset.json"
    if not prompt_archive.is_file():
        archive = {"snapshot_utc": stamp, "scope": "Current batch2: 17 root cyan calls including 2 rejected baselines, plus 10 star calls.",
                   "source_video_sha256": SOURCE_SHA256, "calls": len(records), "selected": sum(item["selected"] for item in records),
                   "field_normalization": {"root": "canonical_cel, output, original_tool_output, asset_sha256, references + reference_roles",
                                           "star": "source_cel, output_path, generated_origin, output_sha256, ordered_reference_roles",
                                           "lossless_policy": "Full prompt and source_exposures retained; every original job field is included."},
                   "artistic_accepted": False, "actual_speed_review_performed_by_auditor": False, "jobs": records}
        prompt_archive.write_text(json.dumps(archive, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    sealed = read(prompt_archive)
    sealed_by_id = {item["job_id"]: item for item in sealed["jobs"]}
    archive_matches = all(sealed_by_id[item["job_id"]]["prompt"] == item["prompt"]
                          and sealed_by_id[item["job_id"]]["source_exposures"] == item["source_exposures"]
                          and sealed_by_id[item["job_id"]]["ordered_reference_roles"] == item["ordered_reference_roles"]
                          for item in records)
    f967 = next(item for item in records if item["source_frame"] == 967)
    note = f967["original_job_fields"].get("post_generation_source_audit", "")
    caption_correction = {"original_submitted_prompt_excerpt": "this current frame's original lyric phase switches at967",
                          "preserved_in_original_prompt": "original lyric phase switches at967" in f967["prompt"],
                          "post_generation_source_audit": note,
                          "explicit_boundary966_inside_cel965": "at966 inside cel965 exposure, not967" in note,
                          "character_source_frame_remains": f967["source_frame"]}
    report = {"snapshot_utc": stamp, "scope": "Independent file, provenance, selection, source exposure, coverage and technical-result integrity only.",
              "source_video": file_record(metadata["source"]),
              "source_identity_matches_expected": metadata["sha256"] == SOURCE_SHA256 and digest(resolve(metadata["source"])) == SOURCE_SHA256,
              "prompt_archive": {"path": str(prompt_archive.resolve()), "sha256": digest(prompt_archive), "calls": sealed["calls"],
                                 "selected": sealed["selected"], "matches_current_full_prompts_refs_exposures": archive_matches},
              "jobs": records, "f967_caption_correction": caption_correction,
              "selection_checks": {"15_root_selected": sum(item["selected"] for item in records if item["group"] == "root_cyan") == 15,
                                   "10_star_selected": sum(item["selected"] for item in records if item["group"] == "star_gestures") == 10,
                                   "rejected_baselines_not_selected": not any(norm(item.get("path", "")) in FORBIDDEN for item in selections)},
              "cyan_timeline": timeline_record(source, metadata, records), "coverage": coverage_record(source, selections),
              "star_draft_proposal": star_proposal_record(records),
              "technical_verifications": [verification_record(value) for value in args.verification],
              "outputs_pending": len(args.verification) != 2,
              "artistic_accepted": False, "actual_speed_review_performed_by_auditor": False,
              "limitations": ["Full prompts are archived verbatim from job records; generation tool invocations are not independently replayed.",
                              "Output hash matching verifies files, not visual quality. No artistic acceptance or actual-speed viewing is granted.",
                              "Root reference hashes are audit snapshots where submitted jobs did not record hashes."]}
    failed = [f"{item['job_id']}: {name}" for item in records for name, ok in item["checks"].items() if not ok]
    failed += [f"selections: {name}" for name, ok in report["selection_checks"].items() if not ok]
    failed += [f"cyan_timeline: {name}" for name, ok in report["cyan_timeline"]["checks"].items() if not ok]
    failed += [f"coverage: {name}" for name, ok in report["coverage"]["checks"].items() if not ok]
    failed += [f"star_draft_proposal: {name}" for name, ok in report["star_draft_proposal"]["checks"].items() if not ok]
    failed += [f"verification {item['path']}: {name}" for item in report["technical_verifications"] for name, ok in item["checks"].items() if not ok]
    if not report["source_identity_matches_expected"]:
        failed.append("source_identity_matches_expected")
    if not archive_matches:
        failed.append("prompt_archive_matches_current_full_prompts_refs_exposures")
    report["failed_checks"] = failed
    report["integrity_checks_pass"] = not failed
    destination = HERE / "integrity-audit.json"
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    summary = {"audit": str(destination.resolve()), "integrity_checks_pass": not failed, "failed_checks": failed,
               "prompt_archive": report["prompt_archive"], "root_jobs": len(ROOT_IDS), "star_jobs": len(STAR_IDS),
               "selected_root": 15, "selected_star": 10, "cyan_timeline": report["cyan_timeline"],
               "coverage_summary": report["coverage"]["summary"], "outputs_pending": report["outputs_pending"]}
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
