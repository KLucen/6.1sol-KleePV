"""Read-only audit of delivery inputs; writes only its private QA result."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PAIRS = [
    ("output/klee-dance-812-911-fast-draft-v11.mp4", "qa/dance-812-911-fast-draft-v11-single-verification.json"),
    ("output/klee-dance-812-911-comparison-fast-draft-v11.mp4", "qa/dance-812-911-fast-draft-v11-comparison-verification.json"),
    ("output/klee-raised-1225-1285-fast-draft-v2.mp4", "qa/fast-fullpv-raised/single-v2-technical-verification.json"),
    ("output/klee-raised-1225-1285-comparison-fast-draft-v2.mp4", "qa/fast-fullpv-raised/comparison-v2-technical-verification.json"),
]


def absolute(path):
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def saved(path):
    p = absolute(path)
    return {"path": str(p), "exists": p.is_file(), "sha256": sha(p) if p.is_file() else None}


def main():
    outputs = []
    for video_path, report_path in PAIRS:
        v, r = absolute(video_path), absolute(report_path)
        report = json.loads(r.read_text(encoding="utf-8"))
        checks = report.get("checks", {})
        actual = sha(v)
        outputs.append({"video": str(v), "actual_video_sha256": actual,
                        "verification_report": str(r), "verification_report_sha256": sha(r),
                        "reported_video_sha256": report.get("video_sha256"),
                        "video_sha_matches_report": actual == report.get("video_sha256"),
                        "report_video_path_matches": Path(report["video"]).resolve() == v.resolve(),
                        "technical_pass": report.get("technical_pass") is True,
                        "check_count": len(checks), "all17_checks_true": len(checks) == 17 and all(x is True for x in checks.values()),
                        "failed_checks": [key for key, value in checks.items() if value is not True],
                        "expected_frames": report.get("expected_frames"), "source_interval": report.get("source_interval")})
    timelines = []
    for name in ["timeline-dance-812-911-fast-draft-v11.json", "timeline-raised-1225-1285-fast-draft-v1.json"]:
        p = absolute(name)
        data = json.loads(p.read_text(encoding="utf-8"))
        timelines.append({**saved(name), "source_start": data["source_start"], "frames": data["frames"], "mode": data["mode"], "pts_entries": len(data["source_pts"])})
    aggregate_path = absolute("qa/fast-fullpv-batch-2026-10-04-generation-records.json")
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    raised_link = aggregate["raised_records"]
    raised_path = absolute(raised_link["path"])
    raised = json.loads(raised_path.read_text(encoding="utf-8"))
    groups = [("root_dance", aggregate["root_dance_records"]), ("root_cyan", aggregate["root_cyan_records"]), ("raised", raised["records"])]
    records = []
    for group, entries in groups:
        for entry in entries:
            refs = entry.get("references", entry.get("referenced_image_paths", []))
            roles = entry.get("reference_roles", [])
            role_complete = bool(refs) and len(refs) == len(roles) and all(isinstance(role, str) and role for role in roles)
            reference_hashes = entry.get("reference_sha256", {})
            if "reference_records" in entry:
                reference_hashes = {item["path"]: item["sha256"] for item in entry["reference_records"]}
            reference_results = []
            for ref in refs:
                p = absolute(ref)
                expected = reference_hashes.get(ref)
                reference_results.append({"path": str(p), "saved_sha256": expected, "exists": p.is_file(), "hash_matches": p.is_file() and expected is not None and sha(p) == expected})
            output = absolute(entry.get("output", entry.get("intended_output")))
            job = absolute(entry["job_path"])
            original = absolute(entry.get("original_tool_output", entry.get("tool_output_path")))
            expected_output = entry["output_sha256"]
            record = {"group": group, "job_path": str(job), "job_sha256": sha(job),
                      "job_hash_matches_record": sha(job) == entry["job_sha256"], "source_frame": entry["source_frame"],
                      "full_prompt_saved": isinstance(entry.get("prompt"), str) and bool(entry["prompt"].strip()),
                      "reference_roles_complete": role_complete, "reference_count": len(refs),
                      "all_reference_files_and_hashes_match": all(item["hash_matches"] for item in reference_results),
                      "output_path": str(output), "output_sha256": sha(output), "output_hash_matches_record": sha(output) == expected_output,
                      "tool_output_path": str(original), "tool_output_exists": original.is_file(),
                      "tool_output_hash_matches_project_copy": original.is_file() and sha(original) == expected_output,
                      "call_status_saved": bool(entry.get("status")), "accepted": entry.get("accepted"),
                      "reference_results": reference_results}
            record["complete"] = all(record[key] for key in ["full_prompt_saved", "reference_roles_complete", "all_reference_files_and_hashes_match", "output_hash_matches_record", "job_hash_matches_record", "tool_output_exists", "tool_output_hash_matches_project_copy", "call_status_saved"])
            records.append(record)
    asset_path = "qa/fast-fullpv-batch-2026-10-04-asset-selections-snapshot.json"
    progress_path = "qa/fast-fullpv-batch-2026-10-04-progress-snapshot.json"
    assets = json.loads(absolute(asset_path).read_text(encoding="utf-8"))
    progress = json.loads(absolute(progress_path).read_text(encoding="utf-8"))
    snapshots = [{**saved(asset_path), "selection_count": len(assets["selections"])}, {**saved(progress_path), "missing_selected_cels": progress["summary"]["missing_selected_cels"], "accepted_character_cels": progress["summary"]["accepted_character_cels"]}]
    result = {"audit_utc": datetime.now(timezone.utc).isoformat(), "scope": "Delivery integrity read-only audit, no generation/render/regression/repeated artistic review",
              "outputs": outputs, "timelines": timelines, "snapshots": snapshots,
              "generation_records": {**saved(aggregate_path), "raised_record_file": saved(raised_path), "raised_link_sha_matches": sha(raised_path) == raised_link["sha256"],
                                     "root_dance_count": len(groups[0][1]), "root_cyan_count": len(groups[1][1]), "raised_count": len(groups[2][1]), "total_calls": len(records),
                                     "all32_records_complete": len(records) == 32 and all(r["complete"] for r in records), "records": records},
              "full_pv_missing_selected_cels": progress["summary"]["missing_selected_cels"], "full_pv_complete": False,
              "original_speed_watch": "Not performed by this delivery audit; saved timing/static reports do not imply uninterrupted visual playback", "artistic_accepted": False}
    result["delivery_integrity_pass"] = all(o["video_sha_matches_report"] and o["report_video_path_matches"] and o["technical_pass"] and o["all17_checks_true"] for o in outputs) and result["generation_records"]["all32_records_complete"] and result["generation_records"]["raised_link_sha_matches"] and all(p["exists"] for p in timelines + snapshots) and result["full_pv_missing_selected_cels"] == 300
    report_path = HERE / "batch-delivery-integrity-2026-10-04.json"
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "report_sha256": sha(report_path), "delivery_integrity_pass": result["delivery_integrity_pass"], "outputs": outputs,
                      "generation_count": len(records), "incomplete_records": [r["job_path"] for r in records if not r["complete"]], "missing_selected_cels": result["full_pv_missing_selected_cels"], "timelines": timelines, "snapshots": snapshots}, indent=2))


if __name__ == "__main__":
    main()
