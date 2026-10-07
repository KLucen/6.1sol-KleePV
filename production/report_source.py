"""Validate the source exposure coverage and summarize analysis limits."""

import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def dump(path, obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")


def main():
    data = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    probe = subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",data["source"]],capture_output=True,check=True)
    all_streams = json.loads(probe.stdout)
    meta["streams"] = all_streams["streams"]
    meta["format"] = all_streams["format"]
    dump(ROOT / "source_meta.json",meta)
    errors=[]
    expected=0
    for exposure in data["source_exposures"]:
        if exposure["start"] != expected:
            errors.append(f"coverage gap or overlap at {expected}")
        expected=exposure["end"]
    if expected != data["frames"]:
        errors.append("exposure coverage does not reach final frame")
    if len(data["frame_to_cel"]) != data["frames"]:
        errors.append("frame-to-cel length differs from decoded source count")
    family_counts = {}
    for family in sorted({c["family"] for c in data["candidates"]}):
        cs=[c for c in data["candidates"] if c["family"] == family]
        family_counts[family]={"cels":len({c["cel"] for c in cs}),"candidates":len(cs),"first_frame":min(c["start"] for c in cs),"last_end_frame":max(c["end"] for c in cs)}
    report={"source_frames":data["frames"],"actual_pts_count":len(meta["pts"]),"raw_candidates":len(data["candidates"]),"independent_cel_candidates":len(data["cels"]),"source_exposures_with_motion":len(data["source_exposures"]),"merge_types":dict(Counter(c["review"] for c in data["candidates"])),"families":family_counts,"coverage_errors":errors,"review_limits":["Every source frame was decoded. Numerical candidates were visually inspected as full-frame contact sheets; numerical equivalence is not complete art approval.","Small coherent RGB/outline/eye/hand differences above the calibrated codec floor are retained.","Repeated drawings may have confirmed source rigid layer/camera motion. Their matrix is source evidence, not non-rigid character interpolation.","Family boundaries are semantic labels and can straddle transitional composite shots.","Moving source stars and subtitles are excluded from drawing equivalence and must be preserved per source frame when compositing.","These analysis masks are not production character mattes: pale costume/skin/props can share the ignored source effects palette.","Two-character composite source frames are retained conservatively when their characters move separately; a whole-frame rigid match cannot prove independent layer identity.","Cyan inserts and source zooms include fine changes that need adjacent-frame review at full resolution.","Do not equate the number of source drawing candidates with the number of artist-approved replacement drawings."]}
    dump(ROOT / "source_analysis_report.json",report)
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
