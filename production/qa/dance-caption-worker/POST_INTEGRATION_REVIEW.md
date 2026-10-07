# Actual Dance Caption Integration Review

## Inspected Version

The final inspected compositor excludes generic overlay at all y>=910 in source `[831,863)`. It keeps only the observed donor/current warm-core intersection from the current source RGB, without expanding alpha. This worker did not edit shared compositor, glyph layer, review pipeline, or asset selections during integration review.

- `compose.py` SHA256: `57c82dc1d7fc309deb6edd9e8b1abe8f1834d98f66febb4ac4e037334f6538bc`.
- `dance_caption_layers.py` SHA256: `d8ad7799d2a93ab72a24bf01c6a0e46dcf89b18a65ae79663807659e92d3eef4`.
- `asset_selections.json` SHA256: `1f5db0999a7700a5cd83ce477bf95177cba8bfb8f71a8040b8a722b8dcf32047`.
- Current phase report SHA256: `a21aa2c4c990c1d4084c96bccb70856482658d38f340c3a1dcbaac0b7540b308`.
- Selected cels were read from current selections: f843 v1, f848 source-native v2, f856 v1.

Five actual integration tests passed in 12.984 seconds. Tests cover interval-outside equivalence, forced generic-graphics exclusion for the entire bottom band, alpha-only dance-layer modification, and inclusion of every actual modified pixel in the declared masks. Exact transcript and provenance are in `post-bottom-band-exclusion/`.

## Old Cuff/Shoe Confirmation

The earlier f843 pale island at `(778,924,800,951)` was not present in the selected Klee cel. It matched the original dancer's pale cuff edge and disappeared when only the original generic bottom-overlay path was disabled. Before the final exclusion, this rectangle had 67 exact source-graphics pixels; all 67 changed by more than 20 RGB channel levels under the counterfactual. f848/f856 also had 21/5 source-graphics copies in the same rectangle.

After final bottom-overlay exclusion, those source-graphics copies are zero for all three inspected cels. Disabling y>=910 generic overlay again changes zero pixels over each entire composed frame, confirming that this path is already excluded. In all three actual outputs, undeclared modified pixels are zero.

This validates removal of the identified generic-overlay residue, not the absence of all possible old-character residue anywhere in the scene.

## Native Crop Observations

The three native 560x185 crops and three 4x nearest-neighbor cuff-detail boards were individually viewed. Native boards contain source / current selected cel / actual composite and are retained in `post-bottom-band-exclusion/`.

| Frame | Readability And Residue | Remaining Uncertainty |
| --- | --- | --- |
| 843 | Chinese line readable over the new brown boot; identified pale source-cuff island absent. | Japanese beginning/end distinguishable, but complex middle glyphs visually merge with the pale background star. |
| 848 | Chinese first characters and full line readable over the new boot; no separate old-shoe/cuff island visible in this crop. | Japanese star-crossing counters are dense; no claim of exact complete glyph shapes. |
| 856 | Chinese line readable; no distinct old-shoe outline visible in the inspected crop/detail. | Middle Japanese glyphs remain low-contrast against the original star; projected AA and counters remain uncertain. |

The observed RGB-core preservation is a bounded improvement over constant cream color. A donor `source_core` includes points held at alpha=0.9, so it is not a mathematical proof that all copied core pixels are originally opaque. Some compressed source background mixing remains possible even at observed letter coordinates.

## Explicit Non-Pass Items

The full 32-frame warm-core support result remains **false**, with 63-1273 raw warm candidates per frame outside donor alpha. These include old-shoe/skin false positives and unresolved Japanese/star/edge candidates. Stable donor-subset equality must not replace or hide this result.

This review is limited to raw-composite static crops from three current cels. It does not establish final encoded contrast, complete Japanese glyph correctness, all-frame old-character removal, pose/costume continuity, or actual-speed acceptance. No character cel was artistically accepted.
