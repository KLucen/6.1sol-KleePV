"""Map existing scene anchors to exact retained cels and enumerate missing drawings."""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--map",type=Path,default=ROOT/"source_map.json")
    parser.add_argument("--output",type=Path,default=ROOT/"generation_jobs.json")
    args=parser.parse_args()
    data=json.loads(args.map.read_text(encoding="utf-8"))
    source_candidates=data["candidates"]
    old=json.loads((ROOT.parent/"analysis"/"scene_candidates.json").read_text(encoding="utf-8"))
    anchors=[]
    anchor_cels=set()
    generated_cels=set()
    generated_mappings=[]
    for row in old:
        frame=round(row["time"]*24)
        candidate=next((c for c in source_candidates if c["start"]<=frame<c["end"]),None)
        if candidate is None:
            continue
        n=row["candidate_index"]+1
        matrix=candidate["source_transform"]["matrix"]
        generated=ROOT/"generated"/f"candidate-{n:03d}.png"
        generated_exists=generated.exists()
        anchors.append({"old_id":f"{n:03d}","old_source_reference":f"../analysis/source_cels/source-cel-{n:03d}.jpg","old_source_frame":frame,"actual_pts":candidate["pts"],"canonical_cel":candidate["cel"],"source_candidate":candidate["id"],"canonical_to_anchor_matrix":matrix,"generated_asset_exists":generated_exists,"generated_asset":str(generated.relative_to(ROOT)).replace("\\","/") if generated_exists else None,"anchor_to_canonical_note":"Use inverse of this rigid matrix if anchoring generated art into canonical source canvas."})
        anchor_cels.add(candidate["cel"])
        if generated_exists:
            generated_cels.add(candidate["cel"])
            generated_mappings.append({"cel":candidate["cel"],"source_frame":frame,"asset":str(generated.relative_to(ROOT)).replace("\\","/"),"canonical_to_asset_matrix":matrix})
    for asset in (ROOT/"generated").glob("*.png"):
        match=re.fullmatch(r"(?:fine|opening)-f(\d+)\.png",asset.name)
        if not match:
            continue
        frame=int(match.group(1))
        candidate=next((c for c in source_candidates if c["start"]<=frame<c["end"]),None)
        if candidate:
            generated_cels.add(candidate["cel"])
            generated_mappings.append({"cel":candidate["cel"],"source_frame":frame,"asset":str(asset.relative_to(ROOT)).replace("\\","/"),"canonical_to_asset_matrix":candidate["source_transform"]["matrix"]})
    grouped=defaultdict(list)
    jobs=[]
    last_by_family={}
    for cel in data["cels"]:
        previous=last_by_family.get(cel["family"])
        last_by_family[cel["family"]]=cel
        if cel["cel"] in anchor_cels or cel["cel"] in generated_cels:
            continue
        blank=cel["family"]=="blank_transition" or cel.get("character_bbox")==[0,0,0,0]
        job={"job_id":cel["cel"],"source_frame":cel["frame"],"actual_pts":cel["pts"],"source_reference":cel["reference"],"source_candidate":cel["id"],"family":cel["family"],"previous_cel":previous["cel"] if previous else None,"previous_source_reference":previous["reference"] if previous else None,"previous_source_frame":previous["frame"] if previous else None,"needs_character_generation":not blank,"status":"missing_independent_source_cel","generation_instruction":"Use this exact source frame for camera/crop/pose/eyes/hands/occlusion. Compare previous source reference at full resolution; redraw genuine source local contour differences and keep character identity/style from approved Klee neighbor. Source rigid motion is recorded separately and is not a substitute for new local drawings."}
        jobs.append(job)
        grouped[cel["family"]].append(job)
    all_missing=[c["cel"] for c in data["cels"] if c["cel"] not in generated_cels]
    result={"version":1,"source_map":str(args.map),"source_frames":data["frames"],"canonical_cels":len(data["cels"]),"existing_scene_anchor_plan":len(anchors),"anchor_plan_covered_cels":len(anchor_cels),"currently_generated_cels":len(generated_cels),"currently_ungenerated_cels":len(all_missing),"missing_extra_cels_beyond_anchor_plan":len(jobs),"missing_extra_character_generation_cels":sum(j["needs_character_generation"] for j in jobs),"old_anchor_to_cel":anchors,"existing_generated_to_cel":generated_mappings,"all_currently_ungenerated_cel_ids":all_missing,"jobs":jobs,"family_jobs":dict(grouped)}
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("old_anchor_to_cel","existing_generated_to_cel","all_currently_ungenerated_cel_ids","jobs","family_jobs")},indent=2))


if __name__=="__main__":
    main()
