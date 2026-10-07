"""Independent shared-compositor oracle and immutable earlier-shot regression."""

import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT))
from compose import compose,read_image

PRIVATE=ROOT/"qa/star-caption-source-recovery-2026-10-05"
CYAN=ROOT/"qa/fast-fullpv-cyan-layers-2026-10-05"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bgr_sha(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def exposure(timeline,frame):
    span=next(row for row in timeline["output_exposures"] if row["start"]<=frame<row["end"])
    return span,timeline["assets"][span["cel"]]


def main():
    cv2.setNumThreads(2)
    OUT.mkdir(exist_ok=True)
    star_path=ROOT/"timeline-star-1008-1043-authorized-draft-v1.json"
    cyan_path=ROOT/"timeline-cyan-911-1008-fast-draft-v1.json"
    dance_path=ROOT/"timeline-dance-812-911-fast-draft-v11.json"
    raised_path=ROOT/"timeline-raised-1225-1285-fast-draft-v1.json"
    timelines={key:read_json(path) for key,path in (
        ("star",star_path),("cyan",cyan_path),("dance",dance_path),("raised",raised_path))}
    cyan_rows={row["source_frame"]:row for row in read_json(CYAN/"raw-final-batch-audit.json")["rows"]}
    frozen_rows={row["source_frame"]:row for row in read_json(CYAN/"frozen-after-hashes.json")["frames"]}
    assert len(cyan_rows)==97 and len(frozen_rows)==74
    scope={**{frame:"star" for frame in range(1008,1043)},
           **{frame:"cyan" for frame in cyan_rows},
           **{frame:"dance" if frame<911 else "raised" for frame in frozen_rows}}
    relevant=("compose.py","star_gestures_layers.py","star_caption_alternate.py",
              "cyan_profile_layers.py","cyan_caption_layers.py",
              "night_transition_layers.py","dance_caption_layers.py","raised_caption_layers.py",
              "layers/star-caption-f3402-authorized-v1.npz")
    code_before={name:sha(ROOT/name) for name in relevant}
    capture=cv2.VideoCapture(read_json(ROOT/"source_meta.json")["source"])
    cache={}
    rows=[]
    failed=[]
    for frame in range(max(scope)+1):
        ok,source=capture.read()
        if not ok:
            raise ValueError(f"Source decode stopped at {frame}")
        if frame not in scope:
            continue
        key=scope[frame]
        timeline=timelines[key]
        span,asset=exposure(timeline,frame)
        asset_path=ROOT/asset["path"]
        if asset["path"] not in cache:
            cache[asset["path"]]=(read_image(ROOT/asset["source_reference"]),read_image(asset_path))
        reference,generated=cache[asset["path"]]
        result,_,_=compose(source,reference,generated,span["source_matrix"],
                            asset["source_frame"],asset_path.name,frame)
        row={"frame":frame,"scope":key,"cel":span["cel"],"asset":asset["path"],
             "asset_sha256":sha(asset_path),"source_bgr_sha256":bgr_sha(source),
             "composite_bgr_sha256":bgr_sha(result)}
        if key=="star":
            oracle=cv2.imread(str(PRIVATE/f"f{frame:04d}-authorized-private-compose.png"))
            row["oracle_bgr_sha256"]=bgr_sha(oracle)
            row["changed_pixels_vs_private_oracle"]=int(np.any(result!=oracle,axis=2).sum())
            row["source_matches_private_actual"]=np.array_equal(
                source,cv2.imread(str(ROOT/f"qa/fast-fullpv-star-gestures-2026-10-04/actual-audit/actual-f{frame:04d}.png")))
            row["exact_pass"]=row["changed_pixels_vs_private_oracle"]==0 and row["source_matches_private_actual"]
            cv2.imwrite(str(OUT/f"f{frame:04d}-shared-raw.png"),result)
        elif key=="cyan":
            prior=cyan_rows[frame]
            row["exact_pass"]=all((row["asset_sha256"]==prior["asset_sha256"],
                                   row["composite_bgr_sha256"]==prior["composite_bgr_sha256"]))
        else:
            prior=frozen_rows[frame]
            row["exact_pass"]=all((asset["path"].replace("\\","/")==prior["asset"].replace("\\","/"),
                                   row["asset_sha256"]==prior["asset_sha256"],
                                   row["source_bgr_sha256"]==prior["source_bgr_sha256"],
                                   row["composite_bgr_sha256"]==prior["composite_bgr_sha256"]))
        rows.append(row)
        if not row["exact_pass"]:
            failed.append(row)
        if len(rows)%20==0:
            print(json.dumps({"processed":len(rows),"total":len(scope),"failed":len(failed)}),flush=True)
    capture.release()
    code_after={name:sha(ROOT/name) for name in relevant}
    report={"accepted":False,"stage":"shared_raw_regression_before_new_render",
            "star_private_oracle_frames":35,"cyan_frozen_frames":97,"earlier_frozen_frames":74,
            "total_frames":len(rows),"rows":rows,"failed":failed,
            "relevant_code_sha256_before":code_before,"relevant_code_sha256_after":code_after,
            "relevant_code_unchanged_during_audit":code_before==code_after,
            "timeline_sha256":{key:sha(path) for key,path in (
                ("star",star_path),("cyan",cyan_path),("dance",dance_path),("raised",raised_path))},
            "references_not_modified":{"cyan_raw_freeze":sha(CYAN/"raw-layer-freeze.json"),
                                        "cyan_raw_audit":sha(CYAN/"raw-final-batch-audit.json"),
                                        "old74_freeze":sha(CYAN/"frozen-after-hashes.json")},
            "all_raw_checks_pass":not failed and code_before==code_after,
            "actual_speed_or_artistic_acceptance":False}
    (OUT/"shared-35-cyan97-old74-regression.json").write_text(
        json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"total":len(rows),"passed":report["all_raw_checks_pass"],
                      "failures":len(failed),"code_unchanged":code_before==code_after}))
    if not report["all_raw_checks_pass"]:
        raise SystemExit(1)


if __name__=="__main__":
    main()
