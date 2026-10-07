"""Private, unaccepted alternate real-source glyph repair for f1037..1042.

The human authorized legible same-word rebuilding with minor stroke changes.
No shared compositor, character PNG, selection, or source exposure is edited.
"""

from functools import lru_cache
from pathlib import Path
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
import star_gestures_layers as base
from alternate_phase2_layer import build_authorized_phase2_layer

SOURCE_INTERVAL=base.SOURCE_INTERVAL
CANVAS_SHAPE=base.CANVAS_SHAPE
REGISTERED=base.REGISTERED
is_registered=base.is_registered
star_subject_mask=base.star_subject_mask
restore_star_gestures=base.restore_star_gestures
_phase=base._phase


@lru_cache(maxsize=3)
def caption_layer(phase_index):
    original=base.caption_layer(phase_index)
    if phase_index!=2:
        return original
    return build_authorized_phase2_layer(original,HERE/"authorized-alternate-japanese-f3402.npz")


def star_caption_extent(frame,shape=CANVAS_SHAPE):
    mask=np.zeros(shape,np.uint8)
    index=_phase(frame)
    if index is None:
        return mask
    if tuple(shape)!=CANVAS_SHAPE:
        raise ValueError("Star captions require native source dimensions")
    layer=caption_layer(index)
    x0,y0,x1,y1=layer["region"]
    mask[y0:y1,x0:x1][layer["extent"]|layer["contrast_ring"]]=255
    return mask


def restore_star_captions(output,source,current_frame,asset_name,
                          character_mask=None):
    if _phase(current_frame)!=2:
        return base.restore_star_captions(output,source,current_frame,asset_name,
                                          character_mask)
    mask=np.zeros(source.shape[:2],np.uint8)
    if not is_registered(current_frame,asset_name):
        return output,mask
    if source.shape!=output.shape or source.shape[:2]!=CANVAS_SHAPE:
        raise ValueError("Registered star captions require native source dimensions")
    layer=caption_layer(2)
    x0,y0,x1,y1=layer["region"]
    target=output[y0:y1,x0:x1]
    original=source[y0:y1,x0:x1]
    alpha=layer["alpha"]
    edited=np.any(target!=original,axis=2)
    paint=(alpha>0)&edited
    ring=np.zeros(alpha.shape,bool)
    if character_mask is not None:
        if character_mask.shape!=CANVAS_SHAPE:
            raise ValueError("Star character mask must use the native source canvas")
        gap=np.max(np.abs(target.astype(np.float32)-layer["ink_rgb"]),axis=2)
        ring=layer["contrast_ring"]&edited&(gap<60)&(character_mask[y0:y1,x0:x1]!=0)
        target[ring]=(54,45,65)
    blended=alpha[...,None]*layer["ink_rgb"]+(1-alpha[...,None])*target
    target[paint]=np.clip(np.rint(blended[paint]),0,255).astype(np.uint8)
    target[layer["core"]&paint]=original[layer["core"]&paint]
    mask[y0:y1,x0:x1][paint|ring]=255
    return output,mask
