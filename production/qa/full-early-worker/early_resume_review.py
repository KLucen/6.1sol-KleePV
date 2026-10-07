"""Private source/generated contact and contour review; no timeline mutation."""
from pathlib import Path
import argparse
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent


def review(job_name, before):
    job_path = ROOT / 'jobs' / (job_name + '.json')
    job = json.loads(job_path.read_text(encoding='utf-8'))
    frame = job.get('source_frame', job.get('frame'))
    rows = json.loads((ROOT / 'full-pv-progress-manifest.json').read_text(encoding='utf-8'))['cels']
    row = next(x for x in rows if x['canonical_source_frame'] == frame)
    prior = next(x for x in rows if x['canonical_source_frame'] == before)
    asset = ROOT / 'generated' / (job_name + '.png')
    with Image.open(asset) as image:
        image.verify()
    proposals_path = QA / 'resume-selections-proposed.json'
    proposals = json.loads(proposals_path.read_text(encoding='utf-8')) if proposals_path.exists() else {
        'owner': 'early_resume', 'accepted': False, 'shared_selection_modified': False,
        'review_scope': 'Per-cel static source and adjacent contour review only; actual speed review pending.', 'selections': []}
    prior_selection = next((x['path'] for x in reversed(proposals['selections']) if x['source_frame'] == before), None)
    alias_path = QA / 'source-aliases-proposed.json'
    if prior_selection is None and alias_path.exists():
        alias_data = json.loads(alias_path.read_text(encoding='utf-8'))
        alias = next((x for x in alias_data['aliases'] if x['source_frame'] == before), None)
        if alias:
            prior_selection = next((x['path'] for x in reversed(proposals['selections']) if x['source_frame'] == alias['verified_target_frame']), None)
    if prior_selection is None and prior.get('selected_asset'):
        prior_selection = prior['selected_asset']['path']
    sources = [ROOT / prior['source_reference'], ROOT / row['source_reference']]
    panels = [Image.open(p).convert('RGB').resize((960, 540)) for p in sources]
    panels += [Image.open(ROOT / prior_selection).convert('RGB').resize((960, 540)) if prior_selection else Image.new('RGB', (960, 540), '#202024'), Image.open(asset).convert('RGB').resize((960, 540))]
    source_arrays = [np.array(p) for p in panels[:2]]
    new_arrays = [np.array(p) for p in panels[2:]]
    overlays = []
    for arrays in (source_arrays, new_arrays):
        ea, eb = [cv2.Canny(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), 80, 160) for a in arrays]
        overlay = np.full_like(arrays[0], 245)
        overlay[ea != 0] = (30, 110, 235)
        overlay[eb != 0] = (235, 80, 30)
        overlay[(ea != 0) & (eb != 0)] = (50, 50, 50)
        overlays.append(Image.fromarray(overlay))
    canvas = Image.new('RGB', (1920, 1728), '#202024')
    draw = ImageDraw.Draw(canvas)
    labels = [f'SOURCE BEFORE f{before}', f'SOURCE CURRENT f{frame}',
              f'KLEE BEFORE f{before}', f'KLEE CURRENT f{frame}',
              'SOURCE contours blue before / red current', 'KLEE contours blue before / red current']
    for index, panel in enumerate(panels + overlays):
        x, y = (index % 2) * 960, (index // 2) * 576
        draw.text((x + 10, y + 10), labels[index], fill='white')
        canvas.paste(panel, (x, y + 30))
    contact_path = QA / (job_name + '-static-contact.jpg')
    canvas.save(contact_path, quality=94)
    job.update({'job_id': job_name, 'source_frame': frame, 'source_candidate': row['source_candidate'],
                'canonical_cel': row['cel'], 'family': row['canonical_family'],
                'references': job.get('references', job.get('refs', [])), 'accepted': False,
                'static_contact_path': str(contact_path), 'continuity_status': 'static_reviewed_temporal_pending'})
    job_path.write_text(json.dumps(job, indent=2), encoding='utf-8')
    proposal = {'source_frame': frame, 'path': 'generated/' + asset.name,
                'review': job['review'], 'known_issues': job.get('known_issues', []),
                'static_contact_path': str(contact_path), 'accepted': False}
    proposals['selections'] = [x for x in proposals['selections'] if x['source_frame'] != frame] + [proposal]
    proposals_path.write_text(json.dumps(proposals, indent=2), encoding='utf-8')
    print(contact_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('job')
    parser.add_argument('before', type=int)
    args = parser.parse_args()
    review(args.job, args.before)
