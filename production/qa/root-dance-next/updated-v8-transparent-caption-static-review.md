# Updated V8 Transparent Caption Static Review

Scope: all 14 updated overlap pages, covering every frame f831..886 (56 frames), and the four actual native full composites f863/f868/f873/f880. All were visually viewed. No core/selection changes.

Exporter evidence SHA256: `c80fc83dfeb154ecebe9802478626dc91a623fadf35947083aa41834d9458b64`.
All 56 native-pair file hashes match exporter records. Each viewed page is pixel-equal to a reconstructed page from its four specific native pairs. All four full-composite caption crops match their native pair target halves. Exact page/frame/file hashes and dimensions are in the JSON.
The previous independent f863..886 source audit's 24 native BGR hashes all match the exporter source hashes. This private static review did not re-decode 56 source-video frames and does not convert old 32-frame labels into a new 56-frame proof.

## Static Findings

- f831..838: Chinese bottom line remains readable and no new missing/fractured stroke was obvious at viewed 2x scale; Japanese center remains crowded by pale star lines.
- f839..847: Descending/front boot crosses the left lyric area. Chinese first characters remain in front of the brown boot/sole rather than erased; not all AA is source-exact.
- f848..867: Left front boot sits behind the first Chinese glyphs. Registered cream strokes remain visible over brown. Japanese left/top boot-cuff contact can be pale-on-pale.
- f868..872: New f868 shoe/pose underlay is present; Chinese first glyphs remain foreground with no obvious new break. Long rear hair remains an independent raw-art continuity issue.
- f873..879: Foot/cuff shape changes with the unfolded kick. Chinese left two characters remain present over the left boot, and the rest of the line remains legible; Japanese starts cross pale cuff with weak contrast.
- f880..886: Both boots enter opposite ends. Chinese left two characters lie over the left brown boot; the final two Chinese characters lie over the right brown boot. The visible strokes remain foreground without obvious new fragmentation. Japanese end glyphs cross cream cuffs and lose contrast; center star crossings remain reconstruction/contrast limits.

No obvious new fragmented Chinese glyph was found at the viewed 2x static scale. At f880..886, the first Chinese characters remain over the left brown boot and the final characters remain over the right brown boot; no broad source-shoe rectangle was visibly reintroduced. Japanese on pale cuffs and star crossings remain contrast/reconstruction limitations.

Exporter stable registered-subset mismatch >30 range: `[0, 0]`; warm candidates outside alpha range: `[198, 4425]`. These diagnostics have their stated subset-only scope and are not full-glyph acceptance.

## Reviewed Artifacts

| Page | Frames Inclusive | SHA256 |
|---|---|---|
| 1 | [831, 834] | `8b10a20cfd182b3fc52d3fe458eba44d1053c96a2d597bd732c5a3c5217d3bdc` |
| 2 | [835, 838] | `76621190dc79c4677d55ee33d36ad345abe9ea0e3454e7abba2d2243e2777615` |
| 3 | [839, 842] | `53db5cb533f4a188db7f7ba3e879a5328d6756aafe4c062e7dc0e6388113db4a` |
| 4 | [843, 846] | `9eaef903a8f7f12f6dc66e8cc55fe584be65a893012b2e3f4d5bb60f8da9e07f` |
| 5 | [847, 850] | `a7a50e4272ec714c53fdc0d1f7c440d826f87e8c7f894d0d27daf9c468dd5c53` |
| 6 | [851, 854] | `3c0f54520377c2d533b745e080fd304fdf2e1ecbd511441ce31b90827caefd65` |
| 7 | [855, 858] | `bbf82cb90c23cc9c3798f99ec8b569290154ff520f68c53a9ff5bc12b4089872` |
| 8 | [859, 862] | `6c610ecf89f6d9a536b8cf802369c80a52fe009104932e8c02cc9682d746007b` |
| 9 | [863, 866] | `b72e96926017b65333e1837b9f4b0cfe1561e03b627fefc76a9c47978f0dcaf4` |
| 10 | [867, 870] | `45e7698f9bc1d01261cea1087adaf54c6f365e5e390ced89f81ab50ef1d2dd56` |
| 11 | [871, 874] | `734170a00365a9c83aca02a86e110aa0563e079e3120d85ed1fe0b433eea5c74` |
| 12 | [875, 878] | `1d73b2a278d95b563dd5878fa4e7c27cc527d3520237a1fe46b8d301597bbcde` |
| 13 | [879, 882] | `c94dc86656d8499edb5afd5aedf9cdf1961f6a1a58a345e445e8c394a4b3c954` |
| 14 | [883, 886] | `b835df16c427205215a87f26d1c6226dbb9cdbcb7ba329a789ac729c8d044bba` |

| Full Composite Frame | SHA256 |
|---|---|
| 863 | `5c884f227410d97c553a448f2b732b9fabdccab6653e146a4caf7188422d0476` |
| 868 | `9580b873d38883a5d82ca2e02e91fd713a32ab39fec94192b8a4fec3ce1e6fb2` |
| 873 | `34783168c4ed5112fbc3712a0afae3226e6a5a91c3ee5bba6661e28ccb5f7c5d` |
| 880 | `897018867a22de45c0340f5e34e76e76b7a0704b16e7d89b0038fe27ccf8b651` |

## Limits

- This review reads exporter-produced actual composites and pairs. It does not independently decode 56 original-video frames; only the earlier separate 24-frame actual source audit is cross-hash-checked.
- All Chinese observations are static 2x nearest-neighbor page inspection, not OCR certification or inspection of every AA pixel.
- The stable registered donor subset is narrower than full glyph geometry. Zero subset mismatches do not certify glyph counters, AA, contrast or exact original alpha.
- Japanese glyphs over cream cuffs and moving pale star crossings remain hard to read; no complete Japanese glyph acceptance is claimed.
- Four updated full images showed no obvious orphan cream waist dots, but existing pale hair wedges at f880 remain raw-art occlusion questions, not yellow-effect or caption-layer approval.
- All underlying Klee drafts remain unaccepted for hair/costume/contour continuity. No full-speed watch or whole-PV completion is claimed.

Complete glyph acceptance: false. Artistic acceptance: false. Actual-speed watch: not performed.
