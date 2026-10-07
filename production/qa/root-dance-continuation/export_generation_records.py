"""Preserve the complete built-in prompt set and selected draft provenance."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    selections = json.loads((ROOT / "asset_selections.json").read_text(encoding="utf-8"))["selections"]
    jobs = []
    for path in sorted((ROOT / "jobs").glob("root-continuation-*.json")):
        job = json.loads(path.read_text(encoding="utf-8"))
        asset = ROOT / job["output"]
        if not asset.exists() or not job.get("prompt"):
            raise ValueError(f"Incomplete persisted generation job: {path}")
        preferred = next((row for row in selections if row["source_frame"] == job["source_frame"]), None)
        jobs.append({"job_file": str(path.resolve()), "full_job": job,
                     "asset_sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
                     "selected_draft": bool(preferred and preferred["path"] == job["output"]),
                     "artistic_accepted": False})
    report = {"tool": "builtin_imagegen", "files": len(jobs),
              "source_frames": sorted({row["full_job"]["source_frame"] for row in jobs}),
              "accepted": False, "actual_speed_artistic_review": "unperformed", "jobs": jobs}
    target = Path(__file__).resolve().parent / "generation-records.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"prompt_set": str(target), "files": len(jobs),
                      "distinct_source_cels": len(report["source_frames"])}))


if __name__ == "__main__":
    main()
