"""Read-only full-draft handoff audit, with an explicit immutable baseline snapshot."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "qa/full-draft-one-pass-2026-10-07"
SELECTION_SHA = "c907f14a02f0d500474a71fe5fc793c22a4c8a07c6398e73dee0389737fa5817"
MANIFEST_SHA = "5e878a6af595fb4bf482666f517ca5b845e3dc1f28401e82fa2914ff212f9fec"
BATCHES = {"middle": ("oct7-bulk-middle", 54), "late_action": ("oct7-bulk-late_action", 44),
           "ending": ("oct7-bulk-ending", 49), "root": ("oct7-bulk-root", 34),
           "root_late": ("oct7-bulk-root-late", 14)}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def normalized(path):
    return Path(path).as_posix().replace("\\", "/")


def main(snapshot_baseline=False, post_adopt=False):
    errors, pending, warnings = [], [], []
    report = {"snapshot_utc": datetime.now(timezone.utc).isoformat(),
              "mode": "post_adopt_preservation" if post_adopt else "frozen_pre_adoption",
              "shared_files_written": False, "owners": {}, "seals": {}}

    def check(condition, message):
        if not condition:
            errors.append(message)

    queue = read(HERE / "ownership-queue-v3.json")
    selection_path, manifest_path = ROOT / "asset_selections.json", ROOT / "full-pv-progress-manifest.json"
    selections, manifest = read(selection_path), read(manifest_path)
    current_hashes = {"asset_selections": digest(selection_path), "manifest": digest(manifest_path)}
    report["shared_sha256"] = current_hashes
    check(set(queue["owners"]) == set(BATCHES), "Ownership must contain exactly the five amended owners")
    check(queue["missing_count"] == 195, "Ownership missing_count is not 195")
    if not post_adopt:
        check(current_hashes["asset_selections"] == SELECTION_SHA, "Frozen original asset_selections SHA changed")
        check(current_hashes["manifest"] == MANIFEST_SHA, "Frozen original manifest SHA changed")

    baseline_path = HERE / "baseline-selection-snapshot.json"
    if snapshot_baseline:
        check(not post_adopt, "Cannot create original baseline after adoption")
        check(not baseline_path.exists(), "Immutable baseline snapshot already exists")
        if not errors:
            baseline = {"snapshot_utc": report["snapshot_utc"], "source": str(selection_path),
                        "selection_sha256": SELECTION_SHA, "manifest_sha256": MANIFEST_SHA,
                        "selection_row_count": len(selections["selections"]),
                        "document_metadata": {k: v for k, v in selections.items() if k != "selections"},
                        "selections": selections["selections"]}
            with baseline_path.open("x", encoding="utf-8") as handle:
                json.dump(baseline, handle, indent=2, ensure_ascii=False)
            report["created_baseline_snapshot"] = {"path": str(baseline_path), "sha256": digest(baseline_path)}

    if baseline_path.exists():
        baseline = read(baseline_path)
        check(baseline["selection_sha256"] == SELECTION_SHA, "Baseline records wrong original selection SHA")
        old_rows = baseline["selections"]
        current_rows = {r["source_frame"]: r for r in selections["selections"]}
        check(len(current_rows) == len(selections["selections"]), "Shared selections contain duplicate frames")
        check(len(old_rows) == baseline["selection_row_count"], "Baseline selection row count mismatch")
        changed = [r["source_frame"] for r in old_rows if current_rows.get(r["source_frame"]) != r]
        check(not changed, f"Original selected rows changed or disappeared: {changed}")
        report["baseline_preservation"] = {"path": str(baseline_path), "sha256": digest(baseline_path),
                                           "original_rows": len(old_rows), "changed_original_frames": changed}
    else:
        pending.append("baseline-selection-snapshot.json missing")

    requested, proposed, outputs, checked_assets, exposure_frames = [], [], [], 0, 0
    manifest_rows = {r["canonical_source_frame"]: r for r in manifest["cels"]}
    for owner, (directory, required_count) in BATCHES.items():
        rows = queue["owners"].get(owner, {}).get("rows", [])
        expected = [r["canonical_source_frame"] for r in rows]
        owner_exposure_frames = sum(e["end"] - e["start"] for r in rows for e in r["source_exposures"])
        exposure_frames += owner_exposure_frames
        requested.extend(expected)
        check(len(expected) == required_count == queue["owners"].get(owner, {}).get("count"),
              f"{owner}: ownership count mismatch")
        check(len(expected) == len(set(expected)), f"{owner}: duplicate ownership frames")
        batch = ROOT / "qa" / directory
        proposal_path = batch / "draft-proposal.json"
        seal_path = batch / "full-builtin-promptset-and-integrity.json"
        summary = {"expected": required_count, "proposal": str(proposal_path),
                   "source_exposure_frames": owner_exposure_frames}
        report["owners"][owner] = summary
        if not proposal_path.exists():
            pending.append(f"{owner}: proposal missing")
            continue
        proposal = read(proposal_path)
        choice_rows = proposal["selections"]
        frames = [r["source_frame"] for r in choice_rows]
        proposed.extend(frames)
        outputs.extend(normalized(r["path"]) for r in choice_rows)
        check(proposal.get("accepted") is False, f"{owner}: proposal not explicitly unaccepted")
        check(len(frames) == len(set(frames)), f"{owner}: duplicate proposed frames")
        extras, missing = sorted(set(frames) - set(expected)), sorted(set(expected) - set(frames))
        check(not extras, f"{owner}: unexpected proposal frames {extras}")
        if missing:
            pending.append(f"{owner}: {len(missing)} missing proposed frames {missing}")
        summary.update({"saved": len(frames), "missing": missing, "proposal_sha256": digest(proposal_path)})
        seal = read(seal_path) if seal_path.exists() else None
        if seal is None:
            pending.append(f"{owner}: seal missing")
            sealed_jobs, integrity = {}, {}
        else:
            sealed_jobs = {j["source_frame"]: j for j in seal["jobs"]}
            integrity = {j["source_frame"]: j for j in seal["integrity"]}
            check(seal.get("accepted") is False and seal.get("tool") == "builtin_imagegen",
                  f"{owner}: invalid seal tool or acceptance")
            check(len(seal["jobs"]) == len(sealed_jobs) == required_count, f"{owner}: sealed jobs count mismatch")
            check(len(seal["integrity"]) == len(integrity) == required_count, f"{owner}: sealed integrity count mismatch")
            check(set(sealed_jobs) == set(integrity) == set(expected), f"{owner}: seal frame set mismatch")
            check(not seal.get("requested_but_ungenerated_frames"), f"{owner}: seal reports missing frames")
            report["seals"][owner] = {"path": str(seal_path), "sha256": digest(seal_path), "jobs": len(sealed_jobs)}

        for choice in choice_rows:
            f = choice["source_frame"]
            label = f"{owner}/f{f}"
            check(choice.get("accepted") is False, f"{label}: choice not explicitly unaccepted")
            job_path, output = ROOT / choice["job"], ROOT / choice["path"]
            if not job_path.exists() or not output.exists():
                errors.append(f"{label}: job/output file missing")
                continue
            job = read(job_path)
            check(job.get("source_frame") == f and job.get("accepted") is False,
                  f"{label}: job frame/acceptance mismatch")
            check(job.get("tool") == "builtin_imagegen", f"{label}: not builtin_imagegen")
            check(normalized(job["output"]) == normalized(choice["path"]), f"{label}: job output path mismatch")
            if seal is not None:
                check(sealed_jobs.get(f) == job, f"{label}: archived job differs from on-disk job")
            raw = output.read_bytes()
            actual_sha = sha256(raw).hexdigest()
            with Image.open(output) as picture:
                dimensions = list(picture.size)
            origin = Path(job["tool_output"])
            check(origin.exists() and raw == origin.read_bytes(), f"{label}: output differs from builtin original")
            check(actual_sha == choice.get("sha256") == job.get("output_sha256"), f"{label}: output SHA mismatch")
            check(dimensions == job.get("dimensions"), f"{label}: job dimensions mismatch")
            check(job.get("source_exposures") == manifest_rows.get(f, {}).get("source_exposures"),
                  f"{label}: exact original exposure timing changed")
            check(job.get("static_review", {}).get("performed") is True, f"{label}: no recorded static review")
            refs = job.get("reference_roles", [])
            check(1 <= len(refs) <= 5 and bool(job.get("prompt")), f"{label}: prompt/reference count invalid")
            if any(ref.get("actually_viewed") is not True for ref in refs):
                warnings.append(f"{label}: per-reference view flags absent/false; inspect supplemental ledgers")
            for ref in refs:
                check(Path(ref["path"]).exists(), f"{label}: missing archived reference {ref['path']}")
            if seal is not None:
                entry = integrity.get(f, {})
                check(entry.get("sha256") == actual_sha and entry.get("dimensions") == dimensions,
                      f"{label}: seal SHA/dimensions mismatch")
                check(entry.get("recorded_sha_exact") is True and entry.get("builtin_origin_byte_exact") is True
                      and entry.get("selected_private") is True and entry.get("accepted") is False,
                      f"{label}: seal integrity flags fail")
                check(normalized(entry.get("output", "")) == normalized(choice["path"]), f"{label}: seal output mismatch")
                for ref in entry.get("references", []):
                    ref_path = Path(ref["path"])
                    check(ref_path.exists() and digest(ref_path) == ref.get("sha256_at_archive"),
                          f"{label}: reference changed after archive {ref['path']}")
            if post_adopt:
                current = next((r for r in selections["selections"] if r["source_frame"] == f), {})
                check(normalized(current.get("path", "")) == normalized(choice["path"])
                      and current.get("accepted") is False, f"{label}: adopted choice missing/wrong/accepted")
            checked_assets += 1

    check(len(requested) == len(set(requested)) == 195, "Amended five-owner queue must be exactly 195 unique frames")
    check(exposure_frames == 790, "Five-owner original exposure coverage must be exactly 790 source frames")
    duplicates = sorted(k for k, v in Counter(proposed).items() if v > 1)
    check(not duplicates, f"Cross-owner duplicate proposals: {duplicates}")
    check(len(outputs) == len(set(outputs)), "Different cels share a proposed output path")
    if len(proposed) != 195:
        pending.append(f"Global proposal count {len(proposed)}/195")
    if not post_adopt:
        missing_manifest = {f for f, row in manifest_rows.items() if row.get("selected_asset") is None}
        check(set(requested) == missing_manifest, "Ownership queue differs from frozen manifest's missing cels")
    report.update({"requested_unique_cels": len(set(requested)), "proposed_unique_cels": len(set(proposed)),
                   "checked_assets": checked_assets, "sealed_owners": len(report["seals"]),
                   "source_exposure_frames": exposure_frames,
                   "errors": errors, "pending": pending, "warning_count": len(warnings), "warnings": warnings,
                   "status": "failed" if errors else "partial" if pending else "ready",
                   "artistic_acceptance": False, "temporal_speed_review": "not_performed_by_preflight"})
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if errors else 2 if pending else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-baseline", action="store_true")
    parser.add_argument("--post-adopt", action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(args.snapshot_baseline, args.post_adopt))
