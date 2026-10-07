# Full PV Coverage And Compositing Audit

Snapshot: 2026-10-02. This is a source-map and saved-asset audit, not an artistic acceptance or real-time playback review. Agents are adding assets; refresh `audit_full_pv_coverage.py` before the final render.

## Coverage

- Source: 3658 frames, 689 conservative source cels, 938 exposure spans.
- Saved PNGs: 203; selected direct character drafts: 153 cels; one verified alias expands this to 154 character cels. A further one cel is an exact source reuse with no visible person.
- Mapped availability: 155 cels, 823 frames, 22.4986% of the full PV. Character replacement accounts for 773 frames; the verified empty source cel accounts for 50 frames.
- Missing selected cels: 534. Four blocked or failed cels are included in that count.
- At least 63 selected drafts have recorded structured flaws or caption cleanup requirements. No character cel has full artistic acceptance in this audit.
- All 203 saved PNGs decode. Most generated canvases are 1672x941 or 1672x940 and need a consistent, reviewed normalization, not an assumption of native source resolution.
- Detailed cel, source-frame, exposure, job, asset and proposed chronological work-package records: `full-pv-coverage-report.json` and `full-pv-progress-manifest.json`.

## Deduplication Evidence

The 2160 raw source candidates were reduced conservatively: 750 codec copies, 76 verified source-layer translations, 584 confirmed drawing copies and 61 confirmed original-camera similarities, leaving 689 source cels. 744 uncertain pairs remain separate. Low residual alone does not authorize a merge.

`source_aliases.json` adds one manually approved source copy: f1299 / cel0280 to f1296 / cel0279, identity transform. It does not change the conservative source map. Other title pairs f1309/f1375 and f1314/f1380 are unapproved candidate duplicates and must not be silently adopted.

The family name `blank_transition` is not a semantic permission to retain a person: f3055 / cel0532 and f3067 / cel0533 contain a large back-facing human and require independent Klee replacements. The only verified no-person source reuse is cel0064, including f407 and later f1771, totaling 50 frames.

## Fatal Full-PV Risks In The Current Compositor

1. **Titles and large pale graphics are not comprehensively restored.** `compose.py` `graphics_mask` only covers selected bottom or small left components and yellow effects. The large Japanese title behind the seated figure around f1296-1426 falls outside those rules. Copying generated pixels inside the union of old and new silhouettes can erase original title fragments exposed by Klee's shorter hair. Use shot-scoped original title/glyph alpha with reviewed back/front occlusion, not an unconditional foreground overwrite.
2. **Non-flat sky cannot use the opening's flat background repair.** Cyan-profile sections include blue-purple gradients and star texture. The source-background median fill is conditional on near-uniform violet, so vacated old hair elsewhere takes generated sky pixels. That changes original texture and risks temporal flicker. Build registered original clean plates from visible source pixels and isolate any genuinely unobserved reconstruction.
3. **Multiple people and partial people need explicit ownership.** Star-dance and cyan-profile transitions contain a cropped warm-colored person at the left/top while another figure is present. Replace every visible person. A single whole-canvas camera transform is not a substitute for separate character tracks or a faithfully redrawn composite cel when motions differ.
4. **Exact props are only handled in a small opening whitelist.** Clock restoration is gated to frames below 210; the later standing-pillow/clock repeat around f2906-3055 is not covered. Pillows, sacks/fish and impact poses have no general original-prop layer. Register per-cel original prop alpha and generated front-hand guards; source geometry must be correct before copying prop pixels.
5. **HSV subject masks are heuristics, not full-PV mattes.** The seed colors overlap sky, cyan-lit clothing, pale trim and effects. External contour fill and dilation can include background stars or omit limbs. Use reviewed per-shot source-vacated and new-character mattes. Do not let global color deletion define semantic character coverage.
6. **Effect halos and depth can restore old anatomy.** Yellow-effect dilation copies neighboring pixels as well as stars, potentially including old skin or hair. White hatched stars are not uniformly included, and some effects belong behind the figure. Use original antialiased effect alpha with explicit front/back ordering.

Current source-backed examples were inspected at full resolution or in chronological family contacts: f3055/f3067 back-facing figures; f1309/f1314/f1375/f1380 title-body overlap; star-dance f812 onwards; cyan-profile f911 onwards; dive-prone f2657 onwards; yellow-star-burst f3087 onwards.

## Completion Gate

Complete independent source drawings first; no static hold, optical flow, mirrored pose or nearby-cel substitute may hide missing cels. Then check all source-map boundaries, key limb contacts, occlusion, original caption/prop pixels, chronological adjacent frames and complete actual-speed playback. Decode, PTS, frame count and AAC packet equality are separate technical checks and do not grant an artistic pass.

## Work Ownership

The progress manifest assigns each canonical cel to its earliest chronological family run. Later repeats reference that owner and are not duplicated. This worker owns missing canonical representatives f2400-3657: 206 cels at this snapshot. Earlier canonical cels occurring in that range remain with their earlier owner.
