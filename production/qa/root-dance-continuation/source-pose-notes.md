# Source Pose Notes: f0835-f0856

Scope: source-only inspection of six canonical retained cels, their immediately
preceding source cels, actual RGB difference boards, and two-color contour boards.
No character artwork was generated. No shared asset selection, compositor, or
exposure table was modified. These are pose observations, not artistic acceptance.

All positions and left/right descriptions below are SCREEN-relative, not the
character's anatomical left/right. Coordinates are approximate native 1920x1080
visual landmarks, not a registration matrix or permission to deform artwork.
The whole-frame RGB counts include changing stars and compression; they do not
independently prove the number of distinct character drawings.

## Common Constraints

- Every one of these six target drawings has BOTH EYES CLOSED. Preserve two
  closed eyelid strokes; do not reveal red irises simply to reinforce Klee identity.
- All six have exactly two arms and two legs. Apparent movement of the long hair
  behind a sleeve must not turn into an extra hand, cuff, or backpack appendage.
- Yellow filled stars and cream outline stars are original effects/background,
  not costume ornaments. Keep their original frame-specific timing and layers.
- The bottom Japanese/Chinese captions are foreground. From f0843 onward a lower
  shoe/leg touches their vertical band. Restore lettering with a reviewed text
  layer, not a broad source rectangle that could copy the original foot.
- The current original frame is pose authority. A previous generated cel may
  supply only persistent identity/color/simplification, never freeze its face,
  hands, leg crossing, hair direction, or coat folds.
- Draw the full native target pose; no mirror, hold, flow, crossfade, or numeric
  interpolation substitutes for these independent drawings.

## f0835 / cel-0147

- Exposure: [835,839), PTS 34.792-34.958; previous canonical source f0831.
- Source: `source_refs/src-0381-f0835.png`.
- Whole-frame source delta: 271727 pixels with max-channel RGB delta >28.
- Facing: near-frontal three-quarter face biased toward screen right. The head
  is bowed slightly; torso has turned toward the viewer from f0831's right-facing
  side view. It is NOT another right-facing profile.
- Face: both eyes closed; small bent/pursed open mouth rather than a broad O.
  The visible cheek/jaw is below the bangs, around x880-1000, y310-382.
- Arms/hands: short foreshortened arms extend to either side. Screen-left hand
  is an explicit small open palm at about x685-760, y388-459, in front of the
  cuff/hair. Screen-right hand is only a narrow hand/finger silhouette just beyond
  the sleeve at x1060-1090, y409-461. Do not expand that far hand into a large palm.
- Legs: upper legs go diagonally down-right from the coat. Screen-left/back leg
  bends back down-left with a nearly vertical rounded shoe at about x850-938,
  y811-958. The other leg is the long diagonal down-right leg, ending in a
  side-on shoe at x1205-1345, y883-974. At the bend the short folded leg reads as
  a rear limb, not an extra third thigh or a second extended leg.
- Hair/occlusion: large hair volume sweeps screen-left behind head/shoulder;
  shorter front lock frames screen-right cheek. Preserve the hand in front of
  the screen-left hair/cuff and the small far hand at the screen-right cuff.
- Independent change vs f0831: full torso rotation, arms spreading and separating,
  rear folded leg dropping lower, long leg extending, head/eye contours moving,
  and main hair mass changing sweep. This is a major pose transition.
- Evidence: `qa/full-early-worker/resume-f0835-source-difference.png`,
  `qa/full-early-worker/resume-f0835-source-local.png`,
  `qa/full-early-worker/resume-f0835-source-head.png`.

## f0839 / cel-0148

- Exposure: [839,843), PTS 34.958-35.125; previous canonical source f0835.
- Source: `source_refs/src-0385-f0839.png`.
- Whole-frame source delta: 297924 pixels with max-channel RGB delta >28.
- Facing: front-facing face and chest. Torso slopes from higher screen-left
  shoulder toward lower screen-right hip; head is not the f0835 three-quarter.
- Face: both closed eyes, clearly enlarged vertical O mouth around x799-828,
  y308-338. Front cheek shapes are more symmetric.
- Arms/hands: arms now stretch into a broad near-T, not f0835 foreshortened arms.
  Screen-left sleeve extends to x454, hand x395-465, y431-470 and reads edge-on,
  thin and nearly horizontal. Screen-right sleeve ends around x1103, hand
  x1098-1149, y376-441 with separated upward fingers. Do not make both hands the
  same front-facing palm or mirror one to construct the other.
