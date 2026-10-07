"""Private missing-cel queue and source-only QA evidence for the early range."""
from pathlib import Path
import argparse
import json
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from delta_reference import make_delta


def manifest_rows():
    return json.loads((ROOT / 'full-pv-progress-manifest.json').read_text(encoding='utf-8'))['cels']


def queue():
    rows = manifest_rows()
    owned = [r for r in rows if 433 <= r['canonical_source_frame'] <= 1295]
    pending = [r for r in owned if not r.get('selected_asset')]
    result = {
        'owner': 'full_early_resume', 'accepted': False,
        'shared_selection_modified': False,
        'assigned_cels': len(owned), 'missing_at_start': len(pending),
        'first_missing': pending[0]['canonical_source_frame'] if pending else None,
        'last_missing': pending[-1]['canonical_source_frame'] if pending else None,
        'source_manifest_snapshot': json.loads((ROOT / 'full-pv-progress-manifest.json').read_text(encoding='utf-8'))['snapshot_utc'],
        'queue': [{
            'frame': r['canonical_source_frame'], 'cel': r['cel'],
            'source_candidate': r['source_candidate'],
            'source_reference': r['source_reference'], 'family': r['canonical_family'],
            'status': 'pending', 'accepted': False
        } for r in pending]
    }
    (QA / 'full-resume-queue.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'assigned': len(owned), 'missing': len(pending), 'frames': [r['frame'] for r in result['queue']]}))


def prepare(frame):
    rows = manifest_rows()
    index = next(i for i, r in enumerate(rows) if r['canonical_source_frame'] == frame)
    current, before = rows[index], rows[index - 1]
    source = ROOT / current['source_reference']
    prior = ROOT / before['source_reference']
    delta = QA / f'resume-f{frame:04d}-source-difference.png'
    make_delta(prior, source, delta)
    a, b = [np.array(Image.open(path).convert('RGB')) for path in (prior, source)]
    diff = np.minimum(np.abs(a.astype(np.int16) - b.astype(np.int16)) * 4, 255).astype(np.uint8)
    edges = [cv2.Canny(image, 80, 160) for image in (a, b)]
    overlay = np.full_like(a, 245)
    overlay[edges[0] != 0] = (30, 110, 235)
    overlay[edges[1] != 0] = (235, 80, 30)
    overlay[(edges[0] != 0) & (edges[1] != 0)] = (50, 50, 50)
    boxes = [('head-eyes', (350, 80, 1550, 750)), ('hands-cuffs-body', (200, 400, 1750, 1080))]
    contact = Image.new('RGB', (2400, len(boxes) * 600), '#202024')
    draw = ImageDraw.Draw(contact)
    for row, (label, box) in enumerate(boxes):
        for col, (array, name) in enumerate([(a, 'BEFORE'), (b, 'CURRENT'), (diff, 'RGB x4'), (overlay, 'CONTOURS')]):
            crop = Image.fromarray(array).crop(box)
            crop.thumbnail((600, 550))
            x, y = col * 600, row * 600
            draw.text((x + 8, y + 8), label + ' ' + name, fill='white')
            contact.paste(crop, (x + (600 - crop.width) // 2, y + 35))
    local = QA / f'resume-f{frame:04d}-source-local.png'
    contact.save(local)
    head = QA / f'resume-f{frame:04d}-source-head.png'
    Image.fromarray(b).crop(boxes[0][1]).save(head)
    print(json.dumps({'frame': frame, 'before': before['canonical_source_frame'], 'source': str(source), 'delta': str(delta), 'local': str(local), 'head': str(head)}))


def contact(frame, asset):
    rows = manifest_rows()
    index = next(i for i, r in enumerate(rows) if r['canonical_source_frame'] == frame)
    current, before = rows[index], rows[index - 1]
    images = [Image.open(ROOT / r['source_reference']).convert('RGB') for r in (before, current)]
    generated = Image.open(asset).convert('RGB').resize(images[0].size)
    ledger_path = QA / 'full-resume-selections-proposed.json'
    ledger = json.loads(ledger_path.read_text(encoding='utf-8')) if ledger_path.exists() else {'selections': []}
    previous_asset = next((ROOT / r['path'] for r in reversed(ledger['selections']) if r['source_frame'] == before['canonical_source_frame']), None)
    if previous_asset is None and before.get('selected_asset'):
        previous_asset = ROOT / before['selected_asset']['path']
    previous_generated = Image.open(previous_asset).convert('RGB').resize(images[0].size) if previous_asset else Image.new('RGB', images[0].size, '#202024')
    panels = images + [previous_generated, generated]
    diff = np.minimum(np.abs(np.array(images[1]).astype(np.int16) - np.array(generated).astype(np.int16)) * 4, 255).astype(np.uint8)
    whole_diff = QA / (Path(asset).stem + '-whole-source-draft-difference.png')
    Image.fromarray(diff).save(whole_diff)
    for pair in (images, [previous_generated, generated]):
        edges = [cv2.Canny(np.array(image), 80, 160) for image in pair]
        overlay = np.full_like(np.array(images[0]), 245)
        overlay[edges[0] != 0] = (30, 110, 235)
        overlay[edges[1] != 0] = (235, 80, 30)
        overlay[(edges[0] != 0) & (edges[1] != 0)] = (50, 50, 50)
        panels.append(Image.fromarray(overlay))
    canvas = Image.new('RGB', (1920, 1740), '#202024')
    draw = ImageDraw.Draw(canvas)
    labels = [f'SOURCE BEFORE f{before["canonical_source_frame"]}', f'SOURCE CURRENT f{frame}', f'KLEE BEFORE f{before["canonical_source_frame"]}', 'CURRENT KLEE DRAFT', 'SOURCE CONTOURS blue before / red current', 'KLEE CONTOURS blue before / red current']
    for i, panel in enumerate(panels):
        x, y = (i % 2) * 960, (i // 2) * 580
        draw.text((x + 8, y + 8), labels[i], fill='white')
        canvas.paste(panel.resize((960, 540)), (x, y + 30))
    output = QA / (Path(asset).stem + '-source-static-contact.jpg')
    canvas.save(output, quality=94)
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['queue', 'prepare', 'contact'])
    parser.add_argument('--frame', type=int)
    parser.add_argument('--asset', type=Path)
    args = parser.parse_args()
    if args.mode == 'queue':
        queue()
    elif args.mode == 'prepare':
        prepare(args.frame)
    else:
        contact(args.frame, args.asset)
