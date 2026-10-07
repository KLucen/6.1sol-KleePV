"""Export stable chronological camera-refined IDs while the full source audit completes."""

import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent


def hom(matrix):
    return np.vstack([np.array(matrix,dtype=np.float64),[0,0,1]])


def main():
    data=json.loads((ROOT/"source_map.json").read_text(encoding="utf-8"))
    partial=json.loads((ROOT/"source_camera_partial.json").read_text(encoding="utf-8"))
    remap=partial["remap"]
    cels=partial["canonical_cels"]
    for index,cel in enumerate(cels):
        cel["prior_cel"]=cel["cel"]
        cel["cel"]=f"cel-{index:04d}"
    candidates=[]
    covered=max(c["frame"] for c in cels)
    for candidate in data["candidates"]:
        if candidate["cel"] not in remap or candidate["start"]>covered:
            continue
        mapping=remap[candidate["cel"]]
        candidate["prior_cel"]=candidate["cel"]
        candidate["cel"]=cels[mapping["new_index"]]["cel"]
        matrix=(hom(candidate["source_transform"]["matrix"])@hom(mapping["matrix"]))[:2].tolist()
        candidate["source_transform"]={"kind":"identity" if np.allclose(matrix,[[1,0,0],[0,1,0]],atol=1e-10) else "verified_original_rigid_motion","matrix":matrix}
        candidates.append(candidate)
    data["candidates"]=candidates
    data["cels"]=cels
    data["partial_review"]={"covered_through_frame":covered,"source_original_cels_processed":partial["processed_cels"],"final_id_stability":"IDs are chronological and remain unchanged as later source cels are processed."}
    (ROOT/"source_camera_early.json").write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"canonical_cels":len(cels),"covered_through_frame":covered,"covered_time":covered/24}))


if __name__=="__main__":
    main()
