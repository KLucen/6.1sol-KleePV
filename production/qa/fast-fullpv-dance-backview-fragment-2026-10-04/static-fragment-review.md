# Back-View Rear Hat Fragment: Frames 900 And 901

- Source frames 900 and 901 were actually decoded in order from the original video, after sequentially advancing from frame 0. Both are saved at native 1920x1080. Their source pixel hashes are distinct; no seek or substituted cel was used.
- Actually inspected: source900 native, raw candidate028, the native source/generated/current-composite fragment contact, source901 native fragment, source mask, and source901 full current composite.
- Blocking: both current composites and the raw `candidate-028-clean.png` itself retain the original rear cyan animal hat, its two green ears/lobes, and the green descending rim. This is source anatomy, not a star, not merely a generic-matte hole.
- Source visible cyan/green anatomical core bbox is `[1143,6,1472,269]` for each actual frame. The generated/current-composite anatomical core is `[1146,4,1469,255]`. Coordinates are native x0,y0,x1,y1, with the final pair exclusive.
- Those strict color-core bounds exclude compression/AA fringe. For bounded redraw/inspection, allow the small enclosing region `[1125,0,1490,285]`; do not stop at y80. This enclosing region is an evidence/inspection region, not a rectangular paint instruction.
- The foreground back-view head/beret hides all rear eyes, mouth and face. Only the rear hat fragment is visible. A replacement must preserve that foreground occlusion and replace the exposed cool rear anatomy with a Klee beret/feather sliver, without revealing a face.
- No `compose.py`, registration scope, timeline, selection, exposure or acceptance state was changed by this inspection. Root owns the one bounded source-led redraw. Final replacement/actual-composite verification remains pending.

`actual-fragment-evidence.json` records separately labeled source/artwork/composite hashes, ranges and bounds. Native original images and mask/crop evidence are included. The masks are analytical cyan/green core detection only, not a final character matte.
