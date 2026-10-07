# Dance V11 Encoded Caption Static Review

Date: 2026-10-04. Scope: source frames [812, 911), all 99 frames.

## Evidence Actually Reviewed

The same original source and the final single V11 video were decoded sequentially, at native 1920 x 1080 resolution. There are 99 source and 99 encoded decodes, with no extra encoded frame. All 99 source/encoded native caption pairs and all 13 contact pages were actually viewed, including clear frames 812..830, the true lyric boundary at 897, and the corrected back-view exposure at 900/901. Encoded crops, not raw composites, are the object of this review.

Video: `C:/Users/KLucen/Desktop/kl/production/output/klee-dance-812-911-fast-draft-v11.mp4`

Video SHA256: `568454f423d2a1bef897a2d3c4929fdb8328fce5fde024183d4ac289c33e5fc7`

Timeline SHA256: `3e6c40b9d382f2a61b510b3d6fa128c532ce0a7b7c52a1d51588e4e376e74b5d`

The machine record is `report.json`; every frame has source/encoded BGR hashes, asset provenance, phase registration, observed source glyph core diagnostics, and hashes for the crop and mask archive. All 99 crop hashes, 99 mask hashes, 13 page hashes, timeline/video/implementation hashes, and recorded asset/donor hashes were checked. All 478 recorded file-hash checks match; the source-frame sequence is exactly 812..910.

## Static Findings

- Clear phase [812, 831), 19 frames: the two short lyric lines remain present. Source pale-star overlap affecting parts of the Japanese line is retained rather than labeled a new caption-layer defect.
- Old registered phase [831, 897), 66 frames: no new missing/broken line or incorrect phase was observed. Existing pale source/animated stars intersect portions of Japanese and Chinese middle glyphs. This limits clarity on those intersections; the finding is not that every character is unobstructed or crystal clear. The frozen old output was not changed during this encoded review.
- Night registered phase [897, 911), 14 frames: the actual lyric changes at frame 897, not 887. Both longer lyric lines remain complete and readable in these static crops, including the pale hair at 900/901 and the night-transition foreground. The scoped fixed 1 px contrast edge remains effective after encoding; no newly missing/broken glyph or wrong-phase substitution was observed.

Observed-core color differences are lossy-encoding diagnostics, not an exact-RGB claim. The per-frame maximum-channel P95 ranges are 10..11 for clear, 8..15 for old, and 9..32 for night. These statistics do not establish legibility; legibility observations above come from actually viewing the encoded crops. Reconstructed anti-alias support does not claim exact recovery of hidden original alpha.

## Frozen Inputs And Limits

- `compose.py`: `94c6146c85ca34e3099ebe5cfa583c450664f26ed176bd09249b428cf78bf8f5`
- `dance_caption_layers.py`: `b00988faaab15a3282c05e39483ca114152e2325be0e3e964fac7391c727eda8`
- `night_transition_layers.py`: `746a0e2c6b586a108c4cb8f35902184ee8327232acc0ea808f9e5aa197921ac7`

No production layers, composition rules, assets, timings, or audio were edited in this final review. No rerender or whole-project test suite was performed. V10 evidence remains a baseline whose full manual caption review was deliberately held while the original rear-hat fragment was repaired; it is not substituted for this V11 review.

This is an independently completed static caption review over all 99 encoded frames. It does not establish original-speed continuous motion, character/occlusion artistic acceptance, side-by-side artistic acceptance, or full-PV completion. Original-speed viewing was not performed by this caption task. Root owns final video technical verification and the remaining production acceptance decisions.
