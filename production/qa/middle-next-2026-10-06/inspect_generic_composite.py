"""Preserve generic compositor baselines before any shot-specific repair."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from compose import compose, read_image

cv2.setNumThreads(2)
timeline = json.loads((ROOT / "timeline-middle-2121-2145-oct6-draft-v1.json").read_text())
out = HERE / "generic-baseline"
if out.exists():
    raise FileExistsError("Preserve the previous baseline")
out.mkdir()
cap = cv2.VideoCapture(timeline["source"])
exposures = timeline["output_exposures"]
records = []
assets = {}
for frame in range(2145):
    ok, source = cap.read()
    if not ok:
        raise RuntimeError(f"Source decode failed f{frame}")
    if frame < 2121:
        continue
    e = next(e for e in exposures if e["start"] <= frame < e["end"])
    a = timeline["assets"][e["cel"]]
    if e["cel"] not in assets:
        assets[e["cel"]] = (read_image(ROOT / a["source_reference"]), read_image(ROOT / a["path"]))
    reference, generated = assets[e["cel"]]
    composite, _, masks = compose(source, reference, generated, e["source_matrix"],
                                   a["source_frame"], Path(a["path"]).name, frame)
    cv2.imwrite(str(out / f"f{frame}-composite.png"), composite)
    cv2.imwrite(str(out / f"f{frame}-caption-native.png"), np.concatenate((source[945:1050, 650:1270], composite[945:1050, 650:1270])))
    if frame == e["start"]:
        cv2.imwrite(str(out / f"f{frame}-masks.png"), masks)
    records.append({"frame": frame, "asset": a["path"], "source_sha256_bgr": sha256(source.tobytes()).hexdigest(),
                    "composite_sha256_bgr": sha256(composite.tobytes()).hexdigest(), "accepted": False})
cap.release()
(out / "report.json").write_text(json.dumps({"frames": records, "scope": "generic baseline; no ownership or artistic approval"}, indent=2))
print(json.dumps({"frames": len(records), "output": str(out)}))
