"""Inventory strict-source PV drafts without changing source maps or selecting new art."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

from PIL import Image

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recorded_issues(job):
    static = job.get("static_review")
    groups = [job.get("known_issues", [])]
    if isinstance(static, dict):
        groups.append(static.get("flaws", []))
    return list(dict.fromkeys(issue for group in groups if isinstance(group, list)
                              for issue in group if isinstance(issue, str)))


def recorded_acceptance(records):
    evidence = []
    for provenance, record in records:
        field = next((key for key in ("artistic_accepted", "accepted")
                      if isinstance(record.get(key), bool)), None)
        if field:
            evidence.append({"source": provenance, "field": field, "value": record[field]})
    values = {record["value"] for record in evidence}
    accepted = next(iter(values)) if len(values) == 1 else None
    status = ("conflicting" if len(values) > 1 else
              "not_recorded" if not values else
              "accepted" if accepted else "explicit_not_accepted")
    return {"artistic_accepted": accepted, "artistic_acceptance_status": status,
            "artistic_acceptance_records": evidence}


def main():
    snapshot = datetime.now(timezone.utc).isoformat()
    source = read(ROOT / "source_map.json")
    metadata = read(ROOT / "source_meta.json")
    aliases = read(ROOT / "source_aliases.json")["aliases"]
    selections = read(ROOT / "asset_selections.json")["selections"]
    selection_issues = {Path(row["path"]).name: recorded_issues(row)
                        for row in selections if row["path"]}
    generated_paths = list((ROOT / "generated").glob("*.png"))
    jobs = [(path, read(path)) for path in sorted((ROOT / "jobs").glob("*.json"))]
    inventory = []
    for path in generated_paths:
        entry = {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}
        try:
            with Image.open(path) as image:
                image.load()
                entry.update({"dimensions": list(image.size), "decoded": True,
                              "aspect_16_9": image.width * 9 == image.height * 16})
        except Exception as error:
            entry.update({"decoded": False, "error": str(error)})
        inventory.append(entry)
    by_name = defaultdict(list)
    for path, job in jobs:
        if isinstance(job.get("output"), str):
            by_name[Path(job["output"]).name].append((path, job))
    rows = []
    for anchor in read(ROOT / "generation_jobs.json")["old_anchor_to_cel"]:
        stem = f"candidate-{anchor['old_id']}"
        choices = [ROOT / "generated" / f"{stem}{suffix}.png" for suffix in ("-red-eyes", "-clean", "")]
        asset = next((path for path in choices if path.exists()), None)
        if asset:
            rows.append((anchor["old_source_frame"], asset, None))
    for path in generated_paths:
        match = re.fullmatch(r"(?:fine|opening)-f(\d+)\.png", path.name)
        if match:
            rows.append((int(match[1]), path, None))
    for selection in selections:
        rows = [(frame, path, review) for frame, path, review in rows if frame != selection["source_frame"]]
        if selection["path"]:
            rows.append((selection["source_frame"], ROOT / selection["path"], selection))
    assets = {}
    for frame, path, selection in rows:
        candidate = next(c for c in source["candidates"] if c["start"] <= frame < c["end"])
        assets[candidate["cel"]] = {"path": str(path.relative_to(ROOT)), "source_frame": frame,
                                     "selection_review": selection["review"] if selection else None,
                                     "selection_metadata": selection, "verified_alias": None,
                                     "selection_known_issues": selection_issues.get(path.name, [])}
    direct_asset_count = len(assets)
    for alias in aliases:
        if alias["review"] == "manual_full_resolution_source_approved" and alias["verified_target_cel"] in assets:
            assets[alias["source_cel"]] = {**assets[alias["verified_target_cel"]], "verified_alias": alias}
    blocked = {}
    for selection in selections:
        if selection["path"] is None:
            cel = source["frame_to_cel"][selection["source_frame"]]
            blocked[cel] = selection
    unresolved_blocked = {cel: record for cel, record in blocked.items() if cel not in assets}
    exposures = defaultdict(list)
    for span in source["source_exposures"]:
        exposures[span["cel"]].append({key: span[key] for key in ("start", "end", "pts", "end_pts", "family", "source_transform")})
    cel_records = []
    for candidate in source["cels"]:
        cel = candidate["cel"]
        asset = assets.get(cel)
        documents, flaws, repair_flags, caption_cleanup = [], [], [], False
        acceptance_records = []
        if asset:
            if asset["selection_metadata"]:
                acceptance_records.append((f"asset_selections.json#source_frame={asset['source_frame']}",
                                           asset["selection_metadata"]))
            flaws.extend(asset.get("selection_known_issues", []))
            for path, job in by_name[Path(asset["path"]).name]:
                acceptance_records.append((str(path.relative_to(ROOT)), job))
                documents.append({"path": str(path.relative_to(ROOT)), "status": job.get("status"),
                                  "inspection": job.get("inspection"), "static_review": job.get("static_review"),
                                  "review": job.get("review"), "known_issues": job.get("known_issues"),
                                  "continuity_status": job.get("continuity_status"), "temporal_review": job.get("temporal_review")})
                flaws.extend(recorded_issues(job))
                repair_flags.extend(job.get("repair_flags", []))
                caption_cleanup |= job.get("caption_cleanup_required", False)
        acceptance = recorded_acceptance(acceptance_records)
        review = asset["selection_review"] if asset else None
        if review and any(word in review for word in ("extra_lower_hair", "stray_lower_hair", "display_width", "finger_coverage", "sleeve_contour_changed", "costume_continuity_pending")):
            repair_flags.append(review)
        is_empty = cel == "cel-0064"
        status = ("verified_source_reuse_no_character" if is_empty and asset else
                  "blocked_existing_failed_variants" if cel in unresolved_blocked else
                  "draft_with_recorded_flaws" if asset and (flaws or repair_flags or caption_cleanup) else
                  "draft_temporal_review_pending" if asset else "missing_selected_replacement")
        record = {"cel": cel, "source_candidate": candidate["id"], "canonical_source_frame": candidate["frame"],
                  "source_reference": candidate["reference"], "canonical_family": candidate["family"],
                  "exposure_families": sorted({e["family"] for e in exposures[cel]}),
                  "source_exposures": exposures[cel], "source_frames_covered": sum(e["end"] - e["start"] for e in exposures[cel]),
                  "selected_asset": asset, "status": status, **acceptance,
                  "recorded_flaws": list(dict.fromkeys(flaws)), "repair_flags": list(dict.fromkeys(repair_flags)),
                  "caption_cleanup_required": bool(caption_cleanup), "job_documents": documents,
                  "blocked_selection": blocked.get(cel),
                  "historical_blocked_selection_resolved": cel in blocked and asset is not None}
        if candidate["frame"] in (3055, 3067):
            record["semantic_override_note"] = "Full-resolution source inspected: this blank_transition label contains a large back-facing head/hair/body. Character replacement is mandatory."
        cel_records.append(record)
    by_cel = {record["cel"]: record for record in cel_records}
    frame_flags = [cel in assets for cel in source["frame_to_cel"]]
    reuse_flags = [cel == "cel-0064" and cel in assets for cel in source["frame_to_cel"]]
    runs = []
    for span in source["source_exposures"]:
        if not runs or runs[-1]["family"] != span["family"]:
            runs.append({"family": span["family"], "start": span["start"], "end": span["end"], "cels": []})
        runs[-1]["end"] = span["end"]
        if span["cel"] not in runs[-1]["cels"]:
            runs[-1]["cels"].append(span["cel"])
    owners = {}
    packages = []
    for index, run in enumerate(runs):
        identifier = f"shot-{index + 1:02d}-{run['family']}-f{run['start']:04d}-f{run['end']:04d}"
        owned, shared = [], []
        for cel in run["cels"]:
            if cel not in owners:
                owners[cel] = identifier
                owned.append(cel)
            else:
                shared.append({"cel": cel, "owner": owners[cel]})
        packages.append({"id": identifier, **run, "owned_cels": owned, "shared_cels": shared,
                         "missing_owned_cels": [cel for cel in owned if cel not in assets],
                         "blocked_owned_cels": [cel for cel in owned if cel in unresolved_blocked],
                         "owned_drafts_with_recorded_flaws": [cel for cel in owned if by_cel[cel]["status"] == "draft_with_recorded_flaws"],
                         "required_work": "Verify local source/delta, create genuine missing independent cels, then single-frame/adjacent/cycle/actual-speed review. No still-frame padding or automatic merge.",
                         "parallel_policy": "Independent shot groups can run in parallel after identity anchors. Shared source cels remain owned by their first package; do not regenerate duplicates."})
    family_summary = []
    for family in source["families"]:
        cels = {e["cel"] for e in source["source_exposures"] if e["family"] == family}
        family_summary.append({"family": family, "source_cels": len(cels),
                               "mapped_draft_or_reuse_cels": sum(cel in assets for cel in cels),
                               "missing_selected_cels": sum(cel not in assets for cel in cels),
                               "blocked_existing_failed_cels": sum(cel in unresolved_blocked for cel in cels),
                               "drafts_with_structured_flaws_or_cleanup": sum(by_cel[cel]["status"] == "draft_with_recorded_flaws" for cel in cels),
                               "accepted_cels": sum(by_cel[cel]["artistic_accepted"] is True for cel in cels)})
    total = source["frames"]
    first_gap = next((i for i, flag in enumerate(frame_flags) if not flag), total)
    summary = {"source_frames": total, "source_cel_upper_bound": len(source["cels"]),
               "raw_generated_png_files": len(generated_paths), "job_json_files": len(jobs),
               "direct_selected_asset_cels": direct_asset_count, "direct_generated_character_cels": direct_asset_count - 1,
               "verified_alias_expansion_cels": len(assets) - direct_asset_count,
               "alias_inclusive_character_cels": len(assets) - 1, "source_reuse_no_character_cels": 1,
               "mapped_cels_including_source_reuse": len(assets), "missing_selected_cels": len(source["cels"]) - len(assets),
               "blocked_failed_cels": len(unresolved_blocked),
               "historical_blocked_selection_records_resolved": len(blocked) - len(unresolved_blocked),
               "covered_frames_draft_plus_source_reuse": sum(frame_flags),
               "coverage_percent_draft_plus_source_reuse": 100 * sum(frame_flags) / total,
               "character_replacement_draft_frames": sum(frame_flags) - sum(reuse_flags),
               "verified_no_character_source_reuse_frames": sum(reuse_flags),
               "contiguous_available_prefix_frames": first_gap,
               "drafts_with_structured_flaws_or_cleanup": sum(r["status"] == "draft_with_recorded_flaws" for r in cel_records),
               "accepted_character_cels": sum(r["artistic_accepted"] is True and r["cel"] != "cel-0064" for r in cel_records),
               "artistic_acceptance_status_counts": dict(Counter(r["artistic_acceptance_status"] for r in cel_records)),
               "mapped_artistic_acceptance_status_counts": dict(Counter(r["artistic_acceptance_status"] for r in cel_records if r["selected_asset"])),
               "job_statuses": dict(Counter(job.get("status", "missing") for _, job in jobs)),
               "late_worker_missing_cels_canonical_frame_ge_2400": sum(r["canonical_source_frame"] >= 2400 and r["selected_asset"] is None for r in cel_records)}
    camera = source["deduplication"]["camera_similarity_evidence"]
    report = {"snapshot_utc": snapshot, "scope": "full-PV source-map coverage audit, not final artistic acceptance",
              "summary": summary, "families": family_summary,
              "deduplication_evidence": {"raw_candidates": len(source["candidates"]),
                                         "first_stage_types": dict(Counter(c["review"] for c in source["candidates"])),
                                         "second_stage_types": dict(Counter(e["proof"]["kind"] for e in camera)),
                                         "already_confirmed_source_camera_examples": camera[:6],
                                         "uncertain_pairs_kept_separate": len(source["deduplication"]["uncertain_pairs_kept_separate"]),
                                         "approved_manual_aliases": aliases,
                                         "additional_unapproved_local_copy_candidates": read(ROOT / "qa/late-title-copy-candidates.json"),
                                         "merge_policy": "Only approved source_aliases apply. Additional low residuals do not change this inventory or authorize holds."},
              "semantic_findings": [{"frames": [3055, 3067], "severity": "critical",
                                     "finding": "blank_transition contains back-facing people; both source references were viewed and must be replaced."},
                                    {"cel": "cel-0064", "finding": "The recorded source-reuse cel has no visible person. Its 50 repeated source frames are not generated character animation."}],
              "limitations": ["Counts follow current make_timeline discovery/override/alias rules; generated PNG variants are not independent source cels.",
                              "Structured recorded flaws are a lower bound. Unstructured inspection notes are retained per cel but are not automatically labeled bad.",
                              "Artistic acceptance follows explicit selected-asset job/selection booleans only; missing or conflicting records remain null. False records mean explicitly not accepted, not necessarily rejected.",
                              "Technical success and source alias approval do not grant artistic acceptance. Mapped coverage and artwork acceptance do not imply suitable layers, original-speed continuity or deliverability.",
                              "Family/canonical labels may straddle transitions. Ownership and coverage are derived from exact source_exposures.",
                              "Generation may continue while this snapshot is written. Refresh before final full-PV render."],
              "generated_asset_inventory": inventory,
              "provenance": {str(path.relative_to(ROOT)): digest(path) for path in
                             [ROOT / "source_map.json", ROOT / "source_aliases.json", ROOT / "asset_selections.json", ROOT / "make_timeline.py", ROOT / "compose.py"]}}
    manifest = {"snapshot_utc": snapshot, "source": source["source"], "frames": total, "mode": "strict_source",
                "summary": summary, "cels": cel_records, "work_packages": packages,
                "late_worker_missing_queue": [r for r in cel_records if r["canonical_source_frame"] >= 2400 and r["selected_asset"] is None],
                "accepted": False}
    (ROOT / "full-pv-coverage-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (ROOT / "full-pv-progress-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
