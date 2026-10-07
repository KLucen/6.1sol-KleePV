# Dance Caption Layer Draft Handoff

Only the new `production/dance_caption_layers.py`, its new focused tests, and private QA files were changed. No shared compositor, opening-caption helper, review pipeline, or asset selection was changed by this worker. No images were generated.

## Scope And Evidence

- Effect is strictly source frames `[831,863)`, native 1920x1080, region `(754,954,1136,1047)`.
- Main observed donor is `source_refs/src-0377-f0831.png`. f835 and f839 are phase-check donors. The warm-cream detector includes hue 12 and excludes the pale pink star color as an initial glyph core.
- All seven retained reference cels were compared and visually inspected on `source-phase-and-over-boot.png`. Fixed-position glyph-core comparisons favor offset `[0,0]` for f831/835/839/843/848/852/856.
- All 32 actual source frames were sequentially decoded from the identity-verified source, not inferred from seven cels. See `phase-and-layer-audit.json` for each frame's offset, color delta, and alpha-support diagnostic.
- All 10 focused tests passed. The exact transcript is `focused-tests.txt`.

## False Item And Reconstruction Limit

`all_32_current_warm_core_inside_donor_alpha` is **false**. The recorded unsupported points must not be omitted or called accepted. Broad warm-HSV candidates include later old-shoe/skin false positives, but some unsupported points also occur in Japanese glyph/star intersections and compressed edges. The first donor itself has unsupported warm candidates after the cross-frame core filter. These candidates require visual classification; they do not automatically prove either a missing letter or a correct matte.

Full point coordinates are preserved in `unsupported-current-warm-core-points.npz` with columns `frame,x,y`. Eight `unsupported-current-core-page-XX.png` pages display all 32 frames, marking these candidates red. The JSON retains counts and representative coordinates.

The f831 text is unobstructed by a human, but a pale pink background star passes behind the Japanese line. Hidden background, local plate, projected anti-aliasing, and constant foreground color are **reconstructed**. No exact original subtitle alpha or source-exact replacement text is claimed. The Chinese line is more reliable than the star-crossing Japanese counters; the latter may be denser or less precise than the original raster.

The current best bounded version removes the visibly detached between-line star fragments and never pastes an old shoe/background rectangle. A trial global color unmixing produced unstable, broken glyphs and was discarded. No further broad algorithm revision was made after the requested stopping point.

## Integration Recommendation

1. Before applying generic source graphics, suppress that overlay only in the registered `REGION` and `[831,863)` scope. Do not copy a broad original-text rectangle afterward: current source f843 onward contains old shoes/skin behind the letters.
2. After character, scene, and independent graphics composition, call `restore_dance_captions(output, current_source, current_frame)`. It preserves exactly unchanged source pixels to avoid painting existing glyph AA twice. Changed glyph pixels are cream-over-current-underlay, not opaque donor pixels; its returned mask must be included in declared edits.
3. Add this module plus all three donor paths to raw-review provenance. Include the source-derived alpha reconstruction note, rather than labeling the layer source-exact.
4. Check current selected assets from `asset_selections.json`, especially new source-led f835/f848 v2, rather than an old private asset list. Review stable donor glyph cores separately from unsupported candidates. Full-size final glyph shapes, pale-on-pale contrast, old-shoe removal, preserved stars outside glyph support, and f830/831 plus f862/863 boundaries need final composite checks.

This is a draft integration candidate only. Its transparent blending and scope tests do not establish drawing quality, corrected shoe extent, full-speed continuity, or artistic acceptance. Artistically accepted character cels remain zero.
