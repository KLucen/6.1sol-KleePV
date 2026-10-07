"""Original-source-only repeat evidence for f1123..1128."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def main():
    path = ROOT / "qa/star-microcel-audit-2026-10-05/prepare_evidence.py"
    spec = importlib.util.spec_from_file_location("source_microcel_evidence", path)
    evidence = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evidence)
    evidence.OUT = OUT
    evidence.PAIRS = [(1123, 1125)]
    evidence.WINDOWS = [(1123, 1129)]
    evidence.main()
    source_map = json.loads((ROOT / "source_map.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "full-pv-progress-manifest.json").read_text(encoding="utf-8"))
    old = json.loads((ROOT / "qa/star-microcel-audit-2026-10-05/source-alias-proposal.json").read_text(encoding="utf-8"))
    candidates = {row["frame"]: row for row in source_map["candidates"]}
    cels = {row["canonical_source_frame"]: row for row in manifest["cels"]}
    checks = []
    for source, target in [(1100, 1097), (1117, 1113), (1125, 1123)]:
        previous = next((row for row in old["proposals"] if row["source_frame"] == source), None)
        checks.append({
            "source_frame": source,
            "target_frame": target,
            "source_candidate": candidates[source],
            "target_candidate": candidates[target],
            "source_cel": cels[source]["cel"],
            "target_cel": cels[target]["cel"],
            "source_exposures": cels[source]["source_exposures"],
            "target_exposures": cels[target]["source_exposures"],
            "previous_proposal_metadata_matches": None if previous is None else (
                previous["verified_target_frame"] == target
                and previous["source_cel"] == cels[source]["cel"]
                and previous["verified_target_cel"] == cels[target]["cel"]
                and previous["source_exposures_unchanged"] == cels[source]["source_exposures"]
                and previous["target_exposures_unchanged"] == cels[target]["source_exposures"]
            ),
            "metadata_check_only_not_new_semantic_approval": source != 1125,
        })
    (OUT / "candidate-and-exposure-checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
