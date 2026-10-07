"""Decode every source frame, retain coherent character changes, and expose review evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".python_deps"))
import cv2
import numpy as np
from PIL import Image, ImageDraw


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def foreground(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    blue_field = (h >= 85) & (h <= 151) & (s >= 145)
    cyan_scene = float(blue_field.mean()) > 0.10
    if cyan_scene:
        violet = (h >= 112) & (h <= 151) & (s >= 65) & (v >= 207)
        white = (s <= 25) & (v >= 201)
    else:
        # Lavender-to-white star antialiasing changes saturation, not the background hue.
        violet = (h >= 112) & (h <= 151) & (v >= 207)
        white = ((s <= 25) & (v >= 201)) | ((s <= 55) & (v >= 220))
    text_star = ((h >= 20) & (h <= 45) & (v >= 150)) | white
    mask = (~(violet | blue_field | text_star)).astype(np.uint8)
    # Isolated codec noise must not become a character ROI; small coherent details survive.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    keep = np.zeros(count, np.uint8)
    keep[np.flatnonzero(stats[:, cv2.CC_STAT_AREA] >= 60)] = 1
    keep[0] = 0
    return keep[labels]


def difference(a, b, ma, mb):
    active = cv2.dilate(ma | mb, np.ones((5, 5), np.uint8))
    delta = cv2.absdiff(a, b).max(axis=2)
    changed = ((delta >= 28) & (active != 0)).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(changed, 8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    coherent = int(areas[areas >= 8].sum())
    largest = int(areas.max(initial=0))
    return {"pixels": int(changed.sum()), "coherent_pixels": coherent, "largest_region": largest,
            "masked_mean_delta": float(delta[active != 0].mean()) if active.any() else 0.0}


def signature(image, mask):
    visible = image.copy()
    visible[mask == 0] = (237, 135, 148)
    return cv2.resize(visible, (160, 90), interpolation=cv2.INTER_AREA).astype(np.int16)


def sheet(items, output, columns=6, width=320):
    height = int(width * 1080 / 1920) + 36
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * width, rows * height), "#202024")
    draw = ImageDraw.Draw(canvas)
    for i, item in enumerate(items):
        im = Image.open(ROOT / item["reference"]).convert("RGB")
        im.thumbnail((width, height - 36), Image.Resampling.LANCZOS)
        x, y = (i % columns) * width, (i // columns) * height
        canvas.paste(im, (x, y))
        draw.text((x + 5, y + height - 33), f'{item["id"]}  f{item["frame"]}  {item["pts"]:.3f}s', fill="white")
        draw.text((x + 5, y + height - 17), f'{item.get("family", "?")}   {item.get("review", "candidate")}', fill="#ccc")
    canvas.save(output, quality=94)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    source = args.source or next(ROOT.parent.glob("*.mp4"))
    ROOT.mkdir(exist_ok=True)
    refs = ROOT / "source_refs"
    refs.mkdir(exist_ok=True)
    contacts = ROOT / "source_contacts"
    contacts.mkdir(exist_ok=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-show_frames", "-select_streams", "v:0", "-of", "json", str(source)], capture_output=True, check=True)
    pdata = json.loads(probe.stdout)
    pts = [float(f["best_effort_timestamp_time"]) for f in pdata["frames"]]
    durations = [float(f.get("pkt_duration_time", 0)) for f in pdata["frames"]]
    raw_meta = {"source": str(source), "sha256": hashlib.file_digest(source.open("rb"), "sha256").hexdigest(),
                "streams": pdata["streams"], "format": pdata["format"], "pts": pts, "frame_durations": durations,
                "interval_convention": "0-based [start,end)", "pts_cfr_test": {"min_delta": float(np.diff(pts).min()), "max_delta": float(np.diff(pts).max())}}
    dump(ROOT / "source_meta.json", raw_meta)
    cap = cv2.VideoCapture(str(source))
    previous = previous_mask = None
    candidates, metrics, frame_map = [], [], []
    current = None
    frame = 0
    while True:
        ok, image = cap.read()
        if not ok:
            break
        mask = foreground(image)
        metric = difference(previous, image, previous_mask, mask) if previous is not None else {"pixels": 0, "coherent_pixels": 0, "largest_region": 0, "masked_mean_delta": 0}
        metric.update(frame=frame, pts=pts[frame], foreground_pixels=int(mask.sum()))
        changed = frame == 0 or metric["coherent_pixels"] >= 90 or metric["largest_region"] >= 30
        if changed:
            if current is not None:
                current["end"] = frame
                current["end_pts"] = pts[frame]
            cid = f"src-{len(candidates):04d}"
            path = refs / f"{cid}-f{frame:04d}.png"
            cv2.imwrite(str(path), image)
            current = {"id": cid, "frame": frame, "start": frame, "end": None, "pts": pts[frame], "end_pts": None,
                       "reference": str(path.relative_to(ROOT)).replace("\\", "/"), "change": metric, "review": "candidate"}
            candidates.append(current)
        frame_map.append(current["id"])
        metrics.append(metric)
        previous, previous_mask = image, mask
        frame += 1
        if frame % 240 == 0:
            print(f"decoded {frame}/{len(pts)} frames, {len(candidates)} coherent-change candidates", flush=True)
    cap.release()
    current["end"] = frame
    current["end_pts"] = pts[-1] + durations[-1]
    dump(ROOT / "source_metrics.json", metrics)
    dump(ROOT / "source_map.json", {"version": 1, "source": str(source), "frames": frame, "mode": "strict_source_candidate", "thresholds": {"delta": 28, "coherent_pixels": 90, "largest_region": 30}, "candidates": candidates, "frame_to_candidate": frame_map})
    for page, start in enumerate(range(0, len(candidates), 72)):
        sheet(candidates[start:start+72], contacts / f"candidates-{page:02d}.jpg")
    print(f"COMPLETE {frame} frames; {len(candidates)} candidate source drawings", flush=True)


if __name__ == "__main__":
    main()
