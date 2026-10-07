"""Mechanically adopt delegated static drafts without granting artistic acceptance."""

import argparse
import hashlib
import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent


def integrate(paths):
    destination = ROOT/"asset_selections.json"
    data = json.loads(destination.read_text(encoding="utf-8"))
    rows = {r["source_frame"]: r for r in data["selections"]}
    mapping = json.loads((ROOT/"source_map.json").read_text(encoding="utf-8"))
    canonical = {c["frame"] for c in mapping["cels"]}
    adopted, preserved, skipped = [], [], []
    for path in paths:
        path = path.resolve()
        proposal = json.loads(path.read_text(encoding="utf-8"))
        if proposal.get("accepted", proposal.get("artistic_accepted")) is not False:
            raise ValueError(f"Proposal must explicitly remain unaccepted: {path}")
        owner = proposal.get("owner", path.parent.name)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        suggestions = proposal.get("selections", proposal.get("proposals", proposal.get("cels")))
        if not isinstance(suggestions, list):
            raise ValueError(f"No structured draft suggestions in {path}")
        for row in suggestions:
            asset_path = row["path"].replace("\\", "/")
            frame, asset = row["source_frame"], ROOT/asset_path
            if frame not in canonical or asset.parent != ROOT/"generated" or not asset.is_file():
                raise ValueError(f"Invalid draft proposal: {row}")
            if row.get("accepted", row.get("artistic_accepted")) is True or cv2.imread(str(asset)) is None:
                raise ValueError(f"Accepted or undecodable draft proposal: {row}")
            previous = rows.get(frame)
            if previous and previous.get("adoption") != "delegated_draft_only":
                preserved.append(frame)
                continue
            review = row.get("review", row.get("static_review"))
            if not isinstance(review, (str, dict)):
                skipped.append({"frame": frame, "reason": "no completed static review"})
                continue
            issues = row.get("known_issues", review.get("issues", []) if isinstance(review, dict) else [])
            review_text = review if isinstance(review, str) else json.dumps(review, ensure_ascii=False)
            rows[frame] = {"source_frame": frame, "path": asset_path,
                           "review": "draft_static_only; "+review_text,
                           "known_issues": issues, "accepted": False,
                           "adoption": "delegated_draft_only", "reviewed_by": owner,
                           "proposal": path.relative_to(ROOT).as_posix(),
                           "proposal_sha256_at_adoption": digest}
            for key in ("consecutive_review", "static_contact_path"):
                if key in row:
                    rows[frame][key] = row[key]
            adopted.append(frame)
    data["selections"] = sorted(rows.values(), key=lambda r: r["source_frame"])
    destination.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps({"adopted_draft_frames": adopted, "preserved_explicit_choices": preserved,
                      "skipped_incomplete_reviews": skipped,
                      "artistic_acceptance": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("proposals", nargs="+", type=Path)
    args = parser.parse_args()
    integrate(args.proposals)
