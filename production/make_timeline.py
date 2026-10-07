"""Resolve available cels to source exposures; never fill gaps with approximate poses."""

import argparse
import json
from pathlib import Path
import re

import numpy as np

ROOT = Path(__file__).resolve().parent


def homogeneous(matrix):
    return np.vstack([np.array(matrix, dtype=float), [0, 0, 1]])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    if not 0 <= args.start < args.end <= source["frames"]:
        raise ValueError("Requested source interval is invalid")
    anchors = json.loads((ROOT / "generation_jobs.json").read_text(encoding="utf-8"))["old_anchor_to_cel"]
    rows = []
    for anchor in anchors:
        stem = f'candidate-{anchor["old_id"]}'
        choices = [ROOT / "generated" / f"{stem}-red-eyes.png", ROOT / "generated" / f"{stem}-clean.png", ROOT / "generated" / f"{stem}.png"]
        asset = next((p for p in choices if p.exists()), None)
        if asset:
            rows.append((anchor["old_source_frame"], asset))
    for asset in (ROOT / "generated").glob("*.png"):
        match = re.fullmatch(r"(?:fine|opening)-f(\d+)\.png", asset.name)
        if match:
            rows.append((int(match.group(1)), asset))
    selections_path = ROOT / "asset_selections.json"
    selections = json.loads(selections_path.read_text(encoding="utf-8"))["selections"] if selections_path.exists() else []
    for selection in selections:
        rows = [(frame, asset) for frame, asset in rows if frame != selection["source_frame"]]
        if selection["path"]:
            asset = ROOT / selection["path"]
            if not asset.exists():
                raise ValueError(f"Selected asset missing: {asset}")
            rows.append((selection["source_frame"], asset))
    assets = {}
    for frame, asset in rows:
        candidate = next(c for c in source["candidates"] if c["start"] <= frame < c["end"])
        assets[candidate["cel"]] = {"path": str(asset.relative_to(ROOT)).replace("\\", "/"),
                                    "source_frame": frame, "source_reference": candidate["reference"],
                                    "canonical_to_asset_matrix": candidate["source_transform"]["matrix"],
                                    "review": "draft_static_inspected_temporal_pending"}
    aliases_path = ROOT / "source_aliases.json"
    aliases = json.loads(aliases_path.read_text(encoding="utf-8"))["aliases"] if aliases_path.exists() else []
    candidates = {c["id"]: c for c in source["candidates"]}
    for alias in aliases:
        if alias["review"] != "manual_full_resolution_source_approved":
            continue
        target = assets.get(alias["verified_target_cel"])
        if target is None:
            continue
        alias_frame = candidates[alias["source_candidate"]]
        target_frame = candidates[alias["verified_target_candidate"]]
        # Express the verified target asset in the alias cel's canonical coordinates.
        matrix = (homogeneous(target["canonical_to_asset_matrix"])
                  @ np.linalg.inv(homogeneous(target_frame["source_transform"]["matrix"]))
                  @ np.linalg.inv(homogeneous(alias["transform"]["matrix"]))
                  @ homogeneous(alias_frame["source_transform"]["matrix"]))[:2]
        assets[alias["source_cel"]] = {**target, "canonical_to_asset_matrix": matrix.tolist(),
                                        "verified_source_alias": alias}
    exposures = []
    for span in source["source_exposures"]:
        if span["end"] <= args.start:
            continue
        if span["start"] >= args.end:
            break
        if span["cel"] not in assets:
            raise ValueError(f'Missing true cel {span["cel"]} at frame {span["start"]}; refusing a held-pose substitute')
        asset = assets[span["cel"]]
        matrix = (homogeneous(span["source_transform"]["matrix"]) @ np.linalg.inv(homogeneous(asset["canonical_to_asset_matrix"])))[:2]
        exposures.append({"start": max(span["start"], args.start), "end": min(span["end"], args.end),
                          "cel": span["cel"], "source_matrix": matrix.tolist(),
                          "family": span["family"], "review": "draft"})
    if not exposures or exposures[0]["start"] != args.start or exposures[-1]["end"] != args.end:
        raise ValueError("Preview interval is not fully covered")
    for left, right in zip(exposures, exposures[1:]):
        if left["end"] != right["start"]:
            raise ValueError("Preview exposures have a gap")
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    timeline = {"source": source["source"], "frames": args.end-args.start, "source_start": args.start,
                "source_frames": source["frames"], "mode": "strict_source_draft_preview", "fps": 24,
                "source_pts": metadata["pts"][args.start:args.end],
                "assets": assets, "output_exposures": exposures,
                "notes": ["Draft only; original-speed artistic acceptance remains pending.",
                          "Only actual source copies/camera matrices reused. No morph, optical flow or crossfade."]}
    args.output.write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "source_start": args.start, "frames": args.end-args.start, "used_cels": len({e["cel"] for e in exposures}), "exposures": len(exposures)}))


if __name__ == "__main__":
    main()
