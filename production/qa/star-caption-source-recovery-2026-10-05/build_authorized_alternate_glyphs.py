"""Extract one real, fully visible original Japanese word phase without art."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
SOURCE=ROOT/"source_refs/src-1905-f3402.png"
DONOR_REGION=(688,954,1225,992)
DESTINATION_REGION=(676,954,1213,992)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source=cv2.imread(str(SOURCE))
    decoded=cv2.imread(str(OUT/"caption-all-f3402-native.png"))
    assert np.array_equal(source[945:1047,350:1570],decoded)
    x0,y0,x1,y1=DONOR_REGION
    observed=source[y0:y1,x0:x1].astype(np.float32)
    b,g,r=cv2.split(observed)
    seeds=(b>=198)&(g>=216)&(r>=232)&(r>b+8)&(g>b+5)
    assert np.count_nonzero(seeds)>1000
    candidate=((g>=198)&(b>=177)&(r>=225)).astype(np.uint8)
    support=cv2.dilate(candidate,np.ones((5,5),np.uint8))!=0
    support[:3]=False
    support[-1:]=False
    yy,xx=np.indices(seeds.shape,dtype=np.float32)
    design=np.stack((np.ones_like(xx),xx,yy),axis=2)
    background=~cv2.dilate(candidate,np.ones((7,7),np.uint8)).astype(bool)
    coefficients=np.linalg.lstsq(design[background],observed[background],rcond=None)[0]
    plate=design@coefficients
    foreground=np.median(observed[g>=np.percentile(g,99.5)],axis=0).astype(np.float32)
    direction=foreground-plate
    alpha=np.clip(np.sum((observed-plate)*direction,axis=2)/
                  np.maximum(np.sum(direction*direction,axis=2),1),0,1)
    residual=np.max(np.abs(observed-(plate+alpha[...,None]*direction)),axis=2)
    alpha[~support|(alpha<.045)|(residual>10)]=0
    core=(alpha>.9)&seeds
    reconstructed=alpha[...,None]*foreground+(1-alpha[...,None])*plate
    errors=np.abs(reconstructed-observed)
    visible=alpha>.1
    ring=(cv2.dilate(visible.astype(np.uint8),np.ones((3,3),np.uint8))!=0)&~visible
    target_source=cv2.imread(str(ROOT/"source_refs/src-0569-f1037.png"))
    target_probe=target_source[959:989,686:806].astype(np.float32)
    tb,tg,tr=cv2.split(target_probe)
    target_core=(tb>=198)&(tg>=216)&(tr>=232)&(tr>tb+8)&(tg>tb+5)
    target_foreground=np.median(target_probe[target_core],axis=0)
    ink_rgb=np.broadcast_to(target_foreground,observed.shape).copy()
    np.savez_compressed(OUT/"authorized-alternate-japanese-f3402.npz",
                        alpha=alpha.astype(np.float32),ink_rgb=ink_rgb,
                        core=core,ring=ring,region=np.array(DESTINATION_REGION))
    cv2.imwrite(str(OUT/"actual-f3402-observed-word-native.png"),observed.astype(np.uint8))
    cv2.imwrite(str(OUT/"alternate-f3402-observed-alpha.png"),np.rint(alpha*255).astype(np.uint8))
    for label,color in (("dark",(45,45,55)),("purple",(228,136,160)),
                        ("brown",(36,77,132))):
        preview=alpha[...,None]*ink_rgb+(1-alpha[...,None])*np.array(color)
        cv2.imwrite(str(OUT/f"alternate-f3402-glyph-only-on-{label}.png"),
                    np.clip(np.rint(preview),0,255).astype(np.uint8))
    glyphs=[("愛",(700,954,738,992)),("し",(746,954,772,992)),
            ("て",(782,954,812,992)),("る",(824,954,852,992)),
            ("寂",(870,954,909,992)),("し",(918,954,943,992)),
            ("さ",(954,954,984,992)),("2",(990,954,1008,992)),
            ("分",(1009,954,1048,992)),("の",(1050,954,1085,992)),
            ("1",(1089,954,1106,992)),("ず",(1110,954,1143,992)),
            ("つ",(1150,954,1183,992)),("を",(1191,954,1221,992))]
    record={"accepted":False,"authorization":{
        "user_message":"允许先重建清晰字幕，看片后再指定返工",
        "relay":"Root explicitly relayed the human authorization on 2026-10-05",
        "scope":[1037,1043],"allowance":"Real original glyph alternate with minor stroke differences"},
        "kind":"alternate_real_original_glyph_donor",
        "lyric":"愛してる 寂しさ2分の1ずつを",
        "source_frame":3402,"source_path":str(SOURCE),"source_file_sha256":sha(SOURCE),
        "source_bgr_sha256":hashlib.sha256(source.tobytes()).hexdigest(),
        "source_crop_matches_independent_sequential_decode":True,
        "native_canvas":[1920,1080],"donor_region":DONOR_REGION,
        "destination_region":DESTINATION_REGION,
        "registration":{"kind":"integer_translation_only","matrix":[[1,0,-12],[0,1,0]],
                        "scale":1,"rotation":0,"baseline_y":959,
                        "explanation":"Register the same-word original line origin x688 to original target line origin x676. Handwritten stroke extrema vary slightly; no glyph morph or resizing."},
        "per_glyph":[{"text":text,"donor_frame":3402,"donor_bounds":bounds,
                      "destination_bounds":[bounds[0]-12,bounds[1],bounds[2]-12,bounds[3]],
                      "pixel_source":"src-1905-f3402.png","status":"real source alternate; unaccepted"}
                     for text,bounds in glyphs],
        "donor_foreground_bgr_estimate":foreground.tolist(),
        "target_foreground_bgr_observed_median":target_foreground.tolist(),
        "target_palette_probe":{"frame":1037,"bounds":[686,959,806,989],
                                "observed_pixels":int(target_core.sum())},
        "palette_policy":"Extract the real donor shape, then compose using observed target-phase cream ink. Decoded donor warm pink-plate chroma is not copied onto target boots.",
        "observed_alpha_pixels":int(visible.sum()),
        "observed_core_pixels":int(core.sum()),
        "donor_plate_reconstruction_mean_absolute_bgr":float(errors[visible].mean()),
        "donor_plate_reconstruction_max_absolute_bgr":float(errors[visible].max()),
        "npz_sha256":sha(OUT/"authorized-alternate-japanese-f3402.npz"),
        "limitations":["Not restoration of the unobservable original f1037 stroke alpha.",
                       "Donor ink is genuinely observed; alpha and donor plate are estimated.",
                       "Chinese is not replaced by this alternate Japanese donor.",
                       "Actual-speed and encoded review still pending."]}
    (OUT/"authorized-alternate-glyph-provenance.json").write_text(
        json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"visible_pixels":int(visible.sum()),"core_pixels":int(core.sum()),
                      "foreground":foreground.tolist(),"mean_error":float(errors[visible].mean())}))


if __name__ == "__main__":
    main()
