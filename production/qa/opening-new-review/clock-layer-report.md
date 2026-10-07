# Clock-Only Helper

Implemented `production/opening_clock_layers.py` and
`production/test_opening_clock_layers.py`; no compositor, timeline, selection,
generated cel, pillow helper or source asset was edited.

`restore_clock(output, source, generated_in_source_coordinates,
asset_source_frame, asset_name, transform)` returns a new uint8 BGR canvas
and a 0/255 restoration mask. Inputs are normalized 1920x1080. The `source`
argument is the actual current source frame whose pixels are copied.

## Guardrails

- Only 15 explicit source-frame/asset-name pairs are supported. This includes
  the eye-repaired frame 38, hair/cuff-repaired frame 176 and hair-repaired
  frame 185 in addition to their reviewed parent assets.
- Frame 38/50/54 uses `[854,375,1050,533]`; isolated frame 162/167/172/176/
  180/185/190/194 clocks use `[866,464,1018,624]`.
- Frame 157 supports only `fine-f0157-glove-repair.png`, and verifies the
  exact PNG SHA, the recorded review SHA, the guarded-mask file SHA and the
  exact normalized generated raster. It uses the saved glove-guarded clock
  silhouette, not a full rectangle. Failures return unchanged pixels and a
  zero mask.
- Only exact 2x3 identity matrices are supported. `None` denotes the
  renderer's existing identity default. Translation, scaling, rotation,
  malformed matrices and unknown filename/frame pairs return a no-op.
- Held clocks, pillow restoration and the obsolete shifted frame-157 clock
  eraser are not supported. No unverified camera-frame mask reuse is added.

## Verification

Eight unittest cases pass. The technical audit covers all 15 supported pairs:
inside-mask pixels equal the supplied current source, outside-mask changes
are zero, frame 157 guarded-glove overlap/changes are zero, and input arrays
are not mutated. Tests also prove nonidentity/unknown assets, stale asset or
mask hashes, and a modified released-clock raster cannot enable restoration.

Provenance and source/generated hashes are recorded in
`clock-layer-provenance.json`. This is technical pixel-copy verification,
not artistic acceptance or actual-speed continuous-frame review.

## Additional Local Repair Review

The frame-185 hair repair restores the exposed curled forehead lock. Whole
image inspection confirms the clock remains isolated and within its approved
rectangle. However, this is not pixel-local: outside the forehead ROI,
76,601 pixels change by over 8 channel levels, mean absolute channel delta
2.92423. The heatmap shows widespread outline/texture resampling changes.

The frame-38 eye repair changes the visible profile iris toward red. The
isolated clock remains safely separated from the character inside its
approved rectangle. Outside the eye ROI, 95,180 pixels change by over 8
channel levels, mean absolute channel delta 1.87666. It is likewise not a
pixel-locked edit outside the requested local change.

Exact ROIs and metrics are saved in `clock-layer-local-repair-review.json`;
both x4 difference heatmaps are retained. The siblings are supported only
for clock restoration, with no character-quality acceptance inferred.
