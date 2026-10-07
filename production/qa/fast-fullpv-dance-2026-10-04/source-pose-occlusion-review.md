# Shot 10 Missing Source Cels: Pose and Occlusion Review

Source-only preparation for strict-source missing frames 887, 889, 903, 907, 908, 909. No artwork generation, aliases, global selection, exposure or compose changes were made.

`prepare_missing_refs.py` sequentially decoded the same original MP4 from frame 0 through 911, saved actual current and preceding source frames, and compared all six current frames pixel-for-pixel with their canonical `source_refs`. All six comparisons are exact. `missing-source-reference-queue.json` holds source PNG/BGR hashes, source-map and manifest hashes, all exposure ranges, full A/B/RGB/contour references and local crop paths/hashes.

The reviewing agent actually viewed all six current source images, all six full A/B/RGB/contour boards and all six final local A/B boards. This is source analysis, not generated-artwork approval or original-speed acceptance. The queue's machine-generated `manual_source_review: pending` is superseded only for this documented source-view scope.

| Current | Actual preceding cel | Exposure | Required pose and semantic changes |
| --- | --- | --- | --- |
| 887 | 880 | [887, 889), 36.958-37.042 s | One full-body performer. Closed eyelids, small open O mouth, clockwise/right head lean. Screen-left arm high with spread palm; screen-right arm slopes down to spread palm. Two straight separated legs, left boot flatter/lower, right boot pointing right/up. Versus 880 the head, shoulders and sleeve geometry change, raised hand moves left/down and lowered right hand moves up/left; do not freeze 880. |
| 889 | 887 | [889, 891), 37.042-37.125 s | A second huge foreground face enters from the right. Foreground eyes open with two-color irises and tiny open mouth; hat top and right side of face leave the canvas, shoulder/coat cropped below. Background small dancer remains in the 887-style pose. The foreground hat/hair/face masks part of the background right hair, sleeve/hand region and right-side yellow particle area. Both people must become Klee; do not treat the foreground face as background art. |
| 903 | 902 | [903, 905), 37.625-37.708 s | Two portraits during transition. Huge left foreground head, hat cropped above/left, closed horizontal eyelids and small chevron/closed mouth. Side hair sweeps across shoulders and the rear character. Rear right-facing profile is blue/cyan night-tinted, one visible open eye and tiny dot mouth; hat/head/neck/coat remain visible behind. Versus 902 the primary differences are rear profile hat/fringe contour and disappearing cream star overlays; front mouth remains closed chevron. No hands or legs are visible. |
| 907 | 905 | [907, 908), 37.792-37.833 s | Left foreground closed eyes and small triangular open mouth; huge face remains cropped. Rear right-facing blue/cyan profile remains behind. Actual 905-to-907 difference is very small: max RGB 70, 2307 whole-canvas pixels at delta >= 28, mainly thin rear portrait contour differences/compression. Independence is not established from numbers alone. Retained mapping stays separate; no automatic alias was made. No hands/legs visible. |
| 908 | 907 | [908, 909), 37.833-37.875 s | Foreground head shifts substantially left and leans, with re-drawn bangs, closed eyelids and triangular mouth. Large right side-hair wedge crosses the rear profile neck/chest. Rear profile keeps its pose/canvas location. This is a major foreground redraw, not a rigid duplicate or hold. No hands/legs visible. |
| 909 | 908 | [909, 911), 37.875-37.958 s | Foreground portrait largely keeps the 908 expression/crop. Rear profile is independently changed: hat slope, fringe tip, side hair and lower profile/chin/coat contours differ from 908. Blue/cyan lighting and right-facing gaze remain. Front hair stays in front of the rear neck/chest. No hands/legs visible. |

## Reference Roles

- Current actual source is `fNNNN-source-actual.png`, the sole authority for pose, crop, foreground/background person count and layer order.
- Preceding actual source is paired in `fAAAA-fBBBB-source-ab-rgb-contours.png`; its upper row is original A/B, lower row is true RGB delta x4 and blue-before/red-current contours. Whole-frame differences include stars, captions and compression.
- Current crop files and `fNNNN-source-local-ab.png` are evidence of local geometry, not artwork components to be pasted.
- For 887/889, final local crops cover small head, raised palm/cuff, lower palm/cuff, legs/boots/caption and incoming giant face.
- For 903/907/908/909, final local crops instead cover foreground head/hat, eyes/mouth, rear night profile, coat/hair/caption overlap and left edge. Earlier unused dance-style hand/leg crop files from the first preparation pass do not imply visible limbs and are not referenced by the final queue.

## Quality Priorities

1. Replace both visible people from 889 onward. The manifest family `star_dance` does not imply one person, nor does it define the actual shot semantic transition.
2. Keep near/far layer ordering and source cropping; do not invent out-of-frame hands/legs or expand the huge head into a full standing person.
3. Replace the sleep-mask/animal hat design with the established Klee hat identity while preserving its crop/lean. Rear night tint is required scene lighting, not identity coloration.
4. Keep source moon, star field, yellow particles and independent caption phase. Bottom Chinese/Japanese text crosses boots/coat/hair at these stages and must be composited independently; generated captions must not become the final text layer.
5. Preserve all six existing exposure ranges. No source deduplication decision has been made; 907 is a source-uniqueness review candidate but remains a separate missing cel unless a separate, spatially verified decision authorizes otherwise.

All six were missing at this preparation snapshot. This report does not fill their mappings, approve generated artwork or claim the shot is finished.
