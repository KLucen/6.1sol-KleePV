"""Screen same-word donors using visible, uncovered original letter shapes."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
META = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))


def warm(image):
    b,g,r = cv2.split(image.astype(np.int16))
    return ((b > 170) & (g > 195) & (r > 210)
            & (r > b+8) & (g > b+5)).astype(np.uint8)


def main():
    target = cv2.imread(str(ROOT / "source_refs/src-0569-f1037.png"))
    # Three letters wholly outside the source cuff. Never evaluate similarity
    # using the cuff-overlapped middle of this sentence.
    template = warm(target[959:989,686:806]).astype(np.float32)
    cv2.imwrite(str(OUT / "target-first-three-observed-mask.png"),template*255)
    capture = cv2.VideoCapture(META["source"])
    rows=[]
    i=0
    while True:
        ok,image=capture.read()
        if not ok:
            break
        if 1037 <= i < 1153 or 3340 <= i < 3480:
            crop=image[945:1047,350:1570]
            cv2.imwrite(str(OUT / f"caption-all-f{i}-native.png"),crop)
            band=warm(image[959:989,620:960]).astype(np.float32)
            dot=cv2.matchTemplate(band,template,cv2.TM_CCORR)
            area=cv2.matchTemplate(band,np.ones(template.shape,np.float32),cv2.TM_CCORR)
            dice=2*dot/np.maximum(area+float(template.sum()),1)
            _,score,_,location=cv2.minMaxLoc(dice)
            rows.append({"frame":i,"pts":META["pts"][i],
                         "native_crop":f"caption-all-f{i}-native.png",
                         "template_dice":score,"donor_x":location[0]+620,
                         "shift_x":location[0]+620-686,
                         "source_bgr_sha256":hashlib.sha256(image.tobytes()).hexdigest()})
        i+=1
    capture.release()
    rows.sort(key=lambda row:row["template_dice"],reverse=True)
    (OUT / "same-caption-drawing-candidates.json").write_text(json.dumps({
        "source_sha256":META["sha256"],"decoded_frames":i,
        "target_frame":1037,"target_probe":[686,959,806,989],
        "caption_drawings_not_approved":rows},indent=2),encoding="utf-8")
    print(json.dumps(rows[:24],indent=2))


if __name__ == "__main__":
    main()
