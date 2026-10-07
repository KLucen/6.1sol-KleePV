"""Pure data construction for the authorized, registered real glyph alternate."""

import numpy as np


def build_authorized_phase2_layer(original,data_path):
    with np.load(data_path) as alternate:
        ax0,ay0,ax1,ay1=map(int,alternate["region"])
        ox0,oy0,ox1,oy1=original["region"]
        if (ax0,ay0)!=(ox0,oy0) or ax1<ox1 or ay1>oy1:
            raise ValueError("Alternate real glyph data is not registered to this phase")
        region=(ox0,oy0,ax1,oy1)
        pad=ax1-ox1
        layer=dict(original)
        for key in ("core","extent","alpha","contrast_ring"):
            layer[key]=np.pad(original[key],((0,0),(0,pad)))
        top=ay1-oy0
        layer["core"][:top]=False
        layer["alpha"][:top]=alternate["alpha"]
        layer["extent"][:top]=alternate["alpha"]>0
        layer["contrast_ring"][:top]=alternate["ring"]
        ink=np.broadcast_to(original["foreground"],(*layer["alpha"].shape,3)).copy()
        ink[:top]=alternate["ink_rgb"]
        layer.update(region=region,ink_rgb=ink,
                     alternate_japanese_core=alternate["core"].copy(),
                     alternate_interval=(1037,1043),
                     real_alternate_donor="source_refs/src-1905-f3402.png",
                     integer_translation=(-12,0),
                     reconstruction="Human-authorized real f3402 same-word Japanese glyph alternate; target cream palette and estimated alpha/AA. Original Chinese observed cores retained. Unaccepted.")
        return layer
