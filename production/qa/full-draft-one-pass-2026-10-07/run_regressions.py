"""Run existing focused tests without changing production selections or artwork."""

import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
MODULES = [
    "test_render_timing",
    "test_audio_cut_quantization",
    "test_title_layers",
    "test_star_extended_layers",
    "test_middle_transition_layers",
    "test_caption_composite",
    "test_caption_diagnostics",
    "test_clear_dance_captions",
    "test_dance_caption_layers",
    "test_dance_caption_integration",
    "test_dance_caption_transition",
    "test_raised_caption_layers",
]


def main():
    cv2.setNumThreads(2)
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromNames(MODULES)
        requested = suite.countTestCases()
        result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
    output = captured.getvalue()
    report = {
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.perf_counter() - clock,
        "python": sys.executable,
        "python_version": sys.version,
        "opencv_version": cv2.__version__,
        "opencv_threads": cv2.getNumThreads(),
        "modules": MODULES,
        "requested_tests": requested,
        "tests_run": result.testsRun,
        "failures_count": len(result.failures),
        "errors_count": len(result.errors),
        "skipped_count": len(result.skipped),
        "expected_failures_count": len(result.expectedFailures),
        "unexpected_successes_count": len(result.unexpectedSuccesses),
        "successful": result.wasSuccessful(),
        "failures": [{"test": test.id(), "traceback": trace} for test, trace in result.failures],
        "errors": [{"test": test.id(), "traceback": trace} for test, trace in result.errors],
        "stdout": output,
        "shared_selections_changed": False,
        "artistic_acceptance": "not_performed",
    }
    (HERE / "regression-test-run.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (HERE / "regression-test-stdout.txt").write_text(output, encoding="utf-8")
    print(output, end="")
    print(json.dumps({key: report[key] for key in (
        "tests_run", "failures_count", "errors_count", "skipped_count", "successful", "elapsed_seconds"
    )}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
