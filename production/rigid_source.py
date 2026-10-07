"""Prove source rigid camera/layer motion using an isotropic transform and RGB residuals."""

import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT / ".python_deps"))
import cv2
import numpy as np
from group_source import character_mask, measure


def similarity(a,b,ma=None,mb=None):
    ma=character_mask(a)[0] if ma is None else ma
    mb=character_mask(b)[0] if mb is None else mb
    size=(640,360)
    ga=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY).astype(np.float32)/255
    gb=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY).astype(np.float32)/255
    ga[ma==0]=220/255
    gb[mb==0]=220/255
    ga=cv2.resize(ga,size,interpolation=cv2.INTER_AREA)
    gb=cv2.resize(gb,size,interpolation=cv2.INTER_AREA)
    warp=np.float32([[1,0,0],[0,1,0]])
    try:
        score,warp=cv2.findTransformECC(gb,ga,warp,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,60,1e-6),None,3)
    except cv2.error:
        return None
    raw=cv2.invertAffineTransform(warp)
    av=(float(raw[0,0])+float(raw[1,1]))/2
    bv=(float(raw[1,0])-float(raw[0,1]))/2
    matrix=np.float32([[av,-bv,raw[0,2]*3],[bv,av,raw[1,2]*3]])
    scale=float(np.sqrt(av*av+bv*bv))
    angle=float(np.degrees(np.arctan2(bv,av)))
    if not (0.75<scale<1.4) or abs(angle)>30:
        return None
    warped=cv2.warpAffine(a,matrix,(1920,1080),borderMode=cv2.BORDER_CONSTANT,borderValue=(237,135,148))
    wm=cv2.warpAffine(ma,matrix,(1920,1080),flags=cv2.INTER_NEAREST)
    metric=measure(warped,b,wm,mb)
    return {"metric":metric,"matrix":matrix.tolist(),"ecc":float(score),"scale":scale,"rotation_degrees":angle,"confirmed":metric["coherent"]<350 and metric["largest"]<120,"kind":"confirmed_source_rigid_similarity"}


def main():
    import argparse,json
    parser=argparse.ArgumentParser()
    parser.add_argument("a",type=int)
    parser.add_argument("b",type=int)
    args=parser.parse_args()
    source=next(ROOT.parent.glob("*.mp4"))
    cap=cv2.VideoCapture(str(source))
    cap.set(cv2.CAP_PROP_POS_FRAMES,args.a)
    _,a=cap.read()
    cap.set(cv2.CAP_PROP_POS_FRAMES,args.b)
    _,b=cap.read()
    cap.release()
    cv2.imwrite(str(ROOT / f"pair-f{args.a}.png"),a)
    cv2.imwrite(str(ROOT / f"pair-f{args.b}.png"),b)
    result=similarity(a,b)
    ma=character_mask(a)[0]
    mb=character_mask(b)[0]
    diff=cv2.absdiff(a,b)
    diff=np.clip(diff.astype(np.uint16)*4,0,255).astype(np.uint8)
    cv2.imwrite(str(ROOT / f"pair-f{args.a}-f{args.b}-rgb-diff-x4.png"),diff)
    active=cv2.dilate(ma|mb,np.ones((3,3),np.uint8))
    da=cv2.GaussianBlur(a,(5,5),0.8)
    db=cv2.GaussianBlur(b,(5,5),0.8)
    delta=cv2.absdiff(da,db).max(axis=2)
    diagnostic=np.zeros_like(a)
    diagnostic[active!=0]=(50,50,50)
    diagnostic[(active!=0)&(delta>=22)]=(0,0,255)
    cv2.imwrite(str(ROOT / f"pair-f{args.a}-f{args.b}-masked-regions.png"),diagnostic)
    ea=cv2.Canny(cv2.cvtColor(a,cv2.COLOR_BGR2GRAY),80,180)
    eb=cv2.Canny(cv2.cvtColor(b,cv2.COLOR_BGR2GRAY),80,180)
    overlay=np.full_like(a,245)
    overlay[ea!=0]=(255,140,20)
    overlay[eb!=0]=(20,140,255)
    overlay[(ea!=0)&(eb!=0)]=(65,65,65)
    cv2.imwrite(str(ROOT / f"pair-f{args.a}-f{args.b}-contours.png"),overlay)
    report={"frames":[args.a,args.b],"direct":measure(a,b,ma,mb),"rigid_similarity":result}
    (ROOT / f"pair-f{args.a}-f{args.b}.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
