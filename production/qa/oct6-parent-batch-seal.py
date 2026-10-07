"""Seal completed builtin outputs without inventing unfinished queue results."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main(directory):
    here = ROOT / "qa" / directory
    destination = here / "full-builtin-promptset-and-integrity.json"
    if destination.exists():
        raise FileExistsError("Retain prior sealed archive")
    jobs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(here.glob("job-f*-v*.json"))]
    proposal = json.loads((here / "draft-proposal.json").read_text(encoding="utf-8"))
    queue_path = here / "missing-source-reference-queue.json"
    if not queue_path.exists():
        queue_path = here / "source-evidence-queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))["queue"]
    selected = {row["path"] for row in proposal["selections"]}
    checks = []
    for job in jobs:
        output, origin = ROOT / job["output"], Path(job["tool_output"])
        checks.append({"source_frame": job["source_frame"], "output": job["output"],
                       "sha256": digest(output), "recorded_sha_exact": digest(output) == job["output_sha256"],
                       "builtin_origin_byte_exact": output.read_bytes() == origin.read_bytes(),
                       "dimensions": list(Image.open(output).size), "selected_private": job["output"] in selected,
                       "accepted": job["accepted"],
                       "references": [{"path": ref["path"], "role": ref["role"],
                                       "actually_viewed": ref.get("actually_viewed"),
                                       "sha256_at_archive": digest(Path(ref["path"]))}
                                      for ref in job["reference_roles"]]})
    assert all(c["recorded_sha_exact"] and c["builtin_origin_byte_exact"] and not c["accepted"] for c in checks)
    frames = {row["source_frame"] for row in proposal["selections"]}
    coverage = sum(e["end"] - e["start"] for row in queue if row["source_frame"] in frames
                   for e in row["source_exposures"])
    report = {"snapshot_utc": datetime.now(timezone.utc).isoformat(), "tool": "builtin_imagegen",
              "jobs": jobs, "integrity": checks, "successful_builtin_outputs": len(jobs),
              "requested_queue_cels": len(queue), "unique_generated_source_cels": len({j["source_frame"] for j in jobs}),
              "private_selected_drafts": len(selected), "source_exposure_frames_of_private_drafts": coverage,
              "requested_but_ungenerated_frames": [r["source_frame"] for r in queue if r["source_frame"] not in frames],
              "argument_validation_attempts_with_no_generated_output": 0, "accepted": False,
              "shared_selection_edited_at_seal": False, "temporal_speed_review": "not_performed",
              "art_acceptance": "Not performed; static drafts only"}
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"archive": str(destination), "sha256": digest(destination), "outputs": len(jobs),
                      "drafts": len(selected), "source_frames": coverage, "technical_assets_ok": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    main(parser.parse_args().directory)
