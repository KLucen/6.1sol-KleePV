"""Seal seven appended builtin outputs and contact evidence, not acceptance."""
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa/standing-missing-2026-10-05"
FRAMES = [1043, 1048, 1053, 1059, 1064, 1069]
JOBS = [ROOT / "jobs/star-f1017-rear-hair-repair-2026-10-05.json"] + [
    ROOT / f"jobs/standing-f{frame}-fast-2026-10-05-v1.json" for frame in FRAMES]


def metadata(path):
    with Image.open(path) as image:
        size = list(image.size)
    return {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest(), "dimensions": size}


def main():
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    cels = {row["canonical_source_frame"]: row for row in manifest["cels"]}
    records = []
    for path in JOBS:
        job = json.loads(path.read_text(encoding="utf-8"))
        frame = job["source_frame"]
        asset = ROOT / job["output"]
        output, origin = metadata(asset), metadata(Path(job["tool_output_path"]))
        if output["sha256"] != origin["sha256"] or output["sha256"] != job["output_sha256"]:
            raise ValueError(f"Generated origin/hash mismatch f{frame}")
        if output["dimensions"] != job["output_dimensions"]:
            raise ValueError(f"Recorded dimensions mismatch f{frame}")
        if job["accepted"] is not False or cels[frame]["selected_asset"]["path"].replace("\\", "/") != job["output"]:
            raise ValueError(f"Selection or acceptance mismatch f{frame}")
        refs = [dict(role=ref["role"], **metadata(Path(ref["path"]))) for ref in job["reference_roles"]]
        records.append({"job_path": str(path.relative_to(ROOT)), "job_sha256": sha256(path.read_bytes()).hexdigest(),
                        "complete_original_job": job, "references_in_original_order": refs,
                        "output": output, "tool_origin": origin,
                        "actual_cel": cels[frame]["cel"], "actual_source_reference": cels[frame]["source_reference"],
                        "actual_source_exposures": cels[frame]["source_exposures"],
                        "selected_as_unaccepted_draft": True})
    archive = OUT / "oct5-full-7call-promptset.json"
    if archive.exists():
        raise ValueError("Refuse overwriting sealed generation appendix")
    archive.write_text(json.dumps({"mode": "builtin_imagegen", "date": "2026-10-05",
        "recorded_calls": 7, "new_previously_missing_cels": 6, "mapped_blocker_repairs": 1,
        "exposures_changed": False, "aliases_created": False, "accepted": False,
        "original_speed_review": "not_performed", "records": records}, indent=2), encoding="utf-8")
    for page in range(2):
        canvas = Image.new("RGB", (1280, 1155), "#242428")
        draw = ImageDraw.Draw(canvas)
        for index, frame in enumerate(FRAMES[page * 3:page * 3 + 3]):
            y = index * 385
            draw.text((8, y + 5), f"f{frame} actual source | generated draft (reduced, not native)", fill="white")
            for col, path in enumerate((ROOT / cels[frame]["source_reference"], ROOT / cels[frame]["selected_asset"]["path"])):
                with Image.open(path) as im:
                    im = im.convert("RGB").resize((640, 360), Image.Resampling.LANCZOS)
                    canvas.paste(im, (col * 640, y + 25))
        canvas.save(OUT / f"source-generated-consecutive-page-{page + 1:02d}.png")
    print(json.dumps({"archive": str(archive), "sha256": sha256(archive.read_bytes()).hexdigest(),
                      "records": len(records), "artistic_acceptance": False}))


if __name__ == "__main__":
    main()
