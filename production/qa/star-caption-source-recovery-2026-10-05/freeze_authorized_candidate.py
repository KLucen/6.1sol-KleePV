"""Record immutable post-static evidence; this is not a pre-render freeze."""

import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target=OUT/"authorized-candidate-post-static-freeze.json"
    if target.exists():
        raise FileExistsError("Do not overwrite the sealed static candidate")
    record=json.loads((OUT/"authorized-private-35frame-report.json").read_text())
    files=[OUT/name for name in (
        "alternate_phase2_layer.py","authorized_star_caption_candidate.py",
        "authorized-alternate-japanese-f3402.npz",
        "authorized-alternate-glyph-provenance.json",
        "authorized-private-35frame-report.json","static-review.md",
        "integration-proposal.md","build_authorized_alternate_glyphs.py",
        "verify_authorized_caption_candidate.py",
        "source-repeat-candidates.json","same-caption-drawing-candidates.json")]
    files.extend(OUT/f"f{frame:04d}-authorized-private-compose.png" for frame in range(1008,1043))
    files.extend(OUT/f"f{frame:04d}-authorized-native-caption-pair.png" for frame in range(1008,1043))
    files.extend(ROOT/path for group in record["pages"].values() for path in group)
    files.append(ROOT/"source_refs/src-1905-f3402.png")
    freeze={"accepted":False,"stage":"after_private_raw_render_and_static_review",
            "not_pre_render_freeze":True,"interval":[1008,1043],
            "authorized_alternate_interval":[1037,1043],
            "actual_speed_or_encoded_acceptance":False,
            "f1037_pure_builder_refactor_verified_identical_bgr":True,
            "files":[{"path":str(path.relative_to(ROOT)),"bytes":path.stat().st_size,
                      "sha256":sha(path)} for path in files],
            "historical_shared_files_at_35frame_verification":record["shared_sha256"]}
    target.write_text(json.dumps(freeze,indent=2),encoding="utf-8")
    print(json.dumps({"sealed_files":len(files),"freeze":str(target),
                      "freeze_sha256":sha(target),
                      "npz_sha256":sha(OUT/"authorized-alternate-japanese-f3402.npz")}))


if __name__=="__main__":
    main()
