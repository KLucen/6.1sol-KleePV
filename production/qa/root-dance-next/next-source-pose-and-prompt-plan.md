# Next Four Source Cels: f0863-f0880

## Verified Scope and Exposure

Source-only work. Four canonical retained cels were cross-checked against both
`source_map.json` and the latest coverage/progress snapshots. Each raw candidate
within the listed exposure has the same retained cel ID and an identity source
transform. Their aggregate bounds match the progress manifest exactly.
The strict-source exposure table is retained; no alias or reuse was approved.
The global 689-cel count remains a conservative upper bound, not a certification
of 689 unique drawings. These four targets each have clearly observed coherent
pose/hand/face/boot changes, not merely different full-frame noise values.

| Target | Retained cel | Exact exposure [start,end) | PTS [start,end) | Prior canonical source |
| --- | --- | --- | --- | --- |
| 863 | cel-0153 | [863,868), 5 frames | [35.958,36.167) | 856 |
| 868 | cel-0154 | [868,873), 5 frames | [36.167,36.375) | 863 |
| 873 | cel-0155 | [873,880), 7 frames | [36.375,36.667) | 868 |
| 880 | cel-0156 | [880,887), 7 frames | [36.667,36.958) | 873 |

Coverage snapshot at preparation: contiguous available prefix ends at 863,
so f0863 is the first missing selected cel. All four targets were unselected.
Exact source-map candidate ranges, source asset hashes, dimensions, coverage
summary, PTS and reference paths are in `next-source-reference-queue.json`.

## Caption Phase: No Change at f0863

The source f0862 -> f0863 boundary does NOT change the bottom Japanese/Chinese
lyric phase. The same two lines remain visible in f0856, f0862, f0863, f0867,
f0868, f0872, f0873, f0879 and f0880. All nine source crops were inspected in
`f0856-f0880-source-caption-phase-contact.png`.

The text is stationary foreground material over a changing shoe/cuff/background
underlayer. Different pixel values around the leading glyphs at the foot do not
mean a new lyric line. Original antialiasing, compression and foot occlusion
can change the local RGB crop even without a caption phase change.

Do not ask the image model to typeset or reinterpret these lines. Restore the
original source-frame lettering independently, including its edges. Use a
reviewed glyph matte rather than a full lower rectangle that can copy the old
character's shoe or cuff. Both boot masks and the bottom text require encoded
consecutive-frame checks. f0880 brings the second shoe further into the text
band, so this is not an entirely empty caption strip.

## Reference Roles and Common Prompt Constraints

- Current original full frame is authority for pose, head/body placement, arm
  angles, palm visibility, elbow/knee/boot geometry, expression and occlusion.
- Current source head/hand/boot crops clarify those same details. They are not
  new artwork or permission to enlarge the head, palm, sleeves or shoes.
- Actual source predecessor/current RGB and two-color contour boards identify
  the direction and amplitude of the drawing change. Also use direct f0856 ->
  target source boards when the later action could be wrongly frozen to f0856.
- A selected f0856 Klee draft may supply identity and simplified colors only.
  It is unaccepted and must not determine the target head, wrists, bent leg or
  costume defects. In particular do not canonize its center seam/side clover.
- All four targets have BOTH EYES CLOSED. Retain two closed eyelid strokes;
  do not expose red irises to demonstrate identity. Mouth size/tilt changes
  per source, and must not be held unchanged across the four targets.
- Exactly two hands and two legs, with the source-specific visible portions.
  Every exposed hand region is a brown glove, including narrow fingertips.
  No extra hand or cuff may emerge from a ponytail, backpack or rear hair tip.
- Klee has two short ponytails and one badge-attached hat feather in this
  established simplification. Keep attachments and volumes traceable; do not
  add a raised ivory forelock or grow the original's long hair onto Klee.
- Keep a consistent coat/collar/hem/shorts/boot design. Do not toggle chest
  buttons, collar lobes, center seams, clover position or shorts frill merely
  because a previous unaccepted draft happened to contain that variant.
- Preserve original scene extent, purple background, star positions, shot
  timing and text/audio via source layers. No holds, mirrors, optical-flow
  warps, morphs, aliases or extra exposures substitute for the four drawings.

## f0863: Wrists Turn Edge-On and Rear Boot Tucks

Source authority: `source_refs/src-0409-f0863.png`.

Observed pose and change from f0856:

- Face/chest remain frontal. Head moves slightly upward and the head/eyelid
  tilt changes; both eyes stay closed. Round O mouth is small and low under
  the cheeks, around native x695-721, y368-395.
