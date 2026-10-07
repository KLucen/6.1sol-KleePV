"""Private, source-only evidence and traceable middle draft proposals."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

QA = Path(__file__).resolve().parent
ROOT = QA.parents[1]
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta

FRAMES = [2059, 2061, 2065, 2069, 2073, 2077]
BOXES_EARLY = {"head-eye-hair": [1160, 140, 1680, 500],
               "both-hands-cuffs": [1010, 410, 1760, 720],
               "legs-boots-hem": [1170, 620, 1720, 1080]}
BOXES = {"head-eye-hair": [600, 140, 1680, 570],
         "both-hands-cuffs": [650, 350, 1770, 760],
         "legs-boots-hem": [780, 620, 1720, 1080]}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2), encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def path_info(path):
    with Image.open(path) as im:
        return {"path": str(path), "sha256": sha(path), "canvas": list(im.size)}


def prepare():
    manifest = read(ROOT / "full-pv-progress-manifest.json")
    rows = manifest["cels"]
    row_map = {r["canonical_source_frame"]: r for r in rows}
    wanted = [2058, *FRAMES, 2081]
    originals = {}
    cap = cv2.VideoCapture(manifest["source"])
    for frame in range(max(wanted) + 1):
        ok, actual = cap.read()
        if not ok:
            raise RuntimeError(f"Sequential decode failed at {frame}")
        if frame in wanted:
            saved = cv2.imread(str(ROOT / row_map[frame]["source_reference"]))
            if not np.array_equal(actual, saved):
                raise RuntimeError(f"Source reference mismatch at {frame}")
            originals[frame] = actual
    cap.release()
    queue = []
    for frame in FRAMES:
        row = row_map[frame]
        if row["selected_asset"]:
            raise RuntimeError(f"Already selected: {frame}")
        index = wanted.index(frame)
        previous, after = wanted[index - 1], wanted[index + 1]
        target = ROOT / row["source_reference"]
        a = originals[previous]
        b = originals[frame]
        boxes = BOXES_EARLY if frame < 2065 else BOXES
        make_delta(ROOT / row_map[previous]["source_reference"], target,
                   QA / f"actual-source-f{previous}-f{frame}-AB-RGB-contours.png")
        make_delta(target, ROOT / row_map[after]["source_reference"],
                   QA / f"actual-source-f{frame}-f{after}-AB-RGB-contours.png")
        native = Image.new("RGB", (max(box[2]-box[0] for box in boxes.values()),
                                   sum(box[3]-box[1]+28 for box in boxes.values())), "#202024")
        draw = ImageDraw.Draw(native)
        panels = []
        y = 0
        for name, (x1, y1, x2, y2) in boxes.items():
            aa, bb = a[y1:y2, x1:x2], b[y1:y2, x1:x2]
            crop = Image.fromarray(cv2.cvtColor(bb, cv2.COLOR_BGR2RGB))
            draw.text((8, y + 8), name + " native 1:1 CURRENT", fill="white")
            native.paste(crop, (0, y+28))
            y += crop.height + 28
            diff = np.minimum(cv2.absdiff(aa, bb).astype(np.uint16)*4, 255).astype(np.uint8)
            ea, eb = cv2.Canny(aa, 80, 160), cv2.Canny(bb, 80, 160)
            overlay = np.full_like(aa, 245)
            overlay[ea != 0] = (235, 110, 30)
            overlay[eb != 0] = (30, 80, 235)
            overlay[(ea != 0) & (eb != 0)] = (50, 50, 50)
            panel = Image.new("RGB", (4 * crop.width, crop.height + 28), "#202024")
            pd = ImageDraw.Draw(panel)
            for k, (array, title) in enumerate(zip((aa, bb, diff, overlay),
                                  ("BEFORE", "CURRENT", "RGB x4", "blue before / red current"))):
                pd.text((k*crop.width+8, 8), name+": "+title, fill="white")
                panel.paste(Image.fromarray(cv2.cvtColor(array, cv2.COLOR_BGR2RGB)), (k*crop.width,28))
            panels.append(panel)
        native.save(QA / f"f{frame}-source-native-keyparts.png")
        local = Image.new("RGB", (max(p.width for p in panels), sum(p.height for p in panels)), "#202024")
        y = 0
        for panel in panels:
            local.paste(panel, (0, y))
            y += panel.height
        local.save(QA / f"f{frame}-keyparts-AB-RGB-contours.png")
        queue.append({**row, "previous_frame": previous, "next_frame": after,
                      "actual_sequential_decode_reference_equal": True})
    anchor = ROOT / "generated" / "fine-f2058.png"
    Image.open(anchor).crop((1080, 135, 1750, 1080)).save(QA / "klee-f2058-main-identity-only-crop.png")
    write(QA / "source-queue.json", {"snapshot_utc": datetime.now(timezone.utc).isoformat(),
          "manifest_sha256": sha(ROOT / "full-pv-progress-manifest.json"), "queue": queue,
          "source_sha256": sha(Path(manifest["source"])), "source_decode_equal": wanted,
          "native_boxes": BOXES, "accepted": False})
    print(json.dumps({"frames": FRAMES, "source_equal": wanted, "source_frames": sum(r["source_frames_covered"] for r in queue)}))


def save(frame, original, repair=False):
    suffix="hair-v2" if repair else "v1"
    job_path = ROOT / "jobs" / f"middle-continuation-f{frame}-2026-10-05-{suffix}.json"
    job = read(job_path)
    original = Path(original)
    target = ROOT / job["output"]
    if target.exists():
        raise FileExistsError(target)
    shutil.copy2(original, target)
    job.update({"original_tool_output": str(original), "tool_output_metadata": path_info(original),
                "workspace_output_metadata": path_info(target), "output_sha256": sha(target),
                "status": "generated_pending_static_review", "accepted": False, "artistic_accepted": False})
    write(job_path, job)
    source = Image.open(Path(job["source_reference"])).convert("RGB")
    draft = Image.open(target).convert("RGB").resize(source.size, Image.Resampling.LANCZOS)
    page = Image.new("RGB", (3840, 1112), "#202024")
    draw = ImageDraw.Draw(page)
    draw.text((12,8), f"f{frame} SOURCE left / NEW DRAFT right; review only", fill="white")
    page.paste(source, (0,32))
    page.paste(draft, (1920,32))
    page.save(QA / f"f{frame}-source-new-static.png")
    for name, box in BOXES.items():
        a, b = source.crop(box), draft.crop(box)
        page = Image.new("RGB", (a.width*2, a.height+28), "#202024")
        draw = ImageDraw.Draw(page)
        draw.text((8,8), f"SOURCE left / DRAFT right: {name} normalized-to-source review", fill="white")
        page.paste(a,(0,28))
        page.paste(b,(a.width,28))
        page.save(QA / f"f{frame}-source-new-{name}.png")
    print(json.dumps({"frame": frame, "output": str(target), "metadata": job["workspace_output_metadata"]}))


def review(frame, findings, observed):
    job_path = ROOT / "jobs" / f"middle-continuation-f{frame}-2026-10-05-v1.json"
    repair_path=ROOT / "jobs" / f"middle-continuation-f{frame}-2026-10-05-hair-v2.json"
    if repair_path.is_file() and (ROOT / read(repair_path)["output"]).is_file():
        job_path=repair_path
    job = read(job_path)
    job.update({"status": "reviewed_static_temporal_pending", "accepted": False,
                "artistic_accepted": False, "known_issues": findings,
                "source_current_observed": observed, "actual_speed_review": "not_performed",
                "static_review": f"qa/{QA.name}/f{frame}-source-new-static.png"})
    write(job_path, job)
    proposal_path = QA / "draft-proposal.json"
    data = read(proposal_path) if proposal_path.exists() else {"accepted": False, "artistic_accepted": False, "proposals": []}
    data["proposals"] = [r for r in data["proposals"] if r["source_frame"] != frame]
    data["proposals"].append({"source_frame": frame, "path": job["output"],
        "job": job_path.relative_to(ROOT).as_posix(), "source_cel": job["source_cel"],
        "source_exposures": job["source_exposures"], "accepted": False,
        "artistic_accepted": False, "review": job["static_review"], "known_issues": findings,
        "actual_speed_review": "not_performed", "source_current_observed": observed,
        "output_sha256": job["output_sha256"]})
    data["proposals"].sort(key=lambda r:r["source_frame"])
    write(proposal_path,data)
    print(json.dumps({"reviewed":frame,"proposal_count":len(data["proposals"])}))


def seal():
    proposal_path=QA / "draft-proposal.json"
    proposal=read(proposal_path)
    proposal["scope"]=[2059,2081]
    proposal["source_frames_addable_draft_only"]=18
    proposal["successful_builtin_calls"]=7
    proposal["unique_missing_cels_generated"]=6
    proposal["targeted_repair_calls"]=1
    proposal["planned_but_unsubmitted_repair_calls"]=1
    proposal["blocked_candidates"]=[{"source_frame":2077,"path":"generated/middle-continuation-f2077-2026-10-05-v1.png",
        "source_frames":4,"adopt":False,"reason":"Third blonde bunch behind near glove/collar; no completed repair. hair-v2 prompt saved but NEVER submitted after parent stop."}]
    proposal["actual_speed_review"]="not_performed"
    proposal["final_composition_review"]="not_performed"
    write(proposal_path,proposal)
    names=[f"middle-continuation-f{f}-2026-10-05-v1" for f in FRAMES]
    names += ["middle-continuation-f2065-2026-10-05-hair-v2","middle-continuation-f2077-2026-10-05-hair-v2"]
    archive=QA / "promptset-7-successful-plus-1-unsubmitted.json"
    if archive.exists():
        raise FileExistsError(archive)
    records=[]
    failures=[]
    for name in names:
        path=ROOT / "jobs" / (name+".json")
        job=read(path)
        if "ordered_reference_metadata" in job:
            for record in job["ordered_reference_metadata"]:
                if record["sha256"]!=sha(Path(record["path"])):
                    failures.append("Reference changed: "+record["path"])
            job["ordered_reference_metadata_phase"]="before_builtin_call" if job["source_frame"]!=2059 else "after_output_saved; original full prompt/ordered roles were saved before call"
        else:
            job["ordered_reference_metadata"]=[{**path_info(Path(ref)), "role":role}
               for ref,role in zip(job["references"],job["reference_roles"])]
            job["ordered_reference_metadata_phase"]="after_output_saved" if "original_tool_output" in job else "before_planned_call_not_submitted"
        submitted="original_tool_output" in job
        job["actual_builtin_call_submitted"]=submitted
        if submitted:
            tool=path_info(Path(job["original_tool_output"]))
            workspace=path_info(ROOT/job["output"])
            if tool["sha256"] != workspace["sha256"]:
                failures.append("Copy differs from native output: "+name)
            job["tool_output_metadata"]=tool
            job["workspace_output_metadata"]=workspace
        write(path,job)
        records.append({"job":str(path),"job_sha256":sha(path),"submitted":submitted,
                        "full_saved_job":job})
    for offset in (0,3):
        page=Image.new("RGB",(1280,3*384),"#202024")
        draw=ImageDraw.Draw(page)
        for i,frame in enumerate(FRAMES[offset:offset+3]):
            row=next(r for r in read(QA / "source-queue.json")["queue"] if r["canonical_source_frame"]==frame)
            active=next((r["path"] for r in proposal["proposals"] if r["source_frame"]==frame),
                         f"generated/middle-continuation-f{frame}-2026-10-05-v1.png")
            draw.text((8,i*384+8),f"f{frame} SOURCE left / DRAFT right; "+("BLOCKED, unselected" if frame==2077 else "unaccepted draft"),fill="white")
            for k,p in enumerate((ROOT/row["source_reference"],ROOT/active)):
                page.paste(Image.open(p).convert("RGB").resize((640,360),Image.Resampling.LANCZOS),(k*640,i*384+24))
        page.save(QA / f"source-new-consecutive-page-{offset//3+1:02d}.png")
    write(archive,{"snapshot_utc":datetime.now(timezone.utc).isoformat(),
           "successful_builtin_calls":7,"successful_missing_cel_calls":6,"successful_targeted_repair_calls":1,
           "not_submitted_planned_repairs":1,"accepted":False,"records":records,
           "proposal_path":str(proposal_path),"proposal_sha256":sha(proposal_path),
           "validation_failures":failures,"review_scope":"Full outputs, source/native focus/A-B actual RGB-contours visually inspected. Consecutive page visual review pending until opened. Final composition and actual speed not performed."})
    if failures:
        raise RuntimeError(failures)
    print(json.dumps({"archive":str(archive),"archive_sha256":sha(archive),"proposal":str(proposal_path),
                      "addable_proposals":len(proposal["proposals"]),"source_frames":18,"failed":failures}))


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    sub.add_parser("prepare")
    sub.add_parser("back-identity")
    sub.add_parser("seal")
    q=sub.add_parser("save")
    q.add_argument("frame",type=int)
    q.add_argument("original")
    q=sub.add_parser("save-repair")
    q.add_argument("frame",type=int)
    q.add_argument("original")
    q=sub.add_parser("review")
    q.add_argument("frame",type=int)
    q.add_argument("findings",type=json.loads)
    q.add_argument("observed")
    q=sub.add_parser("record")
    q.add_argument("frame",type=int)
    q=sub.add_parser("reference-meta")
    q.add_argument("frame",type=int)
    args=p.parse_args()
    if args.mode=="prepare":
        prepare()
    elif args.mode=="back-identity":
        Image.open(ROOT / "generated" / "root-continuation-f0827-v1.png").crop((820,150,1210,475)).save(QA / "klee-back-hat-hair-only-f0827.png")
    elif args.mode=="seal":
        seal()
    elif args.mode=="save":
        save(args.frame,args.original)
    elif args.mode=="save-repair":
        save(args.frame,args.original,repair=True)
    elif args.mode=="review":
        review(args.frame,args.findings,args.observed)
    elif args.mode=="record":
        data=read(QA / f"f{args.frame}-static-review-input.json")
        review(args.frame,data["findings"],data["observed"])
    elif args.mode=="reference-meta":
        path=ROOT / "jobs" / f"middle-continuation-f{args.frame}-2026-10-05-v1.json"
        data=read(path)
        data["ordered_reference_metadata"]=[{**path_info(Path(ref)), "role":role}
             for ref,role in zip(data["references"],data["reference_roles"])]
        write(path,data)
        print(json.dumps({"frame":args.frame,"references":len(data["ordered_reference_metadata"])}))
