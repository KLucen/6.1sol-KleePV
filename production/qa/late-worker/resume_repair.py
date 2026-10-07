"""Persist bounded late-owner repairs without editing shared selections."""

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("frame", type=int)
    parser.add_argument("variant")
    parser.add_argument("--instruction", default="")
    parser.add_argument("--source-first", action="store_true")
    parser.add_argument("--generator", type=Path)
    parser.add_argument("--notes", default="")
    parser.add_argument("--issue", action="append", default=[])
    args = parser.parse_args()
    path = ROOT / "jobs" / f"fine-f{args.frame:04d}-{args.variant}.json"
    if args.instruction:
        if path.exists():
            raise ValueError("Repair job already exists")
        base = json.loads((ROOT / "jobs" / f"fine-f{args.frame:04d}.json").read_text(encoding="utf-8"))
        target = str(ROOT / base["output"])
        base["prompt"] = args.instruction
        base["references"] = [
            {"path": target, "role": "edit_target_geometry_and_color_invariants"},
            base["references"][0],
            base["references"][1],
        ]
        if args.source_first:
            base["references"] = [base["references"][1], base["references"][2]]
        base["output"] = f"generated/fine-f{args.frame:04d}-{args.variant}.png"
        base["status"] = "prepared_targeted_repair"
        base["repair_of"] = target
        base["static_review"] = {"performed": False}
        base.pop("generator_output", None)
        path.write_text(json.dumps(base, indent=2), encoding="utf-8")
    job = json.loads(path.read_text(encoding="utf-8"))
    if args.generator:
        output = ROOT / job["output"]
        if output.exists():
            raise ValueError("Repair output already exists")
        shutil.copy2(args.generator, output)
        job["generator_output"] = str(args.generator)
        job["status"] = "generated_repair_draft"
    if args.notes or args.issue:
        job["static_review"] = {"performed": True, "pass": not args.issue,
                               "notes": [args.notes] if args.notes else [], "issues": args.issue,
                               "scope": "single-cel static comparison only"}
    job["accepted"] = False
    job["temporal_review"] = {"performed": False, "accepted": False}
    path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    if args.notes and (ROOT / job["output"]).exists():
        suggestions_path = Path(__file__).parent / "recovery-selected-suggestions.json"
        suggestions = json.loads(suggestions_path.read_text(encoding="utf-8"))
        record = {"source_frame": args.frame, "source_cel": job["source_cel"],
                  "path": job["output"], "source_reference": next(r["path"] for r in job["references"] if r["role"] == "current_source_pose_crop_and_occlusion"),
                  "job": str(path.relative_to(ROOT)), "review": job["static_review"],
                  "actual_speed_reviewed": False}
        suggestions["cels"] = [c for c in suggestions["cels"] if c["source_frame"] != args.frame] + [record]
        suggestions["cels"].sort(key=lambda c: c["source_frame"])
        suggestions_path.write_text(json.dumps(suggestions, indent=2), encoding="utf-8")
    print(json.dumps({"job": str(path), "status": job["status"], "output": job["output"]}))


if __name__ == "__main__":
    main()