- Arms remain a shallow raised V, not overhead. The important local change
  is BOTH WRISTS: upright open palms from f0856 rotate outward into thin,
  nearly horizontal/edge-on finger silhouettes. Screen-left hand is around
  x348-418, y270-322; screen-right around x998-1076, y310-360. Do not leave
  the previous up-pointing palm silhouettes unchanged.
- Screen-left long leg descends in front and the lower shoe pivots/rolls to
  a smaller, more left-facing shape around x711-819, y996-1060.
- Screen-right rear folded leg pulls inward again. Only its short bent lower
  region/boot is exposed to the right of the long leg around x800-890,
  y726-860; its root is partly covered by the long leg. Do not invent another
  thigh or maintain the wider f0856 rear foot position.
- Rear source hair shifts around the two shoulders; Klee short ponytails
  should answer that turn without being replaced by the original's long hair.

Executable prompt emphasis:

```text
Redraw only the performer as Klee in the CURRENT original f0863 native pose.
Use f0856 only for persistent identity/color, never its pose. Keep both eyes
closed, a small round O mouth, and the slightly lifted current head. Preserve
the shallow V arms but rotate BOTH wrists to the current thin, outward,
nearly edge-on gestures: no held upright palm. Every exposed finger is brown
glove, one hand per cuff. The long downward leg stays in front; the other
leg is tightly bent behind, with only its current short outer boot visible.
Match current shoe rotation and foreground-caption contact. Exactly two
short ponytails, one attached hat feather; no ivory upturned forelock.
```

References in this QA folder:
`f0863-source-ab-rgb-contours.png`, `f0863-source-local-ab.png`, and the
three `f0863-source-head-eyelids-mouth/hands-cuffs/legs-boots-caption-contact.png`
crops. Actual immediate-neighbor max RGB delta >28 count: 233319 pixels;
the existing delta helper's >=28 count: 236712. Both counts include stars.

## f0868: Open Palms Return; Bent Limb Foreshortens

Source authority: `source_refs/src-0414-f0868.png`.

Observed pose and change from f0863/f0856:

- Head is slightly more raised/tilted than f0863, still frontal. Both eyes
  remain closed; the O mouth enlarges into a vertical oval near x692-722,
  y325-367 rather than retaining the small f0863 mouth.
- Both arms retain a broad shallow V, but palms turn outward and become much
  larger OPEN SPREAD gestures. Screen-left palm around x326-416, y235-345
  has an upward thumb; screen-right around x988-1079, y270-366 has a raised
  thumb and fingers spreading outward/down. Do not copy f0863's thin hands.
- The long leg stays down/front; ankle/shoe is compact and partly behind the
  foreground caption near x704-827, y991-1055.
- The other leg retracts/foreshortens closer below the hip. It reads as a
  rounded bent knee/thigh and a small shoe below it near x752-834, y786-850,
  not as a long horizontal shin ending far to the right. Keep two legs but
  allow source-authored hiding of the rear leg root/short lower segment.
- Coat folds and rear source hair change coherently, with larger trailing
  volume at screen-left. Keep Klee's short ponytail roots; do not freeze their
  tip direction from f0856 or copy source long-hair length.

Executable prompt emphasis:

```text
CURRENT f0868 source is geometry/expression authority. Both eyes remain
closed; enlarge the current vertical O mouth and use the source's current
head tilt. Redraw both wrists as open, spread brown-gloved palms with raised
thumbs; they are NOT f0863's thin edge-on fingers. Keep the shallow V sleeves,
one glove at each cuff, and exactly two legs. The rear bent limb is tightly
foreshortened below the hip, with the small current shoe under the knee;
do not extend a long rear shin or add an extra exposed thigh. Preserve the
front long leg and current ankle/shoe occlusion by the unchanged captions.
```

References: `f0868-source-ab-rgb-contours.png`, `f0868-source-local-ab.png`,
`f0856-to-f0868-source-ab-rgb-contours.png`, plus the three target crops.
Immediate-neighbor max RGB delta >28 count: 206070; >=28 helper count: 209631.

## f0873: Asymmetric High Arm and Reopened Forward Kick

Source authority: `source_refs/src-0419-f0873.png`.

Observed pose and change from f0868/f0856:

- This is a MAJOR NEW EXTREME, not another small shallow-V variation.
  Upper body/head shift substantially screen-right. Head/hat and closed
  eyelid line tilt clockwise; mouth is a vertical tilted O around x965-986,
  y356-386. Do not keep the previous centered/upright head or eye line.
- Screen-left arm rises steeply diagonally up-left to an open spread hand
  around x671-755, y140-226. Screen-right arm slopes downward/right to a
  spread hand around x1225-1286, y552-632. This high/low arm asymmetry must
  replace the two matched shallow-V arms. The head/hat lies below/right of
  the raised hand, not between two hands at the old height.
