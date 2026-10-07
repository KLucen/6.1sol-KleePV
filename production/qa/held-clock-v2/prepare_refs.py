"""Prepare unmodified source detail crops and analytical delta boards."""

import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from delta_reference import make_delta
from compose import read_image

FRAMES = [79,83,87,91,95,99,117]
mapping = json.loads((ROOT/'source_map.json').read_text(encoding='utf-8'))
candidates = {c['frame']:c for c in mapping['candidates']}
previous = 75
for frame in FRAMES:
    original = read_image(ROOT/candidates[frame]['reference'])
    bounds = (1150,180,1500,475) if frame == 79 else (1210,175,1540,455)
    x0,y0,x1,y1 = bounds
    crop = cv2.resize(original[y0:y1,x0:x1],None,fx=3,fy=3,interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(str(OUT/f'f{frame:04d}-source-clock-hands-face.png'),crop)
    make_delta(ROOT/candidates[previous]['reference'],ROOT/candidates[frame]['reference'],OUT/f'f{previous:04d}-f{frame:04d}-source-delta.png')
    previous = frame
costume = read_image(ROOT/'generated/fine-f0121-costume-repair.png')
cv2.imwrite(str(OUT/'identity-collar-and-waist.png'),costume[370:785,1200:1660])
collar = read_image(ROOT/'generated/fine-f0091-v2.png')
cv2.imwrite(str(OUT/'identity-collar-only-f0091.png'),collar[402:555,1325:1460])
print(json.dumps({'frames':FRAMES,'output':str(OUT)},indent=2))
