# Registered Dance-To-Night Matte Review

## Scope And Evidence

- Scope: source frames [902, 911), all 9 actual exposures, 6 registered artwork filenames and their exact exposure ranges. Timeline: `timeline-dance-812-911-fast-draft-v10.json`. No selection, alias, timing or acceptance changes.
- Original video was decoded sequentially from frame 0 through 910. Native source, resized artwork, generic-matte comparison, actual integrated composite, source/new matte and repair support are saved separately for every frame.
- Final module SHA256: `e17867cfca7c7f1012b9cd9d94b7a7e0461a05a134d75e9ba2e960fec2ec58cb`.
- `actual-native-evidence-902-903-904-905-906-907-908-909-910.json` holds distinct source pixel hashes, artwork pixel hashes, exposure ranges and actual composite pixel hashes. Source RGB hashing and generated BGR hashing are explicitly labeled.
- The final integrated native composites were actually viewed individually: 902, 903, 904, 905, 906, 907, 908, 909, 910. Native generated 902 and 907 and corresponding source/matte evidence were also viewed.

## Blocking

- No remaining night-matte blocking defect identified in these final 9 static composites. The previously cut cyan forehead/face, blue feather outline and hat contour remain present. Original green hat/profile linework and its broad compressed fringe have been removed in vacated support.
- Each image is segmented independently. New hat/feather geometry is not clipped to the old source silhouette. Final artwork pixels inside the new mask remain artwork-exact before separately registered caption restoration.

## Nonblocking / Limits

- Invisible vacated background is reconstructed, not observed or donor-exact. A robust smooth gradient is fit to visible sky in the actual current source frame, with locally measured boundary residuals. Only old silhouette removal support outside the new silhouette receives this reconstruction. Generated sky is not used as a cleanplate.
- Source frame 1007 was actually inspected and contains two huge characters in a different scene. It was rejected as a cleanplate. Source frame 911 also contains substantial anatomy and was not treated as a blank donor.
- All unedited source sky, stars and moon outside repair/caption support remain pixel-exact. This numerical result describes edit scope only, not artistic correctness. Native visual inspection supplies the separate contour/seam evidence.
- The existing 902/905 pompon-patterned collars versus new 903/907 paired-leaf collars are a raw-art cross-cel identity detail, not a new matte edit. They were not repainted here.

## Unconfirmed

- Original-speed playback, motion acceptance and full-PV completion are not established by this static review.
- Caption legibility is independently owned by the caption pass. The new subject masks are passed to that layer, but anatomy scope tests do not assert readable Japanese/Chinese text. The pale front clothing still needs the caption owner's separate contrast evidence.
- None of these artworks or exposures has been marked accepted by this work.

## Focused Tests

`python -m unittest test_night_transition_layers.py` from `production`: 6 tests, all PASS.

- Exact filename/range registration and rejection of historical 907 v1.
- Unknown asset, out-of-range frame and unspecified frame are exact no-ops.
- Actual 907 blue feather, forehead, face and coat are included; sky/moon excluded.
- Actual 902 deep-blue feather remains anatomy, not sky.
- New anatomy pixels and unedited source star/moon region remain exact.
- Vacated support receives a non-flat source-derived gradient, not generated sky.

## Lessons

- Night-colored anatomy cannot reuse a broad HSV sky threshold. Border-connected sky plus closed line barriers protects interior blue faces; dark blue linework must not be admitted as bright sky.
- Original and replacement silhouettes must be established independently before deciding the vacated region. Using the old contour to trim the new hat causes truncation.
- Source compression expands old line fringes beyond the obvious drawn edge. Removal support needs that measured fringe, while source-sky sampling must exclude it so reconstruction does not carry a faint old contour back in.
- A filename/family suggesting empty night sky does not establish a cleanplate. Inspect the actual source exposure first.
- Compare every actual exposure at native size after integration; declared-mask equality and a handful of keyframe contacts alone cannot establish a correct matte.