- The long screen-left leg drops almost vertically to shoe x698-844,
  y974-1052. The other leg UNFOLDS into a long forward/down-right kick, shoe
  around x1144-1255, y862-980 with a long diagonal sole edge. No retained
  little tucked boot under the hip; no knee-level X crossing.
- Main source hair streams screen-right behind the lowered arm. Respond
  with Klee's connected short ponytails, not long loose original hair.
- Yellow stars cluster near the raised hand and below the lowered hand;
  they are original effects, not extra hand details or costume emblems.

Executable prompt emphasis:

```text
Use CURRENT f0873 original pose exactly as the action target. It is a new
asymmetric extreme: screen-left arm reaches steeply upward-left, screen-right
arm extends downward-right, both visible hands brown open gloves. Move head
and chest to their current right-shifted positions; match clockwise closed
eyelid/head tilt and the current tilted O mouth. Do NOT freeze f0856/f0868
centered head, shallow V arms or tucked rear boot. Redraw the formerly tucked
leg as the current long forward diagonal kick with the rotated sole edge;
the other leg drops long at screen-left. Exactly two hands and two legs.
```

References: `f0873-source-ab-rgb-contours.png`, `f0873-source-local-ab.png`,
`f0856-to-f0873-source-ab-rgb-contours.png`, plus the three target crops.
Immediate-neighbor max RGB delta >28 count: 438158; >=28 helper count: 440775.

## f0880: Higher Raised Arm and Lowered Second Foot

Source authority: `source_refs/src-0426-f0880.png`.

Observed pose and change from f0873/f0856:

- Body leans more to screen-right, head/eyelids/hat tilt further clockwise.
  Both eyes are closed. The mouth becomes smaller and tilted near x1005-1025,
  y383-405; do not reuse the larger f0873 vertical O.
- Screen-left raised arm becomes closer to vertical, reaching the open palm
  around x777-864, y105-193. Screen-right arm remains downward/right, its
  palm around x1232-1288, y611-690. Raised hand moves right/up relative to
  f0873, while the lowered hand moves down. These changes are not whole-frame
  rigid rotation; sleeve shape, cuffs and hand angles also redraw.
- Screen-left leg stays long with shoe x689-837, y974-1052. The screen-right
  forward kick LOWERS substantially into a wider two-leg standing/open
  stance, foot around x1081-1186, y935-1015. Both legs are long/separated;
  do not preserve the little folded boot from f0856 or the higher f0873 kick.
- The second foot now reaches further into the lower text band. Original
  foreground lettering must remain independently restored over boots/cuffs.
- Source hair falls more downward/right than f0873's broad rightward sweep.
  Klee ponytail tips may respond, but fixed roots, short length, one feather
  and identical costume topology must be retained.

Executable prompt emphasis:

```text
CURRENT f0880 source alone determines pose, crop and expression. Raise the
screen-left arm closer to vertical and move its brown open palm up/right;
lower the screen-right open glove to the current down-right position.
Increase the body's rightward lean and clockwise head/closed-eyelid tilt,
with the smaller tilted current O mouth. BOTH legs are now long and separated:
lower the previously high screen-right kicked shoe into the current open
stance. Do not retain f0873's high kick or any f0856 tucked rear boot. Match
both cuff/boot rotations and their foreground-caption contact without
inventing another foot or changing the original text.
```

References: `f0880-source-ab-rgb-contours.png`, `f0880-source-local-ab.png`,
`f0856-to-f0880-source-ab-rgb-contours.png`, plus the three target crops.
Immediate-neighbor max RGB delta >28 count: 287357; >=28 helper count: 290279.

## Next-Round Gates

1. Generate each current source target independently and immediately preserve
   full prompt/reference roles/output. The first exposure is f0863, not 856 held.
2. Review gloves/cuffs, two-leg depth, sole angles, head/closed-eye placement,
   short-ponytail attachment and single feather against each CURRENT source.
3. Review source/new group sequence through f0856 -> 863 -> 868 -> 873 -> 880:
   wrists thin -> open palms -> asymmetric high/low arms; tucked boot ->
   foreshortened shoe -> unfolded forward kick -> lowered open stance.
4. Keep costume topology consistent across the group. Do not propagate the
   previously documented unaccepted seam/button/collar variations as templates.
5. Verify all consecutive composite frames and unchanged lyric phase, then
   perform actual-speed original/new playback. No such generated/composite
   or artistic check is completed by this source-only plan.

Only files under `qa/root-dance-next/` were written in this preparation.
No generation call, selected asset change, core edit, alias, or exposure change.
