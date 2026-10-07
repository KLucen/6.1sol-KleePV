# Raised Shot1225-1285: Corrected Draft Export and Scoped Review

Reviewed 2026-10-04. This report is local to this shot; it grants neither artistic acceptance nor whole-PV acceptance. Shared composition/caption rules and generated PNGs were not edited by this export/QA task. V1 blocked subtitle baselines remain intact.

## Outputs

Both files were directly rendered once from timeline-raised-1225-1285-fast-draft-v1.json with --draft-preview and libopenh264. The comparison was rendered with --side-by-side; the single file was not cropped from it. Both render tool sessions completed with exit0 and are closed. Both verifier commands and both evidence utilities completed with exit0; no required tool session remains running.

- output/klee-raised-1225-1285-fast-draft-v2.mp4: SHA256 c0a57ac0b6e35d368bc28cbaa6e1c6030559b76b70fd2f7159674ef2bc150e36.
- output/klee-raised-1225-1285-comparison-fast-draft-v2.mp4: SHA256 7365d89fd970b8ee290d9749c7d92e96fccfca95bce51589ee58c13f1710e04b.
- Timeline SHA256 9a080f5ecbc8ad366e3d4f788b89ab411cb62466062c4aa6f384529ceaae12d4. Scope: 60sourceframes [1225,1285),13cels/13exposures,2.5seconds.

Current frozen-rule hashes were checked after export, not captured at render start. Caption owner confirmed raised helper was frozen before render; the later compose change only gates night [902,911), outside this shot.

- compose.py SHA256 bf1dcf9492264d302954ab8192e4eaaf91cbe2258ad7ccac99eb69470ec0a353.
- raised_caption_layers.py SHA256 f097da91b65ff5b3406e9e0e5e24761fea02fb924dcb3c11a4e91bbd2d745cf9.
- verify_preview.py SHA256 b335d885fbe79c03b3f84f5cfaa376db7e1b441dc16681b9dcb5b02ea467e00f.

## Technical Timing

single-v2-technical-verification.json and comparison-v2-technical-verification.json: all17checksPASS; fatal_error absent. Both sequential full video/audio decodes yield exactly60frames; single1920x1080/comparison3840x1080. All60video PTS equal actual source PTS rebased to start; timebase1/16000;0PTS mismatch; end boundary2.5seconds exact.

AAC remains packet-copy with151expected==actual packets and unchanged payload hashes/priming data. Source video origin51.042seconds falls between1/44100 audio ticks. The unique deterministic nearest-sample origin51.041995464852604seconds is used: -0.2samples/-4.535147392290249microseconds, not an arbitrary tolerance. Every packet timestamp and duration strictly matches that shift. Whole-packet audio tail3.219954648526077milliseconds is reported. Video/source exposure timing remains exact; audio's necessary sample-grid quantization is a distinct fact.

These checks confirm correctly timed, decodable original-speed files exist. They do not mean the reviewer visually watched the complete original-speed movie.

## Actual Static Scope

1. Before repair, viewed all5 raw review_interval contact pages from qa/raised-1225-1285-fast-draft-v1:13exposurestarts and12boundarypairs. Confirmed the wide captions nearly disappeared and close-up captions fragmented. Baseline encoded60pairs were persisted in encoded-v1-evidence, but all8baseline encoded pages were not separately viewed. The old reports/baseline files were preserved.
2. After repair, independently viewed caption owner's all10 raw-caption-page-01..10.png from qa/fast-fullpv-raised-caption-2026-10-04: actual source/raw current composite for all60frames. Both lines now visibly complete; no gray old collar rectangle/button is restored through the transparent lyrics. Raw audit numbers from the caption owner are not substituted for this manual review.
3. Sequentially decoded actual source interval and final single video into encoded-v2-evidence/report.json: all60source/encoded native355x108captionpairs, no additional encoded frame. Viewed all8caption-page-01..08.png, including every frame1225..1284. Complete two lines throughout; wide strokes survive, close-up1px local edge gives contrast on cream collar. Source-like compression texture in the dense first Japanese glyph is retained; this is not re-typeset typography or a claim that every original glyph is pristine.
4. Sequentially decoded both final videos, checked dimensions/all60frames/no extras, persisted comparison-and-raw-report.json and60single/comparison-right native captionpairs. Viewed all8comparison-caption-page-01..08.png. No missing line or broken phase in either output. Different encode layouts produce lossy RGB differences: caption max49 between single/right, max65 raw->single glyphcore. These numerical diagnostics are not an artistic acceptance threshold; the actual rows were visually checked.
5. Viewed final encoded wholeframes1225,1261,1264,1270,1274,1282. Also viewed source1225 and its actual generated PNG independently. Wide arms have two spread brown gloves. At1261, the source-mandated zoom places both wrists beyond the frame; close-up drafts preserve that visible boundary without inventing cropped fingertips. No identifiable old pink character, extra arm/hand, or missing main head is confirmed in the representative wholeframe scope.

## Remaining Findings

- Minor local original-outline residue is confirmed, not a completely missed character: f1225 raw pixels(960,44),(970,44),(1324,795) equal dark source pixels while generated is purple sky; both original/new subject masks are0 there. Small black floating segments are also visible near hat/ears in representative close-up outputs. Source ownership was numerically confirmed only for the stated f1225 coordinates. No mask fix or additional render was attempted here; root owns severity/defer decision. Do not state that every original-person pixel was removed.
- Old1261/1270 assets have ornate collar/sleeve motifs; new assets have simpler two-leaf collars. Decorative boundary flicker remains.
- Existing1270 tilted-head to new1274 upright-head join,1264->1267 small mouth/pose delta, and1278->1282 eye-palette shift remain original-speed continuity questions from the earlier art review. Static evidence does not determine their perceptual severity.
- f1225 eyes retain source-like blue upper fill; root explicitly deferred this missing-first batch issue.

No reappearance of the V1 missing/fragmented lyric blocker in the complete final encoded caption scope. This is a draft candidate with separate minor/medium drawing/composition issues, not a final artistic pass.

## Playback Limit

Full uninterrupted original-speed visual playback was NOT performed. Frame/contact-sheet review, source-exact timing, and successful decode are recorded separately; none is mislabeled as watching the complete movie. No remote resource was downloaded to work around viewing limits.
