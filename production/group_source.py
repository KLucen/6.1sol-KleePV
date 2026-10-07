"""Remove codec-only copies without collapsing localized drawing changes."""

import json
from pathlib import Path
import sys
from functools import lru_cache
import argparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".python_deps"))
import cv2
import numpy as np
from analyze_source import foreground, signature, dump, sheet


def character_mask(image):
    mask = foreground(image)
    connected = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(connected, 8)
    if count < 2:
        return np.zeros_like(mask), [0, 0, 0, 0]
    best = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    x, y, w, h, area = stats[best]
    if area < 160:
        return np.zeros_like(mask), [0, 0, 0, 0]
    allowed=cv2.dilate((labels==best).astype(np.uint8),np.ones((7,7),np.uint8))
    return mask * allowed, [int(x), int(y), int(w), int(h)]


def measure(image_a, image_b, mask_a, mask_b):
    active = cv2.dilate(mask_a | mask_b, np.ones((3, 3), np.uint8))
    # A foreground star can hide the same cel; compare only visible character pixels.
    exclusions = []
    for image in (image_a, image_b):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        pale = ((h >= 20) & (h <= 45) & (v >= 150)) | ((s <= 25) & (v >= 201))
        cyan_scene=float(((h>=85)&(h<=151)&(s>=145)).mean())>0.10
        if not cyan_scene:
            pale |= (h>=90)&(h<=151)&(s<=90)&(v>=207)
        exclusions.append(cv2.dilate(pale.astype(np.uint8), np.ones((3, 3), np.uint8)))
    active[(exclusions[0] | exclusions[1]) != 0] = 0
    a = cv2.GaussianBlur(image_a, (5, 5), 0.8)
    b = cv2.GaussianBlur(image_b, (5, 5), 0.8)
    d = cv2.absdiff(a, b).max(axis=2)
    changed = ((d >= 22) & (active != 0)).astype(np.uint8)
    _, _, stats, _ = cv2.connectedComponentsWithStats(changed, 8)
    area = stats[1:, cv2.CC_STAT_AREA]
    return {"pixels": int(changed.sum()), "coherent": int(area[area >= 12].sum()), "largest": int(area.max(initial=0)), "mean": float(d[active != 0].mean()) if active.any() else 0.0}


def source_translation(image_a, image_b, mask_a, mask_b):
    a = cv2.cvtColor(image_a, cv2.COLOR_BGR2GRAY).astype(np.float32)
    b = cv2.cvtColor(image_b, cv2.COLOR_BGR2GRAY).astype(np.float32)
    a[mask_a == 0] = 220
    b[mask_b == 0] = 220
    (dx, dy), response = cv2.phaseCorrelate(a, b)
    if response < 0.65 or abs(dx) > 100 or abs(dy) > 100:
        return None
    matrix = np.float32([[1,0,dx],[0,1,dy]])
    warped = cv2.warpAffine(image_a,matrix,(1920,1080),borderMode=cv2.BORDER_CONSTANT,borderValue=(237,135,148))
    warped_mask = cv2.warpAffine(mask_a,matrix,(1920,1080),flags=cv2.INTER_NEAREST)
    metric = measure(warped,image_b,warped_mask,mask_b)
    if metric["coherent"] < 350 and metric["largest"] < 120:
        return {"metric":metric,"matrix":matrix.tolist(),"response":float(response),"kind":"confirmed_source_layer_translation"}
    return None


def family(frame):
    t = frame / 24
    bins = [(1.583,"opening_pillow"),(8.75,"standing_pillow"),(11.95,"pillow_face_occlusion"),(16.458,"face_reaction"),(21,"kneeling_props"),(22.333,"sack_closeup"),(29.458,"prone_pillow"),(32.708,"front_small"),(33.833,"shout_closeup"),(37.958,"star_dance"),(41.917,"cyan_profile"),(50.9,"star_gestures"),(53.54,"raised_arms_closeup"),(62.5,"seated_title_credits"),(64.125,"small_rest_pose"),(68.4,"hat_closeup"),(70,"small_seated"),(73.75,"blanket_closeup"),(74.3,"blank_transition"),(79.2,"long_seated"),(83.667,"back_side_turn"),(85.708,"shout_zoom"),(89.667,"star_dance"),(93.875,"cyan_profile"),(94.333,"wink_closeup"),(100.375,"star_gestures"),(105.792,"medium_gestures"),(110.625,"curled_floating"),(115.958,"dive_prone_alternation"),(121,"floating_turn"),(127.1,"standing_pillow"),(127.9,"blank_transition"),(128.625,"back_side_turn"),(134.042,"yellow_star_burst"),(136.1,"feet_closeup"),(141.25,"star_dance"),(144.792,"star_gestures"),(147.083,"hand_face_gestures"),(152.417,"ending_closeup")]
    return next((name for end,name in bins if t < end), "ending_closeup")


