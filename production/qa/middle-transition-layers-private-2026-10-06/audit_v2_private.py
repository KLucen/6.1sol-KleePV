"""Reuse the frozen 24-frame oracle but retain all failed v1 evidence."""

from pathlib import Path
import shutil

import audit_private as audit
import middle_transition_layers_v2_private as layer

HERE = Path(__file__).resolve().parent
OUT = HERE / "v2-observed-cool-fill"
if OUT.exists():
    raise FileExistsError("Retain previous v2 evidence")
OUT.mkdir()
shutil.copytree(HERE / "source", OUT / "source")
audit.HERE = OUT
audit.layer = layer
audit.main()
