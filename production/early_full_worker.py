"""Preparation and provenance for independent model-drawn early PV cels."""
from pathlib import Path
import argparse
import json
from PIL import Image, ImageDraw
from delta_reference import make_delta

ROOT = Path(__file__).resolve().parent


def rows(start, end):
    data = json.loads((ROOT / 'full-pv-progress-manifest.json').read_text(encoding='utf-8'))
    return [x for x in data['cels'] if start <= x['canonical_source_frame'] <= end]


def contact(start, end, name):
    items = rows(start, end)
    for offset in range(0, len(items), 6):
        batch = items[offset:offset + 6]
        canvas = Image.new('RGB', (1280, len(batch) * 384), '#242427')
        draw = ImageDraw.Draw(canvas)
        for i, row in enumerate(batch):
            f = row['canonical_source_frame']
            draw.text((8, i * 384 + 8), f'f{f:04d}  {row["cel"]}  {row["canonical_family"]}', fill='white')
            source = ROOT / row['source_reference']
            generated = ROOT / 'generated' / f'fine-f{f:04d}.png'
            if not generated.exists() and row.get('selected_asset'):
                generated = ROOT / row['selected_asset']['path']
            canvas.paste(Image.open(source).convert('RGB').resize((640, 360)), (0, i * 384 + 24))
            if generated.exists():
                canvas.paste(Image.open(generated).convert('RGB').resize((640, 360)), (640, i * 384 + 24))
        path = ROOT / 'qa' / 'full-early-worker' / f'{name}-{offset//6+1:02d}.jpg'
        path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(path, quality=94)
        print(path)


def prepare(frame, before):
    current = rows(frame, frame)[0]
    previous = rows(before, before)[0]
    out = ROOT / 'diffs' / f'early-full-f{frame:04d}.png'
    make_delta(ROOT / previous['source_reference'], ROOT / current['source_reference'], out)
    print(json.dumps(current, ensure_ascii=True))


def crops(frame, anchor):
    row = rows(frame, frame)[0]
    folder = ROOT / 'qa' / 'full-early-worker'
    folder.mkdir(parents=True, exist_ok=True)
    source = Image.open(ROOT / row['source_reference']).convert('RGB')
    for label, box in [('source-face', (245, 395, 620, 710)), ('source-legs', (720, 280, 1240, 660))]:
        output = folder / f'f{frame:04d}-{label}.png'
        source.crop(box).save(output)
        print(output)
    image = Image.open(ROOT / 'generated' / anchor).convert('RGB').resize((1920, 1080))
    for label, box in [('prone-head-continuity', (235, 365, 680, 730)), ('prone-garment-continuity', (525, 470, 950, 735))]:
        output = folder / f'{label}.png'
        image.crop(box).save(output)
        print(output)


def job(frame, name, prompt, refs, output):
    row = rows(frame, frame)[0]
    target = ROOT / 'generated' / f'{name}.png'
    if target.exists():
        raise FileExistsError(target)
    from shutil import copy2
    copy2(output, target)
    record = {'job_id': name, 'source_frame': frame, 'source_candidate': row['source_candidate'],
              'canonical_cel': row['cel'], 'family': row['canonical_family'], 'tool': 'builtin imagegen',
              'references': refs, 'prompt': prompt, 'output': f'../generated/{name}.png',
              'status': 'generated_draft', 'accepted': False, 'continuity_status': 'pending_static_and_sequence_review',
              'caption_cleanup_required': False, 'original_tool_output': output}
    (ROOT / 'jobs' / f'{name}.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(target)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=['contact', 'prepare', 'crops'])
    p.add_argument('a', type=int)
    p.add_argument('b', type=int)
    p.add_argument('--name', default='contact')
    args = p.parse_args()
    if args.mode == 'contact':
        contact(args.a, args.b, args.name)
    elif args.mode == 'prepare':
        prepare(args.a, args.b)
    else:
        crops(args.a, args.name)
