# Star 1008-1043 Encoded Static Review

Date: 2026-10-05, Asia/Shanghai. Reviewer: star_final_render_resume.

## Scope

- The new draft and original/new comparison cover exactly `[1008,1043)`: 35 source frames, 16 selected cels, 16 exposures, source video boundary 1.458 seconds.
- All five `SOURCE-ENCODED` pages and all five `RAW-ENCODED` pages were actually viewed. These 1400x903 sheets retain two 700x105 native caption crops per row without scaling.
- All five body pages were viewed. Their source/raw/encoded images are explicitly 640x360 thumbnails; the first four 1920x1536 sheets were additionally displayed at 1760x1408. They are not native-resolution anatomy inspection or actual-speed playback.
- The technical verifier passed all 17 checks independently for both MP4s. This covers source identity, all video frames/dimensions/PTS/end boundary, original AAC configuration/payload/timing/priming/whole-packet tail, and full video/audio decoding.
- The independent shared compositor regression was actually rerun: all 35 star frames equal the authorized private oracle in BGR, all 97 earlier cyan frames and all 74 older dance/raised frames equal their raw frozen BGR hashes. All nine relevant shared-code/layer hashes were unchanged during that run.

## Caption Findings

- Japanese and Chinese lines remain identifiable throughout the 35 encoded frames. No newly broken or missing glyph caused by encoding was observed in raw/encoded pairs.
- The final six frames `[1037,1043)` use the user's authorized same-sentence clear original Japanese handwriting from f3402, native integer translation `(-12,0)`. Source text, placement and phase timing are unchanged. Alpha, antialiasing and target ink palette are reconstructed, so this is not pixel-exact recovery of invisible source strokes.
- Observed Chinese source cores remain independent of the Japanese reconstruction. The static encoded caption crops show no return of the original character's pale trousers or shoes as a lyric background plate.
- Text over pale new hair deliberately has a thin dark contrast edge. It remains legible in these static crops, but the outline/hollow appearance is more conspicuous than the original raster. Its styling remains a first-cut review issue rather than an accepted match to the original.
- The existing lyric phase boundaries at f1012 and f1037 were retained; no new exposure, crossfade, or retiming was introduced.

## Deferred Artwork Findings

- The f1028-to-f1033 transition changes from the decorated coat draft to the already-selected simplified plain-coat draft. This is a visible asset-level design discontinuity, not an encoding failure. The user has asked to finish the first cut before requesting detailed rework.
- Other existing selected-draft proportions, accessory density, poses and simplification differences are not newly accepted by this export.
- Static comparison shows the selected foreground/background Klee figures and rear-view/closed-eye/full-body shot changes survived encoding. It does not establish motion quality, natural pose flow, or actual-speed visual acceptance.

## Status

Technical checks and this bounded static encoded-caption review pass. `accepted=false` remains in all new records. No actual-speed viewing was performed, and no full PV or artistic acceptance is claimed. This delivery adds a reviewable 1.458-second shot group, not a completed full-length PV.
