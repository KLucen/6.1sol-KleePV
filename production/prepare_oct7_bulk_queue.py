"""Freeze missing-cel ownership for the user-requested one-pass full draft."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "qa/full-draft-one-pass-2026-10-07"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "ownership-queue.json"
    if path.exists():
        raise FileExistsError("Resume frozen ownership; never recreate it")
    manifest_path = ROOT / "full-pv-progress-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing = sorted((row for row in manifest["cels"] if row["selected_asset"] is None),
                     key=lambda row: row["canonical_source_frame"])
    assert len(missing) == 195
    groups = {
        "middle": [r for r in missing if r["canonical_source_frame"] < 2400],
        "late_action": [r for r in missing if 2400 <= r["canonical_source_frame"] < 3267],
        "ending": [r for r in missing if r["canonical_source_frame"] >= 3267],
    }
    assigned = [r["cel"] for rows in groups.values() for r in rows]
    assert len(assigned) == len(set(assigned)) == len(missing)
    snapshot = {
        "date": "2026-10-07", "policy": "all_missing_drafts_once_then_full_video_user_feedback",
        "mode": "strict_source", "accepted": False,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "selection_sha256_at_freeze": hashlib.sha256((ROOT / "asset_selections.json").read_bytes()).hexdigest(),
        "baseline_summary": manifest["summary"], "missing_count": len(missing),
        "owners": {owner: {"count": len(rows), "rows": rows} for owner, rows in groups.items()},
        "constraints": ["one builtin generated candidate per missing true cel", "no local artistic repairs",
                        "no short preview exports", "do not change shared selections from workers",
                        "keep actual source exposure and captions; no held-pose padding"],
    }
    path.write_text(json.dumps(snapshot, ensure_ascii=True, indent=2), encoding="utf-8")
    for owner, rows in groups.items():
        private = ROOT / f"qa/oct7-bulk-{owner}"
        private.mkdir(parents=True, exist_ok=True)
        (private / "source-evidence-queue.json").write_text(
            json.dumps({"owner": owner, "accepted": False, "queue": rows}, indent=2), encoding="utf-8")
    print(json.dumps({"queue": str(path), "owners": {k: len(v) for k, v in groups.items()}}))


if __name__ == "__main__":
    main()
