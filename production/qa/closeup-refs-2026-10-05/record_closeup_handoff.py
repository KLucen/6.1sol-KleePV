"""Record the exact private visual audit scope after viewing source-native evidence."""

import json

from prepare_closeup_refs import OUT, ROOT, digest


def main():
    path = OUT / "closeup-reference-handoff.json"
    if path.exists():
        raise FileExistsError("Handoff already saved.")
    queue_path = OUT / "corrected-closeup-source-reference-queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    notes = {
        1162: "Same character source drawing as f1161; private source alias proposal, only captions and stars change.",
        1164: "Distinct mild up/right head and hat registration; left fist/cuff shifts right and cuff angle changes; closed eyelids and small O remain.",
        1172: "Left-leaning head/body changes relative to f1168; screen-left finger and cuff rise, screen-right index becomes more vertical beside hat; closed eyes/O mouth.",
        1187: "Right-leaning pose; screen-left pointing finger rises above hat at shallow diagonal, right finger rises beside hat; squeezed eyelids and tiny flat mouth.",
        1195: "Both pointing hands lower in front of forehead; head/hat and sleeve geometry change; squeezed eyelids and tiny flat mouth.",
        1199: "Screen-left hand lowers/rotates toward central bangs and screen-right index tilts diagonally up-left; tiny flat mouth and lowered head.",
        1203: "Both forehead-pointing hands shift, cuffs and hat change, tiny mouth becomes W.",
        1211: "Both arms spread up/out with open palms; individual finger outlines/cuffs/face differ from f1207; half-open eyes and O mouth.",
        1216: "Eyes close, mouth widens to open U, arm/cuff/palm and hair outlines differ from f1211. Single-frame character exposure, not a blank.",
        1221: "Closed eyes and rounder O mouth; palms/cuffs/sleeves/head and bangs differ from f1217; caption changes independently.",
    }
    reviews = []
    for row in queue["queue"]:
        frame = row["source_frame"]
        viewed = [page["path"] for page in row["native_local_pages"]]
        if frame in [1164, 1172, 1187, 1195, 1199, 1203]:
            viewed.append(row["native_body_crop"]["path"])
        if frame in [1211, 1216, 1221]:
            viewed.append(row["current_source"]["path"])
        if frame == 1162:
            viewed = [str(OUT / f"f{f:04d}-source-actual.png") for f in [1161, 1162, 1163]]
        reviews.append({"frame": frame, "source_visual_disposition": notes[frame],
            "actual_viewed_files": [{"path": p, "sha256": digest(__import__("pathlib").Path(p))} for p in viewed],
            "native_keyparts_review_complete": True, "artistic_accepted": False,
            "full_3840px_AB_boards": "saved diagnostics; not claimed as native displayed review",
            "earlier_keypart_clip_caveat": "Local ROIs target the current pose and may partially clip a previous moving hand; intact sequential originals and full AB/RGB/contour proof accompany them."})
    report = {"corrected_queue": {"path": str(queue_path), "sha256": digest(queue_path)},
        "original_queue_preserved": queue["first_preparation_queue"],
        "source1162_alias_proposal": {"path": str(OUT / "source1162-alias-proposal.json"),
            "sha256": digest(OUT / "source1162-alias-proposal.json")},
        "source": queue["source"], "source_sha256": queue["source_sha256"],
        "source_map_sha256": digest(ROOT / "source_map.json"),
        "sequential_original_decode": queue["sequential_decode"], "exact_source_checks": queue["exact_source_checks"],
        "reviews": reviews, "shared_edits_performed": False, "imagegen_calls": 0,
        "aliases_adopted": False, "accepted": False, "original_speed_review": "not_performed",
        "lesson": "Reference crops follow actual shot and hand extrema. Full-body standing ROIs are not closeup ROIs; open palms at f1211+ require the full 1920-pixel frame and separate wide cuffs. Preserve wrong first crops as historical evidence, mark superseded, and use the corrected queue."}
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"handoff": str(path), "sha256": digest(path), "reviewed_targets": list(notes)}))


if __name__ == "__main__":
    main()
