"""Exact inherited oracle with the known v2 cheek hole evidence retained."""

from pathlib import Path
import shutil

import audit_private as audit
import middle_transition_layers_v3_private as layer

HERE = Path(__file__).resolve().parent
OUT = HERE / "v3-enclosed-ink-fill"
if OUT.exists():
    raise FileExistsError("Retain previous v3 evidence")
OUT.mkdir()
shutil.copytree(HERE / "source", OUT / "source")
audit.HERE = OUT
audit.layer = layer
audit.main()