- Legs: screen-left leg bends toward the lower-left/center and its shoe is
  side-on near x780-929, y892-957. Screen-right leg extends diagonally right,
  foot lifted to x1180-1274, y775-924. The lifted foot shows a long near-vertical
  sole edge, unlike the flat side shoe in f0835. Legs separate after the hip;
  no knee-level X crossing is visible in this target.
- Hair/occlusion: main trailing hair now sweeps screen-right behind head and
  screen-right shoulder, a reversal from f0835's large screen-left sweep.
- Independent change vs f0835: arm length/foreshortening changes, chest rotates
  fully frontal, mouth opens, trailing hair reverses direction, lower left foot
  rotates side-on, and lifted right foot presents its sole edge.
- Evidence: `qa/full-early-worker/resume-f0839-source-difference.png`,
  `qa/full-early-worker/resume-f0839-source-local.png`,
  `qa/full-early-worker/resume-f0839-source-head.png`.

## f0843 / cel-0149

- Exposure: [843,848), PTS 35.125-35.333; previous canonical source f0839.
- Source: `source_refs/src-0389-f0843.png`.
- Whole-frame source delta: 326363 pixels with max-channel RGB delta >28.
- Facing: frontal chest with face subtly biased screen-right. Head/chest move
  left relative to f0839, while the head tilts slightly; do not freeze center.
- Face: both closed eyes; a small narrow vertical oval mouth. The mouth is
  smaller than f0839, not an unchanged broad O.
- Arms/hands: broad almost-horizontal outstretched arms; both hands now visibly
  splayed. Screen-left hand lies around x370-433, y401-463; screen-right around
  x1082-1137, y393-460. Right forearm slopes slightly down-right from shoulder.
- Legs: screen-left leg drops long and fairly straight to shoe x804-922,
  y940-1018, overlapping the original subtitle band. Screen-right leg kicks
  diagonally forward/right, knee moderately bent, shoe around x1104-1178,
  y808-949 presenting a narrow near-vertical sole edge. No visible X crossing.
- Hair/occlusion: main hair swings back to screen-left behind shoulder/arm.
  The narrow front screen-right lock descends across the cheek toward the collar;
  it must not become an extra scarf or an additional hand at the collar.
- Independent change vs f0839: figure shifts left, torso straightens, left leg
  lengthens/downshifts, right kicked foot lowers/rotates, hair reverses sweep,
  and hand silhouettes/mouth/coat pockets change. Captions now pass in front of
  the lower left shoe rather than occupying an entirely empty strip.
- Evidence: `qa/full-early-worker/resume-f0843-source-difference.png`,
  `qa/full-early-worker/resume-f0843-source-local.png`,
  `qa/full-early-worker/resume-f0843-source-head.png`.

## f0848 / cel-0150

- Exposure: [848,852), PTS 35.333-35.500; previous canonical source f0843.
- Source: `source_refs/src-0394-f0848.png`.
- Whole-frame source delta: 299666 pixels with max-channel RGB delta >28.
- Facing: almost frontal with face/jaw biased slightly screen-right. Body is
  more upright, head lowered to roughly y215-425, rather than the earlier y155.
- Face: both closed eyes. Mouth is an asymmetric curved/hooked open shape,
  roughly x730-765, y379-418; do not replace it with f0843's simple oval.
- Arms/hands: spread arms begin the upward lift. Screen-right arm clearly rises
  from shoulder toward hand x1040-1112, y339-419; screen-left arm is much closer
  to horizontal, with hand x341-407, y384-464. Both have separated visible
  fingers and small palms. Do not turn the slight V into overhead arms.
- Legs: this is the key CHANGE FROM FORWARD KICK TO REAR FOLD. Screen-left leg
  extends down with shoe x738-834, y1007-1070. Screen-right leg folds backward at
  its knee, shin nearly horizontal toward x946, y768-840, shoe x970-1050,
  y760-868. Rear lower leg/foot is separated from the straight leg by background;
  no knee-level X crossing. Do not retain the long f0843 forward kick.
- Hair/occlusion: long hair trails screen-left behind raised/extended sleeve;
  front cheek lock curves toward the mouth/collar. Hair tips behind the sleeve
  must not replace the open hand or generate an extra cuff.
- Independent change vs f0843: right leg reverses bend, head/upper body descend,
  arms begin rising, shirt/coat length and folds redraw, and the mouth changes
  from oval to hooked. Maintain the source's true lowered posture, not shorten
  the whole costume to simulate descent.
- Evidence: `qa/full-early-worker/resume-f0848-source-difference.png`,
  `qa/full-early-worker/resume-f0848-source-local.png`,
  `qa/full-early-worker/resume-f0848-source-head.png`.

