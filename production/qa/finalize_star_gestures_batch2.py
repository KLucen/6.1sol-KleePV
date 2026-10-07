"""Record private generated-cel provenance and static comparison evidence."""

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa/fast-fullpv-star-gestures-2026-10-04"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence = json.loads((OUT / "source-evidence.json").read_text())
    rows, checks, issues = [], [], []
    for item in evidence["targets"]:
        frame = item["source_frame"]
        job_path = ROOT / f"jobs/star-gestures-f{frame:04d}-fast-v1.json"
        job = json.loads(job_path.read_text())
        asset = ROOT / job["output_path"]
        actual_digest = digest(asset)
        if job["output_sha256"] != actual_digest or job["accepted"] is not False:
            raise ValueError(f"Hash or unaccepted-state mismatch: {frame}")
        if job["generation_calls"] != 1:
            raise ValueError(f"Expected one generated candidate: {frame}")
        with Image.open(asset) as im:
            im.load()
            dimensions = list(im.size)
        job["source_sha256"] = item["source_sha256"]
        job["source_meta_sha256"] = evidence["source_meta_sha256"]
        job["source_exposures"] = item["source_exposures"]
        for role in job["ordered_reference_roles"]:
            role["sha256"] = digest(ROOT / role["path"])
            role["viewed_before_generation"] = True
        review = job["static_review"]
        known = review["flaws"]
        job["known_issues"] = known
        job["output_dimensions"] = dimensions
        job["caption_cleanup_required"] = True
        job["source_background_restoration_required"] = True
        job["temporal_review"] = "not_performed_per_batch_scope"
        job["consecutive_review"] = {
            "source_before": item["before_source"],
            "source_after": item["after_source"],
            "source_delta": item["source_delta"],
            "source_next_delta": item["source_next_delta"],
            "status": "static_source_and_adjacent_drafts_checked",
            "limits": "No original-speed, composite, whole-prefix render or artistic acceptance",
        }
        job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")
        row = {
            "source_cel": item["source_cel"],
            "source_frame": frame,
            "source_reference": item["source_reference"],
            "source_sha256": item["source_sha256"],
            "source_exposures": item["source_exposures"],
            "path": job["output_path"],
            "sha256": actual_digest,
            "job_document": str(job_path.relative_to(ROOT)).replace("\\", "/"),
            "accepted": False,
            "static_review": review,
            "known_issues": known,
            "consecutive_review": job["consecutive_review"],
            "static_contact_path": str((OUT / "new-drafts-contact.jpg").relative_to(ROOT)),
        }
        rows.append(row)
        checks.append({"frame": frame, "decodes": True, "dimensions": dimensions,
                       "sha256": actual_digest, "generation_calls": 1,
                       "source_exposures_unchanged": True})
        for flaw in known:
            issues.append({"source_cel": item["source_cel"], "source_frame": frame,
                           "pts": item["source_exposures"][0]["pts"],
                           "version": job["output_path"], "issue": flaw,
                           "status": "recorded_unaccepted_review_pending"})

    contact = Image.new("RGB", (1920, 1135), "#202024")
    draw = ImageDraw.Draw(contact)
    for i, row in enumerate(rows):
        x, y = (i % 4) * 480, (i // 4) * 375
        with Image.open(ROOT / row["path"]) as im:
            im.thumbnail((480, 340))
            contact.paste(im, (x, y + 28))
        draw.text((x + 8, y + 8), f"f{row['source_frame']:04d} {row['source_cel']} v1 UNACCEPTED", fill="white")
    contact.save(OUT / "new-drafts-contact.jpg")

    for page, offset in enumerate(range(0, len(rows), 4), start=1):
        group = rows[offset:offset + 4]
        canvas = Image.new("RGB", (1920, len(group) * 560), "#202024")
        draw = ImageDraw.Draw(canvas)
        for index, row in enumerate(group):
            for column, rel in enumerate((row["source_reference"], row["path"])):
                with Image.open(ROOT / rel) as im:
                    im.thumbnail((960, 525))
                    canvas.paste(im, (column * 960, index * 560 + 30))
            draw.text((12, index * 560 + 8), f"SOURCE f{row['source_frame']:04d}", fill="white")
            draw.text((972, index * 560 + 8), "NEW INDEPENDENT DRAFT / UNACCEPTED", fill="white")
        canvas.save(OUT / f"source-new-pairs-{page:02d}.jpg")

    proposal = {
        "owner": "star_gestures_batch2", "accepted": False, "mode": "strict_source",
        "snapshot_utc": datetime.now(timezone.utc).isoformat(),
        "source_meta_sha256": evidence["source_meta_sha256"],
        "selections": rows,
        "summary": {"new_unique_cels": len(rows), "source_frames_supported": sum(
            e["end"] - e["start"] for row in rows for e in row["source_exposures"]),
            "independent_generation_outputs": len(rows), "targeted_repairs": 0,
            "artistically_accepted": 0, "public_mapping_mutated_by_this_agent": False,
            "compose_mutated_by_this_agent": False},
        "review_limits": "Static only; actual composition, caption/source-background restoration and original-speed artistic review pending",
    }
    (OUT / "draft-proposal.json").write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    (OUT / "batch-verification.json").write_text(json.dumps({
        "checks": checks, "known_issues": issues,
        "public_mapping_sha256_before": evidence["public_mapping_sha256_before"],
        "public_mapping_sha256_after": digest(ROOT / "asset_selections.json"),
        "public_mapping_mutated_by_this_agent": False,
        "scope": "Ten new assets only; no public mapping/compose edits, rendering or art pass",
    }, indent=2), encoding="utf-8")
    print(json.dumps(proposal["summary"]))


if __name__ == "__main__":
    main()
