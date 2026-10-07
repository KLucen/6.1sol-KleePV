"""Factor only camera transforms that preserve source drawing shape at full resolution."""

import json
from functools import lru_cache
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT / ".python_deps"))
import cv2
import numpy as np
from analyze_source import foreground,signature,sheet,dump
from group_source import measure
from rigid_source import similarity


def full_character_mask(image,frame=None):
    mask=foreground(image)
    connected=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((7,7),np.uint8))
    _,labels,stats,_=cv2.connectedComponentsWithStats(connected,8)
    allowed=np.zeros_like(mask)
    if len(stats)<2:
        return allowed
    multiple=frame is not None and (888<=frame<=1006 or 2125<=frame<=2266 or 3360<=frame<=3430)
    floor=max(600,int(stats[1:,cv2.CC_STAT_AREA].max()*0.025))
    best=1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
    for index,(x,y,w,h,area) in enumerate(stats[1:],start=1):
        if (multiple and area>=floor) or (not multiple and index==best):
            allowed[labels==index]=1
    allowed=cv2.dilate(allowed,np.ones((7,7),np.uint8))
    return mask*allowed


@lru_cache(maxsize=24)
def decoded(reference):
    image=cv2.imread(str(ROOT/reference))
    frame=int(Path(reference).stem.rsplit("-f",1)[1])
    return image,full_character_mask(image,frame)


def hom(matrix):
    return np.vstack([np.array(matrix,dtype=np.float64),[0,0,1]])


def matches(metric,mask_a,mask_b):
    visible=max(int(mask_a.sum()),int(mask_b.sum()))
    coherent_floor=min(350,max(25,int(visible*0.0004)))
    largest_floor=min(120,max(15,int(visible*0.00015)))
    return metric["coherent"]<coherent_floor and metric["largest"]<largest_floor


def strict_proof(canonical,current,matrix):
    a,ma=decoded(canonical["reference"])
    b,mb=decoded(current["reference"])
    warped=cv2.warpAffine(a,np.array(matrix,dtype=np.float32),(1920,1080),borderValue=(237,135,148))
    wm=cv2.warpAffine(ma,np.array(matrix,dtype=np.float32),(1920,1080),flags=cv2.INTER_NEAREST)
    metric=measure(warped,b,wm,mb)
    return metric if matches(metric,wm,mb) else None


def main():
    data=json.loads((ROOT/"source_map.json").read_text(encoding="utf-8"))
    dump(ROOT/"source_map_translation_stage.json",data)
    original=data["cels"]
    canonical=[]
    history=[]
    signatures=[]
    remap={}
    evidence=[]
    for i,cel in enumerate(original):
        image,mask=decoded(cel["reference"])
        sig=signature(image,mask)
        match=None
        if signatures:
            errors=np.mean(np.abs(np.stack(signatures)-sig),axis=(1,2,3))
            nearby=np.flatnonzero(errors<12)
            nearby=nearby[np.argsort(errors[nearby])[:5]]
            for index in nearby:
                previous=history[index]
                a,ma=decoded(previous["reference"])
                direct=measure(a,image,ma,mask)
                if matches(direct,ma,mask):
                    rigid={"confirmed":True,"matrix":[[1,0,0],[0,1,0]],"metric":direct,"ecc":None,"direct_copy":True}
                else:
                    rigid=similarity(a,image,ma,mask)
                if rigid and rigid["confirmed"] and matches(rigid["metric"],ma,mask):
                    prev_mapping=remap[previous["cel"]]
                    matrix=(hom(rigid["matrix"])@hom(prev_mapping["matrix"]))[:2].tolist()
                    proof=strict_proof(canonical[prev_mapping["new_index"]],cel,matrix)
                    if proof:
                        match={"new_index":prev_mapping["new_index"],"matrix":matrix,"metric":proof,"local_metric":rigid["metric"],"ecc":rigid["ecc"],"kind":"confirmed_drawing_copy" if rigid.get("direct_copy") else "confirmed_original_camera_similarity"}
                        break
        if match is None:
            match={"new_index":len(canonical),"matrix":[[1,0,0],[0,1,0]],"kind":"identity"}
            canonical.append(cel.copy())
        remap[cel["cel"]]=match
        history.append(cel)
        signatures.append(sig)
        if match["kind"]!="identity":
            evidence.append({"old_cel":cel["cel"],"new_index":match["new_index"],"source_frame":cel["frame"],"proof":match})
        if i%25==0:
            print(f"camera refinement {i}/{len(original)}; {len(canonical)} canonical drawing candidates",flush=True)
            dump(ROOT/"source_camera_partial.json",{"processed_cels":i+1,"canonical_count":len(canonical),"canonical_cels":canonical,"remap":remap})
    for i,cel in enumerate(canonical):
        cel["prior_cel"]=cel["cel"]
        cel["cel"]=f"cel-{i:04d}"
    for candidate in data["candidates"]:
        mapping=remap[candidate["cel"]]
        matrix=(hom(candidate["source_transform"]["matrix"])@hom(mapping["matrix"]))[:2].tolist()
        candidate["prior_cel"]=candidate["cel"]
        candidate["cel"]=canonical[mapping["new_index"]]["cel"]
        candidate["source_transform"]={"kind": "identity" if np.allclose(matrix,[[1,0,0],[0,1,0]],atol=1e-10) else "verified_original_rigid_motion","matrix":matrix}
    by_id={c["id"]:c for c in data["candidates"]}
    data["frame_to_cel"]=[by_id[c]["cel"] for c in data["frame_to_candidate"]]
    data["frame_to_transform"]=[by_id[c]["source_transform"] for c in data["frame_to_candidate"]]
    exposures=[]
    for c in data["candidates"]:
        if exposures and exposures[-1]["cel"]==c["cel"] and exposures[-1]["source_transform"]==c["source_transform"]:
            exposures[-1]["end"]=c["end"]
            exposures[-1]["end_pts"]=c["end_pts"]
        else:
            exposures.append({k:c[k] for k in ("start","end","pts","end_pts","cel","family","source_transform")})
    data["source_exposures"]=exposures
    data["cels"]=canonical
    data["families"]={}
    for cel in canonical:
        data["families"].setdefault(cel["family"],[]).append(cel["cel"])
    data["deduplication"]["camera_similarity_evidence"]=evidence
    data["deduplication"]["camera_rule"]="Only isotropic scale, rigid rotation and translation; projected similarity must meet the same full-resolution coherent residual floor. No mesh, optical flow or morph."
    dump(ROOT/"source_map.json",data)
    for page,start in enumerate(range(0,len(canonical),48)):
        sheet(canonical[start:start+48],ROOT/"source_contacts"/f"canonical-{page:02d}.jpg")
    print(json.dumps({"before":len(original),"after":len(canonical),"proven_camera_reuses":len(evidence)}),flush=True)


if __name__=="__main__":
    main()