@lru_cache(maxsize=24)
def decoded(path):
    image = cv2.imread(path)
    mask, bbox = character_mask(image)
    return image, mask, bbox


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    map_path = ROOT / "source_map.json"
    source_map = json.loads(map_path.read_text(encoding="utf-8"))
    candidates = source_map["candidates"]
    if args.limit:
        candidates = candidates[:args.limit]
        source_map["partial_review"] = {"covered_candidates":len(candidates),"covered_end_frame":candidates[-1]["end"]}
        source_map["candidates"] = candidates
    representatives = []
    signatures = []
    links, review_pairs = [], []
    for i, candidate in enumerate(candidates):
        image, mask, bbox = decoded(str(ROOT / candidate["reference"]))
        sig = signature(image, mask)
        kind = family(candidate["frame"])
        match, best_score, metric, motion = None, None, None, None
        if signatures:
            errors = np.mean(np.abs(np.stack(signatures) - sig), axis=(1,2,3))
            nearby = np.flatnonzero(errors < 8.0)
            nearby = nearby[np.argsort(errors[nearby])[:5]]
            for index in nearby:
                ref = representatives[index]
                ref_image, ref_mask, _ = decoded(str(ROOT / ref["reference"]))
                result = measure(ref_image,image,ref_mask,mask)
                registered = None
                if not (result["coherent"] < 350 and result["largest"] < 120) and result["mean"] < 8:
                    registered = source_translation(ref_image,image,ref_mask,mask)
                    if registered:
                        result = registered["metric"]
                if result["coherent"] < 350 and result["largest"] < 120:
                    score = result["coherent"] + result["largest"]
                    if best_score is None or score < best_score:
                        match, best_score, metric, motion = int(index), score, result, registered
                    if result["coherent"] < 150 and result["largest"] < 60:
                        break
                elif result["coherent"] < 2500 and result["largest"] < 1500:
                    review_pairs.append({"a": ref["id"], "b": candidate["id"], "metric": result, "disposition": "kept_separate_for_local_drawing_review"})
        if match is None:
            match = len(representatives)
            candidate["cel"] = f"cel-{match:04d}"
            candidate["family"] = kind
            candidate["character_bbox"] = bbox
            candidate["review"] = "independent_candidate"
            candidate["source_transform"] = {"kind":"identity","matrix":[[1,0,0],[0,1,0]]}
            representatives.append(candidate.copy())
            signatures.append(sig)
            metric = None
        else:
            candidate["cel"] = representatives[match]["cel"]
            candidate["family"] = kind
            candidate["character_bbox"] = bbox
            candidate["review"] = "codec_copy_of_representative"
            candidate["source_transform"] = motion or {"kind":"identity","matrix":[[1,0,0],[0,1,0]]}
            if motion:
                candidate["review"] = "same_drawing_with_source_layer_translation"
        links.append({"candidate":candidate["id"],"cel":candidate["cel"],"metric_to_representative":metric,"source_transform":candidate["source_transform"]})
        if i % 50 == 0:
            print(f"grouped {i}/{len(candidates)}; {len(representatives)} independent drawing candidates",flush=True)
            dump(ROOT / "source_group_partial.json", {"partial_review":True,"covered_candidates":i+1,"covered_end_frame":candidate["end"],"cels":representatives,"candidates":candidates[:i+1],"method":"coherent character changes with verified source layer translation"})
    source_map["mode"] = "strict_source"
    source_map["cels"] = representatives
    source_map["deduplication"] = {"codec_rule": "full-resolution blurred RGB, character ROI, coherent delta>=22; only coherent<350 and largest<120 merge; exact source layer translation measured separately", "links":links,"uncertain_pairs_kept_separate":review_pairs}
    by_id = {c["id"]:c for c in candidates}
    source_map["frame_to_cel"] = [by_id[cid]["cel"] for cid in source_map["frame_to_candidate"] if cid in by_id]
    source_map["frame_to_transform"] = [by_id[cid]["source_transform"] for cid in source_map["frame_to_candidate"] if cid in by_id]
    exposures=[]
    for candidate in candidates:
        if exposures and exposures[-1]["cel"] == candidate["cel"] and exposures[-1]["source_transform"] == candidate["source_transform"]:
            exposures[-1]["end"] = candidate["end"]
            exposures[-1]["end_pts"] = candidate["end_pts"]
        else:
            exposures.append({k:candidate[k] for k in ("start","end","pts","end_pts","cel","family","source_transform")})
    source_map["source_exposures"] = exposures
    families={}
    for c in representatives:
        families.setdefault(c["family"],[]).append(c["cel"])
    source_map["families"] = families
    dump(args.output or map_path,source_map)
    dump(ROOT / "source_dedup_review.json", review_pairs)
    target=ROOT / "source_contacts"
    for page,start in enumerate(range(0,len(representatives),48)):
        sheet(representatives[start:start+48],target / f"unique-{page:02d}.jpg")
    for kind,ids in families.items():
        group=[c for c in representatives if c["cel"] in ids]
        for page,start in enumerate(range(0,len(group),48)):
            sheet(group[start:start+48],target / f"family-{kind}-{page:02d}.jpg")
    print(json.dumps({"frames":source_map["frames"],"candidates":len(candidates),"cels":len(representatives),"families":{k:len(v) for k,v in families.items()},"uncertain_pairs":len(review_pairs)}),flush=True)


if __name__ == "__main__":
    main()
