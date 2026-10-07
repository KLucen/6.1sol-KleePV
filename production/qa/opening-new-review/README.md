# Opening Draft Static Review

Scope: 11 newly generated/repaired assets at source frames 129, 133, 157, 162,
167, 172, 176, 180, 185, 190 and 194. Whole images, source comparisons,
focused clock crops and the adjacent 172/176/180/185/190/194 sequence were
visually inspected. This is not an actual-speed review or final acceptance.

## Findings

- Frames 129 and 133 geometry repairs substantially improve clock placement,
  but retain thin source-like hair loops below the viewer-left outstretched
  arm. Those are not connected cleanly to Klee's two short ponytails. They
  remain drafts requiring removal and adjacent clothing review.
- Frame 157 glove repair correctly changes the exposed palms to brown gloves
  and retains the released-clock gap. It is not a pixel-local edit: outside
  the two hand ROIs, 107,426 pixels differ by over 8 channel levels, with mean
  absolute channel difference 2.86678. The heatmap shows widespread outline
  and texture changes rather than a preserved raster outside the hands.
- Frame 167 adds a large cream shoulder/elbow pom separate from the smaller
  chest pom; frame 162 had no such shoulder pom and frame 172 removes it.
  Collar, chest ornament and waist cord/pom construction vary in this group.
- Frame 176 original draft had two ponytail-like wings on the viewer-right
  side and a scalloped fluffy cuff. The hair/cuff repair removes the lower
  wing and makes the cuff plain, improving identity consistency. However,
  it also changes the red forearm sleeve contour beyond the cuff edit ROI.
  Outside the cuff/hair ROIs, 83,006 pixels differ by over 8 channel levels;
  mean absolute channel difference is 3.13972. It is an improved draft, not
  a confirmed pixel-local or accepted replacement.
- Face reveal progression is present: frame 172 has visible half-open eyes;
  frame 176 has no exposed eye, nose or mouth; frame 180 hides the face;
  frame 185 reveals only lid/iris slivers; frames 190/194 reveal both
  half-open red eyes while keeping the mouth hidden. Foreground gloves sit
  in front of the pillow at the source's intended contacts.
- The large curled front hair lock is exposed in frame 180, vanishes in
  frame 185, then returns in frame 190. The pillow lowering does not explain
  its disappearance. Keep or remove this identity detail consistently.
- Frames 190/194 preserve the change from curled edge grips to spread palms
  on the pillow front. Frame 194 redraws the finger and cuff orientation;
  it is not simply an unchanged copy of frame 190. Remaining collar/pom,
  sleeve and garment-outline continuity still needs moving review.
- Generated pillows and clocks are not the original raster props. Exact
  source prop restoration and original caption restoration remain separate
  compositing work. No whole-pillow mask is recommended for the frontal
  states 172 onward from the existing helper's older medium-pillow polygon.

## Clock Geometry

Measurements use the largest coherent purple display component and its
convex hull, not all purple components. The previous helper can include the
separate purple clock handle, which biases hull centers. These numbers are
diagnostic, not acceptance thresholds or hand-occlusion proof.

| Frame | Display Delta X/Y, Pixels | Center Distance | Hull IoU |
| --- | --- | --- | --- |
| 129 repair | -5.502 / +1.369 | 5.670 | 0.79809 |
| 133 repair | -7.479 / -4.230 | 8.592 | 0.72652 |
| 157 glove repair | -1.426 / -1.356 | 1.968 | 0.93361 |
| 162 | -1.048 / +0.071 | 1.050 | 0.96208 |
| 167 | -1.254 / -1.293 | 1.801 | 0.94102 |
| 172 | -1.902 / -0.555 | 1.982 | 0.93797 |
| 176 hair/cuff repair | -1.279 / -1.786 | 2.197 | 0.91307 |
| 180 | -3.300 / -1.090 | 3.476 | 0.89657 |
| 185 | -1.155 / -0.174 | 1.168 | 0.96316 |
| 190 | -2.303 / -0.548 | 2.368 | 0.92923 |
| 194 | -3.043 / -1.076 | 3.227 | 0.90622 |

## Source Clock Copy Recommendations

- Frames 162, 167, 172, 176, 180, 185, 190 and 194: the source-clock bounding
  rectangle `[866, 464, 1018, 624]` is visually isolated from both source and
  generated character/gloves. Its edges include source background, so it
  must be copied after the output background is restored from the source.
  Coordinates are normalized 1920x1080 asset source-frame coordinates only.
  Do not reuse across unverified camera transforms.
- Frame 157: a full rectangle is unsafe. The source open hand and generated
  glove enter its upper-right empty corner. Use the saved
  `f0157-clock-mask-from-source-f0162.png` clock silhouette instead, copy
  pixels from actual source frame 157, retain generated glove protection,
  and inspect the composited boundary. Source frame 162 supplies only the
  mask geometry for the same stationary clock, not replacement pixels.
  The raw mask touches 2 brown-glove edge pixels. The asset-specific
  `f0157-clock-mask-glove-guarded.png` excludes a dilated glove guard and has
  zero guarded-glove overlap. A clock-only diagnostic is saved for inspection.
- Do not apply the old helper's frame-157 misplaced-clock eraser to the
  geometry repair: it addresses the old shifted draft and is obsolete here.
- Held-clock frames 129/133 still require a separate glove/cuff-aware mask.
  A bounding rectangle would copy original bare hands into Klee's gloves.
- `opening_layers.py` has explicit crossed-arm/front-fringe annotations only
  for frames 162/167. Its fallback medium pillow mask does not support the
  later frontal poses and should not be silently applied to those states.

## Artifacts

`metrics.json` records exact asset hashes, inspected ROIs and measurements.
`sequence-source.jpg` and `sequence-generated.jpg` are focused static
contacts. Each reviewed frame has a complete source/generated pair, enlarged
display contour comparison and (from 157 onward) clock/nearest-hand crop.
Both local-edit heatmaps are retained. The script edits no production asset,
timeline, selection, compositor or existing prop-helper file.
