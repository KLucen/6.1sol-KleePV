"""Archive this bounded generation batch without promoting drafts to acceptance."""

from hashlib import sha256
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def hash_file(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    jobs = sorted([*(ROOT / "jobs").glob("fast-fullpv-dance-*.json"),
                   *(ROOT / "jobs").glob("fast-fullpv-cyan-*.json")])
    selected = {row["source_frame"]: row["path"].replace("\\", "/")
                for row in json.loads((ROOT / "asset_selections.json").read_text(encoding="utf-8"))["selections"]
                if row.get("path")}
    records = []
    for job_path in jobs:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        image_path = ROOT / job["output"]
        if not image_path.exists() or not job.get("prompt"):
            raise ValueError(f"Incomplete project generation record: {job_path}")
        refs = [{"path": path, "role": role, "sha256": hash_file(Path(path))}
                for path, role in zip(job["references"], job["reference_roles"])]
        if len(refs) != len(job["references"]):
            raise ValueError(f"Missing reference role: {job_path}")
        with Image.open(image_path) as image:
            native_dimensions = list(image.size)
        records.append({**job, "job_path": str(job_path), "job_sha256": hash_file(job_path),
                        "output_sha256": hash_file(image_path), "native_dimensions": native_dimensions,
                        "reference_records": refs,
                        "currently_selected_draft": selected.get(job["source_frame"]) == job["output"],
                        "artistic_accepted": False})
    raised = ROOT / "qa/fast-fullpv-raised/generation-records.json"
    target = ROOT / "qa/fast-fullpv-batch-2026-10-04-generation-records.json"
    dance = [row for row in records if row["job_id"].startswith("fast-fullpv-dance-")]
    cyan = [row for row in records if row["job_id"].startswith("fast-fullpv-cyan-")]
    target.write_text(json.dumps({"tool_mode": "builtin_imagegen", "root_calls": len(records),
        "root_dance_calls": len(dance), "root_cyan_calls": len(cyan),
        "new_missing_cels": 24, "new_missing_source_frames": [887, 889, 903, 907, 908, 909,
            938, 942, 948, 954, 957, 960, 963, 1225, 1229, 1234, 1241, 1248, 1256, 1264, 1267, 1274, 1278, 1282],
        "root_already_mapped_repair_cels": [891, 894, 897, 900],
        "unselected_repair_baselines_retained": True, "root_dance_records": dance,
        "root_cyan_records": cyan,
        "raised_records": {"path": str(raised), "sha256": hash_file(raised)},
        "canvas_note": "Native near-16:9 tool outputs are preserved; existing compositor normalizes to source canvas.",
        "artistic_acceptance": False}, indent=2), encoding="utf-8")
    print(json.dumps({"record": str(target), "root_calls": len(records), "root_selected_drafts":
        sum(row["currently_selected_draft"] for row in records), "sha256": hash_file(target)}))


if __name__ == "__main__":
    main()
