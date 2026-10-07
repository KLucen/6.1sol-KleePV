# Middle Missing Continuation Handoff

Scope: star_dance canonical frames 2059, 2061, 2065, 2069, 2073, 2077, source cels cel-0379 through cel-0384. This packet is unaccepted draft material, not a finished PV segment.

## Call Accounting And Stop State

- Six real missing-cel calls succeeded and their six native tool outputs were copied without modification.
- Two repair jobs were prepared: f2065 hair-v2 was submitted and succeeded; f2077 hair-v2 was NEVER submitted.
- Total actual submitted calls: 7, all successful in this agent. Total successful native outputs: 7. This agent received no image-generation tool failure.
- Parent reported a selected-model capacity error elsewhere and explicitly instructed this agent to stop generation. The f2077 repair status is `queued_not_submitted_parent_stop`, not a failed call. No retry, model switch, CLI, or alternative API was used.
- f2065 v1 remains saved but unselected because it contains an extra middle blonde hair bundle. The single completed targeted repair is f2065 hair-v2.
- f2077 v1 still contains a third blonde bunch behind the near glove/collar and remains BLOCKED, unselected, and excluded from the proposal. It covers four source frames [2077, 2081).
- Five draft candidates are proposed for parent review: f2059 v1, f2061 v1, f2065 hair-v2, f2069 v1, f2073 v1. Their exposures total 18 source frames [2059, 2077). All `accepted` and `artistic_accepted` values are false.

## Evidence And Review

Source frames 2058, 2059, 2061, 2065, 2069, 2073, 2077, and 2081 were sequentially decoded and compared exactly with the saved source references. All eight comparisons passed. Actual adjacent source A/B, RGB difference, contour overlays, full sources, and original-size head/eye/hair, hand/cuff, and leg/boot/hem details were inspected before generation. Full generated outputs and source/new local comparison panels were subsequently inspected.

The two `source-new-consecutive-page-01.png` and `source-new-consecutive-page-02.png` contact pages were opened and visually reviewed after the prompt archive was sealed. The archive's earlier statement that consecutive-page review was pending describes its snapshot time; this note records the later review without rewriting that sealed archive.

Across the contact pages, the successive source turn is represented: left-facing profile, narrow left profile, rear three-quarter, full back, right profile jump with one closed eye, then front three-quarter with both closed eyes. The full-back candidate does not invent a face or eye. The right-profile candidate keeps the far hand hidden. The repaired f2065 has two rooted outer ponytails rather than three descending bunches. Both f2073 and blocked f2077 preserve their required closed-eye states.

There are visible draft continuity risks, not a final acceptance: varying head/hat scale, wider palms and boot silhouettes, changing collar/backpack visibility, approximate clothing hems, and differing glove treatment in f2065. Full-cel raw images also contain regenerated background, caption, star, and effect details. Original background, text, and effects must be restored by the source-layer compositor; these images are not pixel-locked source replacements. No final composition or actual-speed playback review was performed here.

## Saved Provenance

`promptset-7-successful-plus-1-unsubmitted.json` contains all eight full saved jobs, complete prompts, ordered reference roles, reference SHA-256/dimensions, call submission states, successful original tool paths, unmodified project copy metadata, and proposal hash. Validation failures at sealing were empty. Each generated image is 1672 x 941; resized versions were used only for review contacts, never substituted for native outputs.

Full prompts and ordered roles were saved before their respective calls. Reference hash/dimension metadata for f2059 and the completed f2065 repair was recorded after output, and that phase is disclosed in the archive. Other submitted first-pass jobs have before-call reference metadata. The planned f2077 repair has saved prompt and references but no output or call. The f2058 main-identity anchor itself is unaccepted; it is not described as an approved artwork.

Sealed archive SHA-256: `7caacd074e2ea5f350e11f9dacfcefa2cf768e5e9ade2aaa20ad7cc85f38f5ae`.

## Process Lessons

- Local source inspection boxes must follow the actual actor movement. A fixed head box from f2059 misses leftward-moving details later in this shot; full-source inspection and frame-specific native crops are required.
- Freeze the full prompt and ordered roles before calling, and store reference hashes before calling whenever possible. Preserve honest after-output metadata phases rather than retroactively claiming every reference was frozen earlier.
- Check two-ponytail topology where hands, collar, and hair overlap. A third hair bunch is a blocking identity defect; a single targeted full-cel repair should remove that bunch without changing pose authority.
- Keep missing-cel calls, completed repair calls, and planned-but-unsubmitted repairs separate in accounting. A stop instruction is not a tool failure and must not inflate successful or failed call counts.
- Minor costume or silhouette differences can be logged for parent review, but raw background/caption drift and static contact inspection do not establish final compositor quality or actual-speed continuity.

No shared compose, source-map, aliases, asset selections, global documentation, or manifest was modified. All command sessions used for this packet have completed.
