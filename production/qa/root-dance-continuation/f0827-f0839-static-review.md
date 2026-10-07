# Root Continuation Draft Static Review

Reviewed: original/generated f0827, f0831, f0835, f0839 gloves-v2; immediate
source predecessors; explicit generated predecessors; source and generated
two-color contour overlays; four-frame group contact; f0839 glove repair crops.
All observations are STATIC. No actual-speed playback or all-frame output
inspection was performed by this reviewer. No artwork is artistically accepted.
No shared selections or core production files were edited.

## Glove Repair Drift

Both original draft files are 1672x941. Comparison uses RGB images normalized
to 1920x1080 with PIL LANCZOS. A changed pixel means the maximum absolute RGB
channel difference is greater than 28.

- Total changed pixels: 18686 / 2073600.
- Requested rectangles [330,395,460,510] and [1090,345,1210,455] contain 5177
  changed pixels; their complement contains 13509.
- The first requested rectangle clips a small part of the diagonal cream cuff.
  The second includes more of the curved cuff. After viewing original images
  and normalized tight crops, hand-only polygons follow the wrist seams and
  exclude sleeves/cuffs, head, face, torso and legs.
- Hand-only polygon union contains 4837 changed pixels; its complement contains
  13849. Exact polygons, both asset hashes, dimensions and counts are in
  `f0839-glove-repair-drift.json`.
- The visible repair successfully changes both hands from skin tone to brown
  gloves while retaining the gross hand silhouettes and two cuff attachments.
  However, the rest of the frame is NOT pixel-locked. Do not describe this as a
  hand-only pixel-preserving edit. Polygon bounds are manual QA regions, not
  approved production mattes; their counts are not artistic acceptance.

## f0827: Back Turn

Visible positive checks:

- The generated cel shows a genuine back view, not the earlier left-facing
  face left visible. No eyes or mouth are invented on the back of the head.
- Both spread hands are brown, each attached to one cuff. Two legs and boots
  are present; the folded boot shows its sole toward the viewer.
- Backpack is visible centrally on the rear torso rather than layered in
  front of a face. The source action's back turn is represented.

Unaccepted risks:

- Source pose versus draft head/shoulder/hip extent remains approximate;
  the rear hair silhouette is replaced by relatively compact twin tails and
  a large beret. Subsequent drafts must track these persistent volumes.
- The coat hem/shorts use a red frill topology that later f0839 loses.
- Generated background/absence of original caption and yellow stars is not
  itself an output-compositor finding. Original layers must still be restored
  and checked in the actual composite, especially around boots and gloves.

## f0831: Right Side Turn and Crossed/Folded Legs

Visible positive checks:

- Genuine right-facing side view with closed visible eyelid and small mouth.
- Near arm projects toward screen-right and only the appropriate forward hand
  is prominently visible. There is no obviously invented extra large far hand.
- The upper bent leg lies over the other diagonally extending leg; two boots
  remain readable and gross leg-crossing direction follows the source.

Unaccepted risks:

- Two separate white feather/horn-like extensions appear on opposite sides
  of the hat. This is not the single badge-attached feather topology shown in
  the preceding f0823 or following f0839. Do not silently treat this as stable
  character identity; the hat decoration requires a group topology check.
- Backpack changes from a square rear pouch in f0827 to a rounded side pouch.
  Some change follows viewpoint, but strap attachment, depth and size are not
  yet verified across the turn.
- Costume and boot volumes, hand simplification, and head/eye placement still
  differ from the current original. Static action resemblance is not a pass.

## f0835: Front Three-Quarter Transition

Visible positive checks:

- Both eyes remain closed, the near screen-left palm is visible and brown,
  and the far screen-right hand is represented as a small narrow exposure.
- Two legs/boots persist with the short back-folded leg and long screen-right
  extending leg; no obvious third limb was observed.

Unaccepted risks:

- The actual source f0831 -> f0835 turns the chest and face distinctly toward
  the viewer, spreading the arms into foreshortened side projections. The new
  draft f0835 retains too much of f0831's strong right-side head/coat attitude,
  making the turn smaller than in the original. The source/current contour
  board makes this under-rotation visible. Do not call the pose matched.
- The near palm/cuff appears enlarged relative to the source's compact hand;
  exact glove/cuff depth and far-hand occlusion still need scrutiny.
- The same two white hat extensions from f0831 persist. The chest clover
  appears in a much smaller form than f0839, while the buttons are still absent.
- Twin-tail direction and rear backpack volume largely follow f0831 instead
  of fully answering the source's changed hair/shoulder/torso orientation.

## f0839 Gloves-v2: Frontal T Arms and Forward Kick

Visible positive checks:

- The face/chest now read frontal, both eyes are closed, and the O mouth is
  present. The source's large front-facing change is not frozen as f0835.
- Screen-left hand remains a thin edge-on gesture; screen-right palm is open
  with separated raised fingers. Both are brown after repair.
- Left/downward boot is side-on; lifted screen-right boot shows a long sole
  edge. The gross change from f0835's long flat-side shoe to a lifted kicking
  sole is represented. There are still exactly two legs.

Unaccepted risks:

- f0835 -> f0839 changes the hat decoration from two detached white extensions
  to one tall badge-attached feather; hat clover and round badge also reappear.
  The topology shift is stronger than a normal perspective change alone.
- Two large cream chest buttons appear; chest clover enlarges substantially;
  shorts change from frilled to plain; twin tails become short and symmetric.
  These simultaneous costume/hair detail changes create a visible continuity
  risk even where the gross action is correct.
- Coat/hat/backpack shading and contour extent remain different from source
  simplification. Native source hand/leg/head geometry is only approximate.
- The glove repair has measurable drift outside the hands, as reported above.

## Evidence and Handoff

The requested existing `full_early_resume.py contact` was run on all four cels.
It read its own private ledger/manifest for preceding generated assets. At
inspection time f0831/f0835/f0839 therefore had black preceding-draft panels.
Those original helper boards were left intact. Private supplemental boards
explicitly insert the actual root predecessor without editing shared state:

- `f0827-explicit-neighbor-static-contact.jpg`: prior Klee f0823, current f0827.
- `f0831-explicit-neighbor-static-contact.jpg`: prior Klee f0827, current f0831.
- `f0835-explicit-neighbor-static-contact.jpg`: prior Klee f0831, current f0835.
- `f0839-explicit-neighbor-static-contact.jpg`: prior Klee f0835, current gloves-v2.
- `f0827-f0839-source-and-draft-group.jpg`: originals above, drafts below.
- `f0827-f0839-static-evidence.json`: source/draft paths and asset hashes.
- `f0839-glove-repair-tight-crops.png`: before/after annotated ROI and delta.

Highest-priority next review gates: f0835 source-led body/head turn, consistent
hat feather/badge topology across all four, coat button/clover/shorts continuity,
then composite caption/effect masks and actual-speed group playback. Continue
production without counting any of these drafts as artistically approved.
