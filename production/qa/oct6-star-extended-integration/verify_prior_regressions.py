"""Reuse the frozen 206-frame oracle without overwriting its evidence."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = ROOT / "qa/star-final-integration-2026-10-05/verify_shared_raw_regressions.py"
spec = importlib.util.spec_from_file_location("_prior_star_regression", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.OUT = HERE

if __name__ == "__main__":
    module.main()
