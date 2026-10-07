# Back-View Repair900/901: Final Scoped Composite

## Registration And Source

- Timeline: `timeline-dance-812-911-fast-draft-v11.json`; only the new `fast-fullpv-dance-f0900-rearhat-v2.png` [900,902) is registered for the added branch. PNG SHA256: `276249a21a63d3f52558fc501741738fb06cbca53592172c2a29ae505974cd1e`.
- Final helper SHA256: `746a0e2c6b586a108c4cb8f35902184ee8327232acc0ea808f9e5aa197921ac7`.
- Source899/900/901/902 were independently saved after sequential actual video decoding from frame0 through902. Each artwork and exposure range is recorded separately in `actual-fixed-v2-boundary-evidence.json`.
- The unchanged original candidate028 baseline and the new-v2-but-unscoped composite evidence remain in the parent folder and `fixed-v2/`, respectively. They are historical comparison evidence, not current selections.

## Blocking

- No remaining old rear animal-hat blocking fragment seen in the final 900/901 native composite/ROI. The previous two-ear-shaped blue patch and thin green arc are gone. The new small cool burgundy Klee beret arc remains behind the foreground red beret; no rear face is exposed.
- Actually inspected: new raw PNG; final900 full native composite; final901 native ROI; and actual899 -> 900 -> 901 -> 902 composite boundary contact. This is static boundary evidence, not original-speed acceptance.

## Scope And Regression

- Only checkedROI `[1125,0,1490,285]` is repaired. Source and generated contours are independently established inside it. Generic masks and all composite pixels outside it remain unchanged.
- Current SOURCE-visible neighboring night sky supplies the smooth reconstruction under vacated old anatomy and measured compressed fringe. No generated-sky patch, pure-color fill, unverified donor or new character drawing is used.
- Compared with unscoped-v2 baseline, frame900 changes13393 pixels and frame901 changes13391 pixels. Each has zero changed pixels outside the checkedROI.
- Adjacent899 and902 full composites are byte-identical to their baseline outputs. All 9 prior registered902..910 actual composite BGR hashes remain byte-identical.
- `test_backview_transition_layers.py` plus `test_night_transition_layers.py`: 12 tests, all PASS after integration. This includes scope gates, mask merge/outsideROI invariance, new rear/front hat pixel preservation, old AA samples, source-derived non-flat local reconstruction, and the full nine-output hash regression.

## Nonblocking / Measurement Limits

- The strict green core count is zero in both final900/901, but this was not used alone to decide correctness. Native views supply the separate contour/seam evidence.
- A wider greenish threshold also selects 16 unchanged source pixels at `[1466,34,1470,38]`. This is the actual original sky star to the right of the old hat, not remaining hat fringe. It is intentionally preserved, not erased to achieve a numerical zero.
- Four pixels at `[1144,26,1148,27]` equal generated blue and are part of a tiny closed new-edge gap. No two-ear anatomy or visible old contour is present there in the native final ROI. This microscopic difference is recorded without another redraw or global segmentation edit.
- Reconstruction under invisible anatomy is inferred current-source gradient, not donor-exact original sky.

## Unconfirmed

- Original-speed motion and full-film final acceptance remain separate. No artwork/exposure has been marked accepted by this work.
- Caption layers were kept frozen and are independently audited by the caption owner. The added branch does not alter the caption band or mask outside the checkedROI.
