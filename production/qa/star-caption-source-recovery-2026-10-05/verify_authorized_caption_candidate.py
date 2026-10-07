"""Freeze and review all 35 private frames of the authorized glyph candidate."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

import authorized_star_caption_candidate as layers

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
ACTUAL=ROOT/"qa/fast-fullpv-star-gestures-2026-10-04/actual-audit"
PRIOR=ROOT/"qa/star-gestures-layers-2026-10-05"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_bgr(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def pages(images,labels,prefix,rows=7):
    files=[]
    for start in range(0,len(images),rows):
        group=images[start:start+rows]
        row_height=group[0].shape[0]+24
        canvas=np.full((len(group)*row_height,group[0].shape[1],3),32,np.uint8)
        for i,image in enumerate(group):
            cv2.putText(canvas,labels[start+i],(8,i*row_height+17),
                        cv2.FONT_HERSHEY_SIMPLEX,.45,(255,255,255),1,cv2.LINE_AA)
            canvas[i*row_height+24:(i+1)*row_height]=image
        file=OUT/f"{prefix}-page-{start//rows+1:02d}.png"
        cv2.imwrite(str(file),canvas)
        files.append(str(file.relative_to(ROOT)))
    return files


def main():
    cv2.setNumThreads(2)
    names={frame:name for name,(start,end) in layers.REGISTERED.items()
           for frame in range(start,end)}
    canonical={start for start,end in layers.REGISTERED.values()}
    generated_cache={}
    rows=[]
    captions=[]
    bodies=[]
    caption_labels=[]
    body_labels=[]
    shared_paths=[ROOT/"compose.py",ROOT/"star_gestures_layers.py",
                  ROOT/"asset_selections.json",ROOT/"source_aliases.json"]
    shared_before={str(path):sha(path) for path in shared_paths}
    for frame in range(1008,1043):
        name=names[frame]
        source_path=ACTUAL/f"actual-f{frame:04d}.png"
        source=cv2.imread(str(source_path))
        asset=ROOT/"generated"/name
        if name not in generated_cache:
            generated=cv2.resize(cv2.imread(str(asset)),(1920,1080),
                                 interpolation=cv2.INTER_LANCZOS4)
            own=layers.star_subject_mask(generated,frame,name)
            generated_cache[name]=generated,own
        generated,new=generated_cache[name]
        old=layers.star_subject_mask(source,frame,name,source=True)
        result,repair=layers.restore_star_gestures(source.copy(),source,generated,
                                                  old,new,frame,name)
        body_before=result.copy()
        result,lyric=layers.restore_star_captions(result,source,frame,name,new)
        support=(repair|lyric)!=0
        outside_changed=int(np.count_nonzero(np.any(result!=source,axis=2)&~support))
        layer=layers.caption_layer(layers._phase(frame))
        x0,y0,x1,y1=layer["region"]
        core_changed=int(np.count_nonzero(
            np.any(result[y0:y1,x0:x1]!=source[y0:y1,x0:x1],axis=2)&layer["core"]))
        assert outside_changed==0,(frame,"outside source ownership",outside_changed)
        assert core_changed==0,(frame,"retained source core",core_changed)
        prior=cv2.imread(str(PRIOR/f"f{frame:04d}-private-compose.png"))
        prior_equal=np.array_equal(prior,result)
        if frame<1037:
            assert prior_equal,(frame,"prior caption phase must be unchanged")
        body_outside_lyric=int(np.count_nonzero(
            np.any(result!=body_before,axis=2)&(lyric==0)))
        assert body_outside_lyric==0
        result_path=OUT/f"f{frame:04d}-authorized-private-compose.png"
        cv2.imwrite(str(result_path),result)
        native=np.concatenate((source[950:1055,610:1310],result[950:1055,610:1310]),axis=1)
        cv2.imwrite(str(OUT/f"f{frame:04d}-authorized-native-caption-pair.png"),native)
        captions.append(native)
        caption_labels.append(f"f{frame} SOURCE | AUTHORIZED REAL GLYPH ALTERNATE / UNACCEPTED")
        if frame in canonical:
            body=np.concatenate([cv2.resize(image,(640,360),interpolation=cv2.INTER_AREA)
                                 for image in (source,generated,result)],axis=1)
            bodies.append(body)
            body_labels.append(f"f{frame} SOURCE | SELECTED RAW PNG | PRIVATE LAYERS / UNACCEPTED")
        rows.append({"frame":frame,"asset":name,"asset_sha256":sha(asset),
                     "source_path":str(source_path.relative_to(ROOT)),
                     "source_sha256":sha(source_path),
                     "result_sha256":sha(result_path),"result_bgr_sha256":digest_bgr(result),
                     "outside_ownership_changed":outside_changed,
                     "retained_source_core_changed":core_changed,
                     "character_outside_caption_changed":body_outside_lyric,
                     "prior_phase_byte_equivalent_bgr":prior_equal,
                     "real_glyph_alternate_applied":frame>=1037})
    shared_after={str(path):sha(path) for path in shared_paths}
    assert shared_before==shared_after
    report={"accepted":False,"source_interval":[1008,1043],"frames":35,
            "registered_cels":16,"authorized_alternate_interval":[1037,1043],
            "source_timing_modified":False,"shared_files_modified":False,
            "shared_sha256":shared_after,"rows":rows,
            "pages":{"native_captions":pages(captions,caption_labels,"authorized-native-caption"),
                     "canonical_bodies":pages(bodies,body_labels,"authorized-canonical-body",4)},
            "gate":{"technical_private_checks_pass":True,
                    "actual_speed_review_performed":False,
                    "encoded_review_performed":False,
                    "static_native_review":"pending human/model viewing after this script"},
            "provenance":"authorized-alternate-glyph-provenance.json",
            "limitations":"Real f3402 handwriting replaces unobservable f1037 Japanese strokes with human authorization. Alpha/AA and target palette are reconstructed; not original pixel recovery or artistic acceptance."}
    (OUT/"authorized-private-35frame-report.json").write_text(
        json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"frames":35,"cels":16,"outside_pass":True,
                      "retained_source_cores_pass":True,"previous29_bgr_unchanged":True,
                      "report":str(OUT/"authorized-private-35frame-report.json")}))


if __name__=="__main__":
    main()
