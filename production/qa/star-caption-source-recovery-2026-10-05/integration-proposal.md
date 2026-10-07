# Root Integration Proposal

This proposal implements the explicitly authorized alternate real Japanese
glyphs for the already registered frames `[1037,1043)` only. It does not enlarge
`REGISTERED`, mutate source timing, or opt future standing cels into this layer.

1. Create a production helper from the pure function in `alternate_phase2_layer.py`.
   The function accepts an original phase dict and explicit NPZ path, has no
   import of `star_gestures_layers`, and does not mutate the original arrays.
   Do not import `authorized_star_caption_candidate.py` from the shared helper:
   that private wrapper imports the original module and would make a cycle.
2. In existing `caption_layer(2)`, obtain the old `_changed_word_layer` result to
   retain its Chinese layer, then return the pure builder's result using
   `ROOT / "qa/star-caption-source-recovery-2026-10-05/authorized-alternate-japanese-f3402.npz"`.
3. In `restore_star_captions`, use
   `ink = layer.get("ink_rgb", layer["foreground"])` for both the contrast `gap`
   and blend expression. Keep the current `edited` restriction, character-only
   contrast ring and `target[layer["core"] & paint] = original[...]` assignment.
   The builder clears only Japanese source-core flags; Chinese source cores
   remain unchanged. Earlier phases receive the same old foreground vector.
4. Keep `star_caption_extent` based on the dynamic returned `layer["region"]`.
   The registered alternate extends only the phase-2 right AA support to x1213;
   it does not alter caption timing or crop/scale the character.
5. After shared compositor registration, compare all 35 final raw frame BGR
   against `fNNNN-authorized-private-compose.png`, then run the existing frozen
   cyan and earlier registered interval regressions. Render and independently
   review encoded subtitle crops. Do not label the six Japanese frames as exact
   original RGB restoration, or the technical static gate as artistic acceptance.

Private executable oracle: `authorized_star_caption_candidate.py`.
Evidence: `authorized-private-35frame-report.json`, `static-review.md`, all five
`authorized-native-caption-page-*.png` and four `authorized-canonical-body-page-*.png`.
