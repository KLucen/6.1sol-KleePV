"""Exact existing late-pose preparation/archive workflow in a new queue."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("late_next_private", ROOT / "qa/late-oct6-worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
worker.OUT = Path(__file__).resolve().parent
worker.FRAMES = [2911, 2916, 2921, 2926, 2932, 2938]

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare", "save", "seal"])
    p.add_argument("--frame", type=int)
    p.add_argument("--version", type=int, default=1)
    p.add_argument("--origin")
    p.add_argument("--notes")
    p.add_argument("--unselected", action="store_true")
    args = p.parse_args()
    if args.mode == "prepare":
        worker.prepare()
    elif args.mode == "save":
        worker.save(args.frame, args.origin, args.notes, args.version, args.unselected)
    else:
        worker.seal()