## f0852 / cel-0151

- Exposure: [852,856), PTS 35.500-35.667; previous canonical source f0848.
- Source: `source_refs/src-0398-f0852.png`.
- Whole-frame source delta: 214686 pixels with max-channel RGB delta >28.
- Facing: frontal face/chest; head is more level and centered over collar.
- Face: both closed eyes, vertical round O mouth x716-746, y384-421. Unlike
  f0848, there is no hooked asymmetric mouth contour.
- Arms/hands: a more definite shallow V. Screen-left hand has risen to
  x350-409, y306-381; screen-right hand x1018-1085, y314-399. Fingers are spread
  and both palms visible. The shoulders/coat remain down around y425-485.
- Legs: screen-left leg stays long down to bottom shoe x732-832, y1009-1071.
  Screen-right thigh bends back/right, lower leg and boot pull inward: cuff
  near x900, y767-835; boot x909-982, y744-866. Gap between limbs remains;
  do not add an X crossing or lengthen the folded leg back into a front kick.
- Hair/occlusion: the large left trailing hair becomes lower/closer to torso.
  Front side locks are more balanced around face. Behind-sleeve hair remains a
  distinct rear layer and not a protruding gloved hand.
- Independent change vs f0848: left palm rises substantially, right palm rises,
  rear folded boot draws inward, mouth becomes circular, bangs/face recenter,
  and cuff/hem/pocket outlines redraw. Similar gross pose is not identical art.
- Evidence: `qa/full-early-worker/resume-f0852-source-difference.png`,
  `qa/full-early-worker/resume-f0852-source-local.png`,
  `qa/full-early-worker/resume-f0852-source-head.png`.

## f0856 / cel-0152

- Exposure: [856,863), PTS 35.667-35.958; previous canonical source f0852.
- Source: `source_refs/src-0402-f0856.png`.
- Whole-frame source delta: 196580 pixels with max-channel RGB delta >28.
- Facing: frontal face/chest with head slightly bowed and tilted; face appears
  a little lower while the hair mass becomes more symmetrically distributed.
- Face: both closed eyes; round O mouth x695-725, y392-427. Keep eyelid line
  position and downward head attitude, not f0852's level face copied unchanged.
- Arms/hands: shallow V grows steeper. Screen-left palm x337-415, y272-355 is
  higher than in f0852. Screen-right palm x992-1069, y299-379 pulls inward
  slightly. Both palms are open, visible, and attached to exactly one cuff each.
- Legs: screen-left long leg and lower shoe remain down. Screen-right knee is
  drawn inward and lower leg curls closer behind torso, with boot about
  x826-908, y725-852. The straight leg's inner contour visually covers the root
  of this rear bent leg more than f0852; do not draw an extra exposed thigh.
  Boot remains screen-right of the long leg, not crossed to its left.
- Hair/occlusion: long rear hair now hangs at both sides behind sleeves/body;
  tips on screen-left around x535-586, y498-554 and screen-right x810-856,
  y483-565. The earlier strong leftward streaming mass is no longer unchanged.
- Independent change vs f0852: both hands lift/inset, head/eye contours tilt,
  hair falls on both sides, rear leg/boot curl toward center, and coat side
  seams/pockets shift. It is a distinct retained cel, not a held f0852.
- Evidence: `qa/full-early-worker/resume-f0856-source-difference.png`,
  `qa/full-early-worker/resume-f0856-source-local.png`,
  `qa/full-early-worker/resume-f0856-source-head.png`.

## Generation/Review Order Recommendation

1. Treat f0835 and f0848 as geometry-critical anchors: torso/front turn in the
   former and forward-kick-to-back-fold reversal in the latter.
2. Generate each current source separately and use actual adjacent source delta
   boards. Do not use a prior full generated face as pose authority; all target
   eyes are closed even if earlier Klee drafts have exposed red eyes.
3. In the group contact review, track the screen-right boot through
   f0835 -> f0839 -> f0843 -> f0848 -> f0852 -> f0856: flat side shoe -> sole
   edge/front kick -> sole edge/lower kick -> rear fold -> inward rear fold ->
   tighter rear fold. This trajectory catches the largest likely frozen-pose bug.
4. Check each glove/cuff attachment, exactly two legs, rear-hair masking behind
   sleeves, and original foreground caption restoration at the bottom foot.
5. These notes cover static source/current comparisons only. Generated-cel
   structural review, all consecutive output frames, and actual-speed original
   versus replacement playback still remain separate required checks.
