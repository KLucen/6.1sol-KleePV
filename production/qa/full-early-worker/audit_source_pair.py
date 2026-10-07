"""Full-resolution rigid-aligned source evidence; never transform generated art."""
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
from rigid_source import similarity


def audit(before, current):
    rows = json.loads((ROOT / 'full-pv-progress-manifest.json').read_text(encoding='utf-8'))['cels']
    paths = [ROOT / next(x['source_reference'] for x in rows if x['canonical_source_frame'] == frame) for frame in (before, current)]
    a, b = [cv2.imread(str(path)) for path in paths]
    result = similarity(a, b)
    if result is None:
        raise RuntimeError('Source pair did not align')
    aligned = cv2.warpAffine(a, np.float32(result['matrix']), (1920, 1080), borderMode=cv2.BORDER_REPLICATE)
    diff = np.minimum(cv2.absdiff(aligned, b).astype(np.uint16) * 4, 255).astype(np.uint8)
    ea, eb = [cv2.Canny(image, 80, 160) for image in (aligned, b)]
    overlay = np.full_like(a, 245)
    overlay[ea != 0] = (235, 110, 30)
    overlay[eb != 0] = (30, 80, 235)
    overlay[(ea != 0) & (eb != 0)] = (50, 50, 50)
    canvas = Image.new('RGB', (3840, 2240), '#202024')
    draw = ImageDraw.Draw(canvas)
    for index, (panel, label) in enumerate([(aligned, 'SOURCE BEFORE aligned rigidly'), (b, 'SOURCE CURRENT'), (diff, 'Actual aligned RGB difference x4'), (overlay, 'Aligned contours blue before / red current')]):
        x, y = (index % 2) * 1920, (index // 2) * 1120
        draw.text((x + 15, y + 10), label, fill='white')
        canvas.paste(Image.fromarray(cv2.cvtColor(panel, cv2.COLOR_BGR2RGB)), (x, y + 40))
    output = QA / f'source-audit-f{before:04d}-f{current:04d}.png'
    canvas.save(output)
    if before == 671 and current in (682, 720):
        boxes = [('eyes-bangs', (215, 470, 565, 745)), ('gloves-cuffs', (40, 590, 440, 850)),
                 ('pillow', (30, 580, 790, 910)), ('legs-boots', (760, 430, 1270, 690)),
                 ('coat-gray-paint', (430, 440, 830, 745))]
        crop_canvas = Image.new('RGB', (2560, len(boxes) * 540), '#202024')
        crop_draw = ImageDraw.Draw(crop_canvas)
        for index, (label, box) in enumerate(boxes):
            x0, y0, x1, y1 = box
            for col, (panel, panel_name) in enumerate([(aligned, 'BEFORE aligned'), (b, 'CURRENT'), (diff, 'RGBDIFFx4'), (overlay, 'CONTOURS')]):
                crop = Image.fromarray(cv2.cvtColor(panel[y0:y1, x0:x1], cv2.COLOR_BGR2RGB))
                crop.thumbnail((640, 500))
                x, y = col * 640, index * 540
                crop_draw.text((x + 10, y + 10), label + ' ' + panel_name, fill='white')
                crop_canvas.paste(crop, (x + (640-crop.width)//2, y + 35))
        crop_output = QA / f'source-audit-f{before:04d}-f{current:04d}-local-regions.png'
        crop_canvas.save(crop_output)
        result['enlarged_region_proof'] = str(crop_output)
        gray_box = (475, 485, 665, 625)
        gx0, gy0, gx1, gy1 = gray_box
        gray_canvas = Image.new('RGB', (1520, 600), '#202024')
        gray_draw = ImageDraw.Draw(gray_canvas)
        for col, (panel, name) in enumerate([(aligned, 'BEFORE aligned'), (b, 'CURRENT'), (diff, 'Actual RGBdiff x4'), (overlay, 'Contours')]):
            crop = Image.fromarray(cv2.cvtColor(panel[gy0:gy1, gx0:gx1], cv2.COLOR_BGR2RGB)).resize((380, 280), Image.Resampling.NEAREST)
            gray_draw.text((col * 380 + 10, 10), name, fill='white')
            gray_canvas.paste(crop, (col * 380, 40))
            raw = Image.fromarray(cv2.cvtColor((a if col == 0 else b)[gy0:gy1, gx0:gx1], cv2.COLOR_BGR2RGB)).resize((380, 280), Image.Resampling.NEAREST)
            if col < 2:
                gray_draw.text((col * 380 + 10, 325), 'UNALIGNED original ' + name, fill='white')
                gray_canvas.paste(raw, (col * 380, 355))
        gray_output = QA / f'source-audit-f{before:04d}-f{current:04d}-gray-paint.png'
        gray_canvas.save(gray_output)
        result['gray_paint_proof'] = str(gray_output)
    result['source_paths'] = [str(path) for path in paths]
    result['proof'] = str(output)
    result['manual_disposition'] = 'pending_visual_review_not_automatic_alias'
    output.with_suffix('.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('before', type=int)
    parser.add_argument('current', type=int)
    args = parser.parse_args()
    audit(args.before, args.current)
