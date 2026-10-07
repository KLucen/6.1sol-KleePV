"""Compare visible original glyph support before any donor is approved."""

import json
from pathlib import Path

import cv2
import numpy as np

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def warm(image):
    b,g,r = cv2.split(image.astype(np.int16))
    return (b > 170) & (g > 195) & (r > 210) & (r > b+8) & (g > b+5)


def main():
    target_full = cv2.imread(str(ROOT / "source_refs/src-0569-f1037.png"))
    target = target_full[945:1047,350:1570]
    donors = [(3360, cv2.imread(str(OUT / "sample-f3360-native-caption.png"))),
              (3420, cv2.imread(str(OUT / "candidate-f3420-native-caption.png"))),
              (3144, cv2.imread(str(OUT / "candidate-f3144-native-caption.png")))]
    probes = ((676,959,810,989), (1110,959,1203,989))
    record = []
    page = np.full((170*len(donors), 1100, 3), 32, np.uint8)
    for i, (frame, donor) in enumerate(donors):
        page[i*170+20:i*170+122,:527] = target[:,676-350:1203-350]
        page[i*170+20:i*170+122,550:1098] = donor[:,670-350:1218-350]
        cv2.putText(page,f"Target f1037 / donor f{frame}",(4,i*170+15),
                    cv2.FONT_HERSHEY_SIMPLEX,.45,(255,255,255),1,cv2.LINE_AA)
        for probe in probes:
            x0,y0,x1,y1 = probe
            tm = warm(target[y0-945:y1-945,x0-350:x1-350]).astype(np.float32)
            field = warm(donor[y0-945:y1-945]).astype(np.float32)
            scores = cv2.matchTemplate(field,tm,cv2.TM_CCOEFF_NORMED)
            _,score,_,loc=cv2.minMaxLoc(scores)
            shift=loc[0]+350-x0
            record.append({"frame":frame,"target_probe":probe,
                           "matching_donor_x":loc[0]+350,"integer_shift":shift,
                           "warm_support_correlation":score})
    cv2.imwrite(str(OUT / "native-target-later-registration.png"),page)
    (OUT / "native-registration-probes.json").write_text(
        json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps(record,indent=2))


if __name__ == "__main__":
    main()
