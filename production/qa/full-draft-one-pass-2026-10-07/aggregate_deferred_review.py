"""Collect existing static-draft notes without inventing final-film art findings."""

from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def distinct(items):
    return list(dict.fromkeys(items))


def main():
    metadata = read(ROOT / "source_meta.json")
    timeline_path = ROOT / "timeline-full-oct7-draft-v1.json"
    timeline = read(timeline_path)
    ownership_path = HERE / "ownership-queue-v3.json"
    ownership = read(ownership_path)
    source_pts = [Fraction(str(p)) for p in metadata["pts"]]
    stream = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    boundary = Fraction(int(stream["duration_ts"]), 16000)

    def ticks(frame):
        return int((source_pts[frame] if frame < len(source_pts) else boundary) * 16000)

    def exact_timecode(frame):
        microseconds = Fraction(ticks(frame), 16000) * 1_000_000
        assert microseconds.denominator == 1
        seconds, microseconds = divmod(int(microseconds), 1_000_000)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}.{microseconds:06}"

    def nominal_timecode(frame):
        seconds, number = divmod(frame, 24)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}:{number:02}"

    def interval(start, end):
        assert 0 <= start < end <= len(source_pts)
        return {"start": start, "end": end, "frame_count": end - start,
                "source_pts_start_ticks": ticks(start), "source_pts_end_ticks": ticks(end),
                "exact_start_timecode": exact_timecode(start), "exact_end_timecode": exact_timecode(end),
                "nominal_24fps_start": nominal_timecode(start), "nominal_24fps_end": nominal_timecode(end)}

    def exposure(row):
        return {**row, "exact_timing": interval(row["start"], row["end"])}

    owner_rows = {}
    for owner, group in ownership["owners"].items():
        for row in group["rows"]:
            frame = row["canonical_source_frame"]
            assert frame not in owner_rows
            owner_rows[frame] = owner, row

    paths = sorted((ROOT / "qa").glob("oct7-bulk-*/draft-proposal.json"))
    assert len(paths) == 5
    records, provenance = [], []
    for path in paths:
        proposal = read(path)
        provenance.append({"path": str(path.resolve()), "sha256": digest(path),
                           "selection_count": len(proposal["selections"]), "accepted": proposal["accepted"]})
        for selection in proposal["selections"]:
            frame = selection["source_frame"]
            owner, frozen = owner_rows[frame]
            job_path = ROOT / selection["job"]
            job = read(job_path)
            cels = [cel for cel, asset in timeline["assets"].items() if asset["path"] == selection["path"]]
            assert frozen["cel"] in cels and job["source_frame"] == frame
            assert not selection["accepted"] and not job["accepted"]
            issues = distinct(selection.get("known_issues", []))
            version = re.search(r"-(v\d+)\.png$", selection["path"])
            records.append({"owner": owner, "source_cel": frozen["cel"], "source_frame": frame,
                            "source_frame_timecode": exact_timecode(frame), "source_frame_pts_ticks": ticks(frame),
                            "version": version.group(1) if version else None, "path": selection["path"],
                            "sha256": selection["sha256"], "proposal": str(path.resolve()),
                            "job": str(job_path.resolve()), "timeline_asset_cels": cels,
                            "source_family_label": frozen["canonical_family"],
                            "source_exposures": [exposure(x) for x in frozen["source_exposures"]],
                            "timeline_exposures": [exposure(x) for x in timeline["output_exposures"] if x["cel"] in cels],
                            "review": selection["review"], "known_issues": issues,
                            "known_issue_entry_count": len(issues), "full_static_review": job.get("static_review"),
                            "original_temporal_review": job.get("temporal_review"),
                            "accepted": False, "status": "deferred_pending_full_film_feedback",
                            "needs_rework": None, "final_composite_observed": False,
                            "original_speed_review_performed": False})
    records.sort(key=lambda x: x["source_frame"])
    assert len(records) == len({r["source_cel"] for r in records}) == 195

    caption_path = ROOT / "qa" / "caption-clear-v3-six-2026-10-06" / "root-encoded-107-native-review.json"
    caption_review = read(caption_path)
    halo_path = ROOT / "qa" / "caption-clear-v2-2026-10-06" / "caption-v2-native-review-seal.json"
    halo_review = read(halo_path)
    middle_path = ROOT / "qa" / "oct6-middle-transition-integration" / "root-encoded24-native-review.json"
    middle_review = read(middle_path)

    def frozen_issue(start, end, issue, origin, text):
        cels = distinct(x["cel"] for x in timeline["output_exposures"] if x["start"] < end and start < x["end"])
        return {"owner": "frozen_existing_layers", "interval": interval(start, end), "issue": issue,
                "affected_timeline_cels": cels,
                "assets": [{"cel": c, **timeline["assets"][c]} for c in cels],
                "overlapping_exposures": [exposure(x) for x in timeline["output_exposures"]
                                          if x["start"] < end and start < x["end"]],
                "historical_evidence": str(origin.resolve()), "historical_review_text": text,
                "accepted": False, "status": "inherited_deferred_not_reobserved_in_oct7_master",
                "final_composite_observed": False, "original_speed_review_performed": False}

    inherited = [
        frozen_issue(1037, 1043, "Japanese low contrast against cream boot ornaments", caption_path,
                     caption_review["known_risks"][0]),
        frozen_issue(1129, 1144, "Japanese character 寂 camouflaged against cream boot/clover ornament", caption_path,
                     caption_review["known_risks"][1]),
        frozen_issue(1144, 1161, "Japanese characters 分/う camouflaged against cream boot/clover ornament", caption_path,
                     caption_review["known_risks"][1]),
        frozen_issue(2121, 2145, "Existing middle chapter minor cold boundary flecks and two hat-edge AA subpixels at f2135", middle_path,
                     middle_review["observations"][3]),
    ]
    inherited[3]["specific_hat_edge_location"] = interval(2135, 2136)
    report = {"snapshot_utc": datetime.now(timezone.utc).isoformat(), "accepted": False,
              "scope": "Private aggregation of recorded cel/static and historical issues only; no new Oct7 encoded observations",
              "timeline": str(timeline_path.resolve()), "timeline_sha256": digest(timeline_path),
              "ownership": str(ownership_path.resolve()), "ownership_sha256": digest(ownership_path),
              "source_time_base": "1/16000", "interval_convention": "0-based [start,end)",
              "timecode_policy": "exact timecodes derive from saved source PTS; nominal 24fps frame timecode is separately labeled",
              "count_policy": "Distinct known_issues entries counted once per cel; duplicate review/static notes and repeated exposures do not add issues. Mixed positive/limitation notes are not automatic rejection or confirmed final defects.",
              "summary": {"private_proposals": len(paths), "new_distinct_cels": len(records),
                          "owners": dict(Counter(r["owner"] for r in records)),
                          "distinct_cels_with_recorded_issue_entries": sum(bool(r["known_issues"]) for r in records),
                          "known_issue_entries_deduplicated_per_cel": sum(r["known_issue_entry_count"] for r in records),
                          "inherited_issue_groups": len(inherited), "automatic_rejections": 0,
                          "confirmed_oct7_final_composite_defects": None, "original_speed_review_performed": False},
              "proposal_provenance": provenance, "cel_reviews": records, "inherited_frozen_issues": inherited,
              "four_pixel_halo_experiment": {"historical_evidence": str(halo_path.resolve()),
                                             "full_record": halo_review["single_contrast_experiment"],
                                             "adopted_in_this_pass": False, "new_halo_tuning_performed": False},
              "historical_middle_review": {"path": str(middle_path.resolve()), "full_record": middle_review},
              "lessons": [
                  {"lesson": "A flawed adjacent Klee reference can overpower current source motion and propagate defects.",
                   "examples": [3364, 3369, 3403, 3405, 3437, 3443, 3448],
                   "application": "Current source plus actual native AB details remain pose/crop/expression/occlusion authority. Adjacent Klee is identity/style only; omit it or use a sound head-only crop when it carries unrelated defects. Do not rerun completed first-pass cels before full-film feedback."},
                  {"lesson": "Semantic family labels are not visual truth: feet_closeup at f3235 is actually a rear-head/raised-glove shot.",
                   "examples": [3235], "application": "Inspect actual original frame and current native evidence before choosing prompt or crop. Preserve frozen labels for provenance without inferring anatomy from them."},
                  {"lesson": "Expanding glyph halos did not solve same-color boot/clover camouflage.",
                   "application": "The existing single 4px trial remains rejected and unadopted. Retain the current frozen captions; defer any evidence-based clean lyric underlay or decoration repair to user-directed rework."}],
              "shared_artist_repairs_performed": False, "new_composite_review_performed": False,
              "original_speed_review_performed": False}
    destination = HERE / "deferred-art-review.json"
    if destination.exists():
        raise FileExistsError("Preserve prior private review report")
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(destination.resolve()), "sha256": digest(destination), **report["summary"]}))


if __name__ == "__main__":
    main()
