# Raised Caption Repair

Scope is the actual-source half-open interval `[1225,1285)`, all 60 native frames. The Japanese line is `魔法になる 合図`; the Chinese line is `成为魔法的信号`. The f1261 character zoom does not move or scale these two lines.

## Source Registration

`source-audit.json` records sequential decode BGR/PNG hashes, PTS, source-reference hashes and exact native-reference comparisons for all 60 frames. Every comparison is equal and every best local offset is `[0,0]`. Primary donor is f1229, with five independent poses f1225/f1241/f1256/f1261/f1282. Five-of-six fixed cream-color votes and two registered row bands retain 7978 core pixels. The support image `registered-core-extent.png` was inspected: the old moving coat button and collar are excluded; both complete lines, including the horizontal stroke of Japanese `に`, remain.

The older warm-color classification alone misses real strokes whose compressed B channel exceeds G over the pink source coat. It is not used to construct this layer. Red unsupported warm-candidate plots are diagnostic only: pale clothing, skin and AA can share that range, so candidate counts are not glyph completeness measurements.

## Composition

The independent `raised_caption_layers.py` does not alter dance/opening caption implementations. Generic pale recovery is disabled only in this raised interval; generic yellow effects remain. Captions paint only source pixels already changed by the character replacement. Source-observed registered cream cores keep their exact current-source BGR values. Hidden background and AA are reconstructed from a local inpaint plate and projected alpha, not described as exact source alpha.

A fixed 1px dark edge is permitted only within the registered glyph ring, on edited pixels inside the explicit actual `new_subject` mask, with luminance gap below 38 and maximum foreground channel gap below 60. This is a contrast/readability repair, not a change to the words, glyph position or font. No edge is added on untouched source or clearly contrasting red costume areas; no star or old collar is outlined. The declaration includes this additional edge support.

`composite-audit.json` records all 60 actual current-asset composites, asset hashes, core/alpha/halo/new-subject mask archives and caption-page hashes. All 60 have zero non-source-exact observed cores, zero caption changes to previously untouched source, zero halo pixels outside actual new subject, zero changes outside declared glyph/edge support and zero whole-composite changes outside declared masks. Halo pixel counts range from 0 to 2562.

## Static Review

All ten `raw-caption-page-01..10.png` pages were viewed at native 2x crop scale, covering every actual frame. Both lines are now readable in the red-coat stage and the near cream-collar stage. Old gray collar and moving coat-button shapes do not reappear. Source compression texture remains in the complex `魔` glyph; it is not represented as exact font-alpha recovery or a whole-shot art approval.

Focused verification: 10 tests pass (`test_raised_caption_layers`, the existing four V8 full-composite pixel regressions, and `test_clear_dance_captions`). The 56-frame old dance suite and the full project suite were not repeated. The dance subtitle helper is unchanged. No audio or renderer timing code was edited.

## Final Encoded Captions

The corrected single preview is `production/output/klee-raised-1225-1285-fast-draft-v2.mp4`, SHA256 `c0a57ac0b6e35d368bc28cbaa6e1c6030559b76b70fd2f7159674ef2bc150e36`. Native source/encoded evidence for all 60 frames is retained in `production/qa/fast-fullpv-raised/encoded-v2-evidence/report.json` and its 60 crop pairs / eight contact pages. Its report SHA256 at this check is `0fbebaa89324fd6c9deee427c5943d043e49289dca6eeac204d1419cd2e9e2b4`.

All eight final encoded pages were actually viewed by this caption task, independently of the raised-shot owner. The two original lyric lines remain complete/readable in every frame, including f1261's zoom and the subsequent close-up collar placements. The fixed edge remains locally distinguishable after encoding; the v1 disappearance / fragmented-letter symptom does not recur. Encoded YUV compression is not represented as exact original BGR. All 60 source BGR hashes match this task's sequential-source audit, all 60 native crop-pair file hashes match the worker report, all eight page hashes match, and the final single-video hash matches.

This completes the limited static raw/encoded subtitle check, not whole-shot artistic approval or a claim of watching the continuous clip at original speed. Original-speed review is not performed by this caption task. The raised-shot owner separately reports technical preview checks. Broken encoded-v1 evidence is retained separately as baseline, not counted as the repaired version. The later scoped night-module integration affects only different registered assets at f902..910, so no raised layer or asset was changed for this final encoded check.
