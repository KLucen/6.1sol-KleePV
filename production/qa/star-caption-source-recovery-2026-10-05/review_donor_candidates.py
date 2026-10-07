"""Native-size evidence for the authorized alternate real glyph donors."""

from pathlib import Path
import cv2
import numpy as np

OUT=Path(__file__).resolve().parent


def main():
    frames=list(range(3340,3416,3))
    for start in range(0,len(frames),8):
        rows=frames[start:start+8]
        page=np.full((len(rows)*132,650,3),32,np.uint8)
        for j,frame in enumerate(rows):
            crop=cv2.imread(str(OUT/f"caption-all-f{frame}-native.png"))[:,300:950]
            page[j*132+22:j*132+124]=crop
            cv2.putText(page,f"f{frame}",(5,j*132+17),cv2.FONT_HERSHEY_SIMPLEX,
                        .5,(255,255,255),1,cv2.LINE_AA)
        cv2.imwrite(str(OUT/f"third-chorus-donor-detail-page-{start//8+1:02d}.png"),page)
    frames=[3360,3388,3394,3397,3400,3402,3403,3405,3406,3408,3409,3410]
    page=np.full((3*215,4*190,3),32,np.uint8)
    for i,frame in enumerate(frames):
        raw=cv2.imread(str(OUT/f"caption-all-f{frame}-native.png"))
        crop=raw[950-945:997-945,1006-350:1050-350]
        crop=cv2.resize(crop,None,fx=4,fy=4,interpolation=cv2.INTER_NEAREST)
        x=(i%4)*190
        y=(i//4)*215
        page[y+22:y+22+crop.shape[0],x:x+crop.shape[1]]=crop
        cv2.putText(page,f"f{frame} / actual pixels",(x+2,y+16),cv2.FONT_HERSHEY_SIMPLEX,
                    .4,(255,255,255),1,cv2.LINE_AA)
    cv2.imwrite(str(OUT/"actual-donor-middle-glyph-grid.png"),page)


if __name__ == "__main__":
    main()
