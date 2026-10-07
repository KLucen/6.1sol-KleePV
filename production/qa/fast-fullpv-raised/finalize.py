"""Archive private jobs and static suggestions, with source/artwork comparisons."""

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TOOL_ROOT = Path(r"C:\Users\KLucen\.codex\generated_images\01a104e3-14b6-7e82-a5e5-9711b4483037")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    raw = json.loads((HERE / "static-reviews-input.json").read_text(encoding="utf-8"))
    plan = json.loads((HERE / "source-plan.json").read_text(encoding="utf-8"))
    rows = []
    records = []
    for name, (tool_file, seconds) in raw["tool_outputs"].items():
        path = ROOT / "jobs" / (name + ".json")
        job = json.loads(path.read_text(encoding="utf-8"))
        asset = ROOT / job["intended_output"]
        if not asset.is_file():
            raise ValueError(f"Missing workspace copy: {asset}")
        with Image.open(asset) as im:
            canvas = list(im.size)
            if abs(im.width / im.height - 1920 / 1080) > 0.02:
                raise ValueError(f"Wrong asset aspect: {asset}: {im.size}")
        selected = raw["selected_jobs"].get(str(job["source_frame"])) == name
        review = raw["static_reviews"][str(job["source_frame"])] if selected else {
            "result": "Superseded after confirmed original long peach-pink armpit hair residue",
            "blocking_confirmed": ["Old pink hair tips remain at both armpits"],
            "issues": ["Do not use as identity or replacement anchor"]}
        job.update(status="generated_draft_unaccepted" if selected else "generated_blocked_superseded",
                   accepted=False, selected_draft_proposed=selected, static_review=review,
                   tool_output_path=str(TOOL_ROOT / tool_file), observed_call_seconds=seconds,
                   output_sha256=sha(asset), output_canvas=canvas,
                   canvas_note="Native tool output retained; compositor normalizes to source 1920x1080 canvas",
                   reference_sha256={p: sha(Path(p)) for p in job["referenced_image_paths"]})
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        records.append({"job_path": path.relative_to(ROOT).as_posix(), "job_sha256": sha(path), **job})
        if selected:
            rows.append({"source_frame": job["source_frame"], "cel": job["cel"],
                         "path": job["intended_output"], "accepted": False,
                         "output_sha256": sha(asset), "review": review,
                         "known_issues": review["issues"],
                         "consecutive_review": "Private static sequence pending composite/speed review",
                         "static_contact_path": "qa/fast-fullpv-raised/sequence-contact-page-01.jpg"})
    rows.sort(key=lambda x: x["source_frame"])
    ordered_pairs = []
    for cel in plan["cels"]:
        frame = cel["source_frame"]
        row = next((x for x in rows if x["source_frame"] == frame), None)
        asset = ROOT / (row["path"] if row else cel["existing_asset"]["path"])
        source = Path(cel["source_reference"])
        pair = Image.new("RGB", (3840, 1080))
        pair.paste(Image.open(source).convert("RGB"), (0, 0))
        pair.paste(Image.open(asset).convert("RGB").resize((1920, 1080)), (1920, 0))
        native = HERE / f"f{frame:04d}-source-art-native.png"
        pair.save(native)
        ordered_pairs.append((frame, pair))
    for offset in range(0, len(ordered_pairs), 8):
        chunk = ordered_pairs[offset:offset + 8]
        page = Image.new("RGB", (1920, 4 * 306), "#202024")
        draw = ImageDraw.Draw(page)
        for i, (frame, pair) in enumerate(chunk):
            x, y = (i % 2) * 960, (i // 2) * 306
            draw.text((x + 12, y + 8), f"f{frame:04d} SOURCE | KLEE ART DRAFT (NOT COMPOSITE)", fill="white")
            thumb = pair.resize((960, 270))
            page.paste(thumb, (x, y + 30))
        page.save(HERE / f"sequence-contact-page-{offset // 8 + 1:02d}.jpg")
    (HERE / "proposals.json").write_text(json.dumps({
        "owner": raw["owner"], "accepted": False, "mode": "strict_source",
        "source_interval": raw["source_interval"], "review_scope": raw["review_scope"],
        "selections": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "generation-records.json").write_text(json.dumps({
        "owner": raw["owner"], "accepted": False, "tool_mode": "builtin_image_gen",
        "independent_new_cels": 11, "repair_calls": 1,
        "all_workspace_copies_verified": True, "records": records},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"new_proposed_cels": len(rows), "calls": len(records),
                      "proposed_frames": [x["source_frame"] for x in rows], "accepted": False}))


if __name__ == "__main__":
    main()
