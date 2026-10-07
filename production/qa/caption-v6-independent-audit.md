# Opening V6 Independent Caption Audit

Audited: 2026-10-03 17:47 +08:00. No shared compositor, registry, asset selection, or generation files were modified by this audit.

## Evidence

- Raw report: `opening-666-review-caption-fixed-v6/review-report.json`, SHA256 `0cde647e0cbf62e4b1d2d46baeba643ab69ca89688b90d8beadd234559669aa8`.
- Encoded timing/audio report: `klee-opening-27s75-comparison-draft-v6-technical-verification.json`, SHA256 `c004f95835b5d978b74aa1cfa72b39f0b6065b80db1aaf7dd3cc3bada9991808`.
- Lessons: `../PRODUCTION_LESSONS.md`, SHA256 `e93c7ca3a8808a8917b00afa122e65d909b27c1bdf9c56c3ba043002cd259489`.
- Command run in production: `C:\Users\KLucen\anaconda3\python.exe -m unittest test_caption_composite test_caption_diagnostics -v`. All 15 tests passed in 7.628 seconds.
- Independently recomputed every provenance SHA256 recorded by the raw report: no stale input hash found at audit time.

## Result And Exact Scope

The raw review contains all 666 frames in source interval `[0,666)`. All six recorded technical checks pass. The encoded verifier separately passes 666-frame decode, exact source PTS and 27.75-second video boundary, dimensions, and copied AAC packet checks. These are technical checks, not artistic acceptance.

Caption diagnostics contain 512 field records on 508 frames:

| Inclusive frames | Field | Region x0,y0,x1,y1 |
| --- | --- | --- |
| 38-209 | left lyric | 0,350,800,840 |
| 210-286 | left lyric | 180,495,780,635 |
| 287-289 | moving Chinese | 180,470,600,545 |
| 290-293 | moving Chinese | 180,205,600,340 |
| 294-322 | moving Chinese | 180,290,600,380 |
| 290-293 | source-exact bubble interior | 220,390,560,550 |
| 411-503 | bottom lyric | 700,925,1230,1060 |
| 536-665 | right lyric | 1245,495,1830,670 |

There are zero source-bright-core mismatches above 30 channel levels in these registered fields, and zero whole-region mismatches in the four registered bubble interiors.

The 20 left-field entries at f267-286 contain zero detected source-bright-core pixels. Source cels f267 and f276 were independently viewed: both have no visible lyric in that region. This is consistent with a text-free phase, not evidence of 20 readable captions. There are 488 frames with nonempty source-bright-core caption masks.

## Limitations And Potential Misses

- The other 158 frames in this interval have no registered caption diagnostics. In particular, 0-37, 323-410, and 504-535 are not covered by this field detector. Text outside the rectangles, including Japanese text outside the moving-Chinese field, is not directly covered by this caption check.
- Bright-core comparison is not OCR or a complete glyph/anti-aliasing audit. Dim, differently colored, edge pixels, or changes of 30 channel levels or less may escape it. Equal source glyph cores do not by themselves establish final contrast or readability.
- Added wrong glyphs are explicitly detected by whole-region equality only in the registered f290-293 bubble interior. The remaining source-core tests do not generally detect added text elsewhere.
- Source clock displays and their contact/occlusion geometry are not covered. Held-clock source registration remains a separate task; selected f83-156 drafts still have unresolved display issues according to the production state.
- Raw-frame checks do not inspect final encoded text contrast. The encoded technical verifier explicitly does not validate captions, drawing quality, or visual continuity; encoded full-resolution visual review remains separate.
- `registered_title_peripheral_text_exact=true` in this opening report is not evidence that the later title interval was reviewed. It only applies when a registered title asset appears.
- Equality outside declared edit masks cannot establish that the declared matte boundaries or foreground/background order are artistically correct.
- The 65 reduced contact pages are generated, not fully manually accepted. Full-speed viewing and artistic continuity/pose/occlusion checks remain pending.

## Completion Claims

No erroneous artistic-completion claim was found in the inspected raw report, encoded verifier, or lessons. The raw report correctly records `artistic_acceptance=false`, `original_speed_watch=not_performed`, and `manual_contact_review=pending`. Production still has zero artistically accepted character cels.

Permitted summary: registered opening caption-core and four bubble-interior checks passed, with focused repair tests passing and separate timing/audio verification passing.

Not supported: every subtitle is fixed, all props are correct, all consecutive frames are artistically accepted, the preview has passed a real-speed watch, or the full Klee PV is finished.
