"""Additional source/generated spatial evidence, not animation or artwork."""

from hashlib import sha256
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta
from prepare_missing_refs import local_board, TRANSITION_BOXES

FACE_OCCLUSION_BOXES = [
    ("rear-head-occluded-by-foreground", (850, 180, 1210, 580)),
    ("rear-head-left-hair-collar-sliver", (860, 240, 1040, 580)),
    ("raised-hand-cuff", (680, 70, 960, 400)),
    ("rear-torso-lower-hand", (780, 430, 1360, 790)),
    ("foreground-face-hat", (900, 0, 1920, 1080)),
]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    queue = json.loads((QA / "missing-source-reference-queue.json").read_text(encoding="utf-8"))
    actuals = queue["source_decoded_frames"]
    source_outputs = []
    for a, b, boxes in ((889, 891, FACE_OCCLUSION_BOXES), (907, 908, TRANSITION_BOXES)):
        paths = [Path(actuals[str(f)]["path"]) for f in (a, b)]
        for f, path in zip((a, b), paths):
            if digest(path) != actuals[str(f)]["png_sha256"]:
                raise RuntimeError(f"Actual sequential source evidence changed: {f}")
        output = QA / f"f{a:04d}-f{b:04d}-source-extra-ab-rgb-contours.png"
        make_delta(*paths, output)
        board = QA / f"f{a:04d}-f{b:04d}-source-extra-local-ab.png"
        local = local_board(*paths, board, boxes)
        crops = []
        for f, path in zip((a, b), paths):
            source = Image.open(path).convert("RGB")
            for role, box in boxes:
                crop = QA / f"f{f:04d}-extra-{role}.png"
                source.crop(box).save(crop)
                crops.append({"frame": f, "role": role, "xyxy": list(box), "path": str(crop), "sha256": digest(crop)})
        source_outputs.append({"frames": [a, b], "source_paths": [str(p) for p in paths], "delta": str(output), "delta_sha256": digest(output), "local": local, "crops": crops})
    gen_paths = [ROOT / "generated" / f"fast-fullpv-dance-f{f:04d}-v1.png" for f in (907, 908)]
    generated_delta = QA / "f0907-f0908-generated-ab-rgb-contours.png"
    make_delta(*gen_paths, generated_delta)
    board = Image.open(generated_delta).convert("RGB")
    draw = ImageDraw.Draw(board)
    width, _ = Image.open(gen_paths[0]).size
    draw.rectangle((0, 0, width * 2, 39), fill="#202024")
    draw.text((15, 12), "BEFORE GENERATED DRAFT f907", fill="white")
    draw.text((width + 15, 12), "CURRENT GENERATED DRAFT f908", fill="white")
    board.save(generated_delta)
    delta_record = json.loads(generated_delta.with_suffix(".json").read_text(encoding="utf-8"))
    delta_record["role"] = "Actual generated-draft spatial differences only; not original source, artwork editing or motion synthesis"
    generated_delta.with_suffix(".json").write_text(json.dumps(delta_record, indent=2), encoding="utf-8")
    result = {
        "scope": "Source-only 889-to-891 occlusion evidence and source/artwork 907-to-908 spatial changes",
        "source_decode_provenance": "prepare_missing_refs.py sequentially decoded the original MP4 from frame 0 to 911 inclusive; these unchanged files were not seek approximations",
        "actual_source_evidence": "missing-source-reference-queue.json#source_decoded_frames",
        "queue_sha256": digest(QA / "missing-source-reference-queue.json"),
        "source_pairs": source_outputs,
        "generated_pair": {"frames": [907, 908], "paths": [str(p) for p in gen_paths], "hashes": [digest(p) for p in gen_paths], "delta": str(generated_delta), "delta_sha256": digest(generated_delta), "same_native_size": list(Image.open(gen_paths[0]).size)},
        "actual_speed_acceptance": False, "artwork_modified": False,
        "global_selection_changed": False, "aliases_created": False,
    }
    (QA / "extra-neighbor-spatial-evidence.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"evidence": str(QA / "extra-neighbor-spatial-evidence.json")}))


if __name__ == "__main__":
    main()
