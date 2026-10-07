# Dance V11: Root Static Review

This is a draft interval [812,911), not a complete PV or artistic acceptance.

## Actually Inspected

- Final raw contact pages `exposure-starts-page-03.jpg` and `boundary-pairs-page-06.jpg` were opened and inspected after the v11 render completed. They cover the newly changed back-view cel900/901 and its immediate transitions.
- Final native crops `final-scoped/f0900-composite-fragment-native.png` and `f0901-composite-fragment-native.png` were independently opened at original resolution. The thin cool rear Klee beret arc is visible behind the large red foreground beret. No old green animal-hat arc or two-ear-shaped blue patch was seen.
- SHA256 comparison of all 11 contact pages against v10 found only those two pages changed. The other nine pages are byte-identical, allowing the previous recorded static inspection to remain applicable without repeating it. This does not mean every raw frame has received full-frame manual inspection.

## Separate Evidence

- Both final videos passed all 17 checks in the corresponding single/comparison verification JSON files: 99 decoded frames, source-exact video PTS, 4.125-second video boundary, original AAC packet payloads and permitted nearest-sample origin only.
- `review-report.json` audited all 99 raw outputs and declared-region equality. Its caption fields only cover registered subsets; empty fields or a technical pass do not certify all lyrics or matte boundaries.
- The night-layer owner's final scoped record reports 12 focused/regression tests passed, no changes outside the scoped ROI, and unchanged output hashes for899/902 and the previous902..910 layer registration.
- Final encoded caption review is owned and recorded separately under `qa/fast-fullpv-dance-caption-2026-10-04/encoded-v11/`; this root static record does not confer its result.

## Limits And Deferred Items

- Raw generated decoration, collar, hairstyle and limb-proportion differences across earlier/new cels remain draft issues. They are not made acceptable by timing or scope tests.
- Hidden sky and caption antialiasing are reconstructed; not all hidden original pixels or transparency can be recovered.
- No uninterrupted original-speed visual comparison or final full-film artistic acceptance was performed. All selected cels retain their explicit not-accepted state.
- The nine unchanged page hashes and the two newly inspected page hashes are retained in the final batch delivery manifest.
