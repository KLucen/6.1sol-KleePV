"""Private draft queue preparation and builtin-output archiving, not artwork synthesis."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta


def prepare():
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    rows = manifest["cels"]
    lookup = {r["canonical_source_frame"]: r for r in rows}
    frozen = json.loads((OUT / "source-evidence-queue.json").read_text(encoding="utf-8"))["queue"]
    queue = [dict(r) for r in frozen if r["canonical_source_frame"] < 3470]
    for row in queue:
        f = row["source_frame"] = row["canonical_source_frame"]
        previous = rows[rows.index(lookup[f]) - 1]
        p = previous["canonical_source_frame"]
        a_path, b_path = ROOT / previous["source_reference"], ROOT / row["source_reference"]
        a, b = cv2.imread(str(a_path)), cv2.imread(str(b_path))
        delta = OUT / f"f{p}-f{f}-source-ab-rgb-contours.png"
        make_delta(a_path, b_path, delta)
        regions = [("eyes_mouth_bangs", (700, 350, 1260, 720)),
                   ("left_glove_cuff", (90, 500, 680, 1010)),
                   ("right_glove_cuff_hair", (1280, 440, 1880, 1010))]
        canvas = Image.new("RGB", (1280, sum((y2-y1)*2+64 for _,(_,y1,_,y2) in regions)), "#202024")
        draw = ImageDraw.Draw(canvas)
        y = 0
        for name, (x1, y1, x2, y2) in regions:
            aa, bb = a[y1:y2,x1:x2], b[y1:y2,x1:x2]
            h = aa.shape[0]
            diff = np.minimum(cv2.absdiff(aa,bb).astype(np.uint16)*4,255).astype(np.uint8)
            ea, eb = cv2.Canny(aa,80,160), cv2.Canny(bb,80,160)
            contours = np.full_like(aa,245)
            contours[ea!=0]=(235,110,30)
            contours[eb!=0]=(30,80,235)
            contours[(ea!=0)&(eb!=0)]=(50,50,50)
            draw.text((10,y+8),f"{name}: f{p} BEFORE / f{f} CURRENT - native pixels",fill="white")
            for arr,x,yy in [(aa,0,y+28),(bb,640,y+28),(diff,0,y+h+52),(contours,640,y+h+52)]:
                canvas.paste(Image.fromarray(cv2.cvtColor(arr,cv2.COLOR_BGR2RGB)),(x,yy))
            y += h*2+64
        local=OUT/f"f{p}-f{f}-source-locals-native.png"
        canvas.save(local)
        row.update({"current_source":str(b_path),"before_source_frame":p,
                    "actual_delta":str(delta),"native_local_delta":str(local),"accepted":False})
    dest=OUT/"missing-source-reference-queue.json"
    if dest.exists():
        raise FileExistsError(dest)
    dest.write_text(json.dumps({"owner":"oct7_bulk_ending","accepted":False,"queue":queue},indent=2),encoding="utf-8")
    print(json.dumps({"queue":str(dest),"requested_cels":len(queue)}))


def job(frame, notes, prior=None):
    queue=json.loads((OUT/"missing-source-reference-queue.json").read_text(encoding="utf-8"))["queue"]
    row=next(r for r in queue if r["source_frame"]==frame)
    refs=[{"path":row["current_source"],"role":"CURRENT source sole composition, visible people, pose, expression, crop and occlusion authority","actually_viewed":True},
          {"path":str(ROOT/"qa/standing-open-eye-identity-crop.png"),"role":"Klee identity only: pale blonde short twin tails, red eyes, red clover beret white feather; not pose or crop","actually_viewed":True},
          {"path":row["actual_delta"],"role":"Actual original before/current AB, RGB x4 and blue-before/red-current contour spatial changes; CURRENT only is target","actually_viewed":True},
          {"path":row["native_local_delta"],"role":"Native current/before eyes-mouth, both hands and cuffs, hair spatial evidence; use CURRENT pose","actually_viewed":True}]
    feet_only = "FEET ONLY" in notes
    if feet_only:
        refs[1] = {"path":str(ROOT/"generated/root-continuation-f0843-v1.png"),
                   "role":"Klee costume identity only: brown boots with plain cream tops and light bare legs; NEVER full body pose or framing", "actually_viewed":True}
    if prior:
        refs.append({"path":str((ROOT/prior).resolve()),"role":"Previous Klee draft style and identity continuity only, NOT pose; defer existing defects and obey current source","actually_viewed":True})
    prompt=("Use-case: illustration-story. Produce ONE complete hand-drawn 16:9 PV cel replacing every visible original person in image 1 with Klee from Genshin Impact. "
            "Image 1 is the CURRENT actual original cel, sole authority for composition, person count, crop, posture, eye aperture, mouth, shoulder height, elbow wrist finger position and occlusion. "
            "Image 2 determines Klee identity only. Image 3 is diagnostic actual original BEFORE/CURRENT AB plus RGB x4 and contour overlay, not the requested collage. Image 4 is native local diagnostic evidence. "
            +("Image 5 is previous Klee style continuity only; follow current source changes rather than freezing it. " if prior else "")
            +"Draw one normal whole PV frame, never diagnostic panels or montage. Preserve the purple flat source background and exact original camera framing, character scale and lean. "
            "Simple thick black freehand outlines and flat unshaded color blocks, same rough low-frame-rate original style, not detailed polished anime. "
            "Klee has pale blond bangs, TWO SHORT side ponytails only, red clover beret with white feather, red eyes with same source eyelids/direction, subtle orange cheeks, red coat and cream collar. "
            "Whenever hands are visible they wear plain dark brown gloves, with SIMPLE solid cream cuffs, no lace/frills; do not add a backpack mascot to a crop where no bag is visible. "
            "Replace all original pink long hair, animal sleep-mask hat and mauve clothing; no original-person leftovers, extra hands or extra face. "
            "Keep visible source pose and gesture even when source differs from identity photo. Keep cropped torso cropped, do not invent feet, whole body, props or extra people. "
            "Remove all source lyric letters/subtitles and do not invent any text: original subtitles and source FX will be restored deterministically in video. "
            "Exact source-specific observation and changes to implement: "+notes)
    if feet_only:
        prompt += (" CRITICAL feet-only source crop: NO FACE, NO HEAD, NO HAT, NO HAIR, NO ARMS, NO HANDS, NO TORSO. "
                   "Exactly two Klee brown boots with simple cream boot tops and light lower legs replace the two visible original slippers and pajama trousers. "
                   "Keep exact original crop entry from top edge, same toe/heel axes, source crossing and front/back overlap; do not widen framing or add full figure. "
                   "Left half remains empty purple. Source slippers become Klee boots, not brown slippers. No pants, no clover symbols on boots and no extra legs.")
    target=OUT/f"job-f{frame}-v1.json"
    if target.exists():
        raise FileExistsError(target)
    value={"source_frame":frame,"cel":row["cel"],"status":"prepared","accepted":False,
           "source_exposures":row["source_exposures"],"tool":"builtin_imagegen",
           "output":f"generated/oct7-bulk-ending-f{frame}-v1.png","prompt":prompt,
           "reference_roles":refs,"source_observation":notes,"temporal_review":{"performed":False,"accepted":False}}
    target.write_text(json.dumps(value,indent=2),encoding="utf-8")
    print(json.dumps(value))


def save(frame,origin,notes):
    spec=importlib.util.spec_from_file_location("archive_oct6",ROOT/"qa/late-oct6-worker.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT=OUT
    module.save(frame,origin,notes)


def focus(frame, boxes):
    """Native source diagnostics at the actual moving face and hand locations."""
    path = OUT / "missing-source-reference-queue.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    row = next(r for r in value["queue"] if r["source_frame"] == frame)
    before = Image.open(ROOT / next(r["source_reference"] for r in json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))["cels"] if r["canonical_source_frame"] == row["before_source_frame"]))
    current = Image.open(row["current_source"])
    crops = [tuple(map(int, box.split(","))) for box in boxes.split(";")]
    width = max((b[2]-b[0])*2 for b in crops)
    height = sum(b[3]-b[1]+26 for b in crops)
    canvas = Image.new("RGB", (width, height), "#202024")
    draw = ImageDraw.Draw(canvas)
    y = 0
    for i,b in enumerate(crops):
        draw.text((8,y+5), f"local {i+1} source f{row['before_source_frame']} BEFORE / f{frame} CURRENT", fill="white")
        canvas.paste(before.crop(b), (0,y+26))
        canvas.paste(current.crop(b), (b[2]-b[0],y+26))
        y += b[3]-b[1]+26
    dest = OUT / f"f{row['before_source_frame']}-f{frame}-actual-focus-native.png"
    canvas.save(dest)
    row["native_local_delta"] = str(dest)
    row["native_focus_boxes"] = crops
    path.write_text(json.dumps(value,indent=2),encoding="utf-8")
    print(str(dest))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=["prepare","job","save","focus"])
    parser.add_argument("--frame",type=int)
    parser.add_argument("--notes")
    parser.add_argument("--prior")
    parser.add_argument("--origin")
    parser.add_argument("--boxes")
    args=parser.parse_args()
    if args.mode=="prepare":prepare()
    elif args.mode=="job":job(args.frame,args.notes,args.prior)
    elif args.mode=="save":save(args.frame,args.origin,args.notes)
    else:focus(args.frame,args.boxes)
