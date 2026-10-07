# Opening source-layer audit

Scope: the 25 generated opening anchors at source frames 0, 25, 28, 31, 38,
50, 54, 58, 63, 68, 75, 79, 83, 87, 91, 95, 99, 117, 121, 125, 129,
133, 157, 162, and 167. Frame 121 uses `fine-f0121-costume-repair.png`.
This is a
static layer and geometry review, not acceptance of the whole PV or an
actual-speed playback review. Source references are 1920 x 1080; generated
assets are 1672 x 941 and were resized to the source canvas with Lanczos.

## Findings

1. The floating clock at frames 38, 50, and 54 is sufficiently aligned for
   direct restoration from the current original source frame. The generated
   display is blank; the original clock body, display, digits, outlines, and
   empty background around it can be copied together. Display-center drift
   is 0.34, 0.84, and 0.49 pixels respectively. The display hull overlap is
   95.6%, 91.2%, and 92.9%.
2. Held-clock poses have two distinct problems: different finger occlusion,
   and, from frame 79 onward, substantial clock/hand displacement. Restoring
   the original clock at its original coordinates cannot repair those hand
   contacts or the eye occlusion. It would leave a second generated clock or
   put the source clock through the generated face and hat. These poses need
   redraw to the source clock and hand coordinates before full source-prop
   restoration can be accepted.
3. The pillow is behind the head and body. It must be restored only where
   the new character is absent. Original visible lilac/blue material and
   clearly exposed fringe regions can be recovered. Original pillow pixels
   hidden by the old hair and head are unavailable in a single source frame.
   Changes in Klee's silhouette expose different areas; their exact original
   appearance must come from another observed source frame or a reviewed
   background plate. A mask alone cannot reconstruct them.
4. Clock digits are part of the clock layer. Restoring them as independent
   pale glyphs at the original coordinates can detach them from a displaced
   generated clock. For held clocks the intended order is: original pillow,
   Klee head/body, clock, Klee brown fingers and cuffs, then original captions
   and independent effects. The source hand skin must not come back with the
   clock, and the brown fingers must stay in front of its body and display.
5. The independent clock at frames 162 and 167 can be restored together with
   its surrounding original background. These frames require a different
   pillow mask: the visible front fringe covers the rear arm, while the
   crossed arm, cuff, and visible brown glove cover the pillow. The largely
   hidden other hand must not be brought forward with a generic warm-color
   mask. These frames have explicit front-arm guards and their own fringe
   annotations.
6. At frame 157, the generated released clock is 172 pixels left of the source
   display. Its incorrect location can be erased with the exact original
   background. However, the new open hand is also displaced and overlaps
   5,701 of the source display hull's 7,590 pixels. Copying the original clock
   through that hand would cut off the glove; keeping the glove in front
   makes the source's released clock appear held again. The helper includes
   an erase-and-partial-restore diagnostic, but this frame is explicitly
   flagged as needing a pose redraw. It is not a completed prop repair.
7. Frames 129 and 133 move both the held clock and the pillow/character group
   left of the source. Old safe fringe annotations are disabled for frames
   121 onward. Only source-visible cool pillow regions are conservatively
   restored until the displaced holding poses are redrawn.

Measured visible display hull differences in source-canvas pixels:

| Source frame | Generated minus source center (x, y) | Distance | Display overlap |
| --- | --- | --- | --- |
| 58 | -26.9, -9.0 | 28.3 | 9.2% |
| 63 | -5.5, -11.9 | 13.1 | 29.3% |
| 68 | -5.4, -9.8 | 11.2 | 38.1% |
| 75 | +1.4, +0.9 | 1.7 | 89.0% |
| 79 | +37.1, +85.0 | 92.7 | 0.0% |
| 83 | -5.2, +42.8 | 43.1 | 0.1% |
| 87 | -72.3, +49.1 | 87.4 | 0.2% |
| 91 | -66.1, +50.2 | 83.0 | 0.0% |
| 95 | -62.5, +47.2 | 78.4 | 0.2% |
| 99 | -66.9, +48.5 | 82.6 | 0.3% |
| 117 | -82.7, +48.7 | 96.0 | 0.0% |
| 121 | +1.9, -6.6 | 6.9 | 71.9% |
| 125 | +0.6, -12.7 | 12.7 | 63.6% |
| 129 | -94.8, -20.4 | 97.0 | 0.0% |
| 133 | -92.6, -20.3 | 94.8 | 0.0% |
| 157 | -172.0, +8.2 | 172.2 | 0.0% |
| 162 | -1.3, -0.1 | 1.3 | 96.6% |
| 167 | +10.2, -7.9 | 12.9 | 68.9% |

Metrics use coherent purple pixels inside separately annotated display ROIs,
then their convex hull. A change in finger coverage can shift this visible
hull without moving the complete clock; frames 58, 63, and 68 therefore need
the contour overlays and hand crops to interpret the numbers. The much larger
frame 79-117 differences are also plainly visible in the source/generated
images. Hull masks are diagnostic and are never used to paste a clock.

## Implemented conservative restoration

`production/opening_layers.py` provides:

```python
result, masks = restore_original_properties(
    output, current_source_frame, generated_in_source_coordinates,
    asset_source_frame,
)
```

Call it after generated-cel placement and before final original captions and
independent effects are restored. Use the current decoded source frame for
`current_source_frame`, not a frozen reference image. The fourth argument is
the selected asset's source frame, so the semantic mask follows the pose.
Both images must already be in the same 1920 x 1080 coordinate system.

This helper restores observed pillow interiors and clear fringe regions. It
does not claim complete pillow boundary extraction. It restores the full
floating-clock region for frames 38, 50, 54, 162, and 167. A local guard protects
brown generated glove pixels; the frame 75 pillow mask also explicitly
excludes the region crossed by the raised clock and cream cuffs. Held clocks
remain untouched and are marked as needing geometry/hand review. Frame 157
additionally copies source background over the wrong generated clock and
restores the source clock only outside the displaced new glove and cuff.

The manifest records the source and asset SHA-256 hashes, restored pixel
counts, source mismatches, guarded glove overwrites, display geometry, mask
paths, and diagnostic paths. Regenerate the report if an asset changes.

## Verification and limits

Across all 25 anchors the partial restoration copies 1,711,519 pixels in total
from their matching original source frames. Within those masks, source pixel
mismatch after composition is zero. Pixels changed outside the masks: zero.
Protected brown glove pixels overwritten: zero. Protected front-arm and cuff
pixels overwritten: zero. Python compilation succeeded.

Frame 157's wrong-clock erase region is 31,872 pixels. Its actual source
background has BGR standard deviations 1.176, 0.686, and 0.684, consistent with
the source's nearly flat purple field. The replacement copies those current
source pixels exactly; it does not synthesize a new flat color. The erase
region contains no source character, clock, or caption strokes.

The four-column diagnostic sheets show source, generated, partial source-prop
restoration, and masks. Green marks copied pillow regions, amber marks the
floating-clock region, muted blue marks observed source material not copied,
orange marks erased incorrect clock/background, and magenta marks the local
brown glove and front-arm guards. Contour images show the source
display in red and the generated display in cyan.

These checks establish exact copying inside the recorded partial masks. They
do not establish that every pillow edge is preserved or that hidden material
has been recovered. They do not pass held-clock anatomy or temporal continuity.
No generated assets, production compositor, or timeline were edited by this
audit. No held prop was translated, warped, or replaced with a fabricated plate.
