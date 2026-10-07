# Source-Only Caption Extension Audit

Scope: f863..886 inclusive, 24 actual sequential video decodes at native 1920x1080. No core, selection or source-alias changes.

- Source SHA256: `27b5b242fe6ea8f93ae3ce4d794451aa78a25d1796c45f3bbc3b46b17ed880b7`
- Donor: f831; current production interval: `(831, 863)` (half-open).
- All 24 decoded: `True`.
- All 24 local best offsets [0, 0]: `True`.
- Warm candidates outside registered alpha range: `[702, 2775]`.
- Stable-interior mean max-channel delta range: `[8.34015032337004, 10.242265338227583]`.
- All 24 currently NOOP in production: `True`.
- Old 32-frame audit is independent provenance, not reused as a 56-frame proof.

## Per-Frame Actual Decode Evidence

| Frame | PTS | Cel | Best dx,dy | Stable mean delta | Warm candidates | Outside alpha | Native BGR SHA256 |
|---|---:|---|---|---:|---:|---:|---|
| 863 | 35.958 | cel-0153 | [0, 0] | 8.378 | 8948 | 1073 | `01ec4b346f308727a49d5b61fdcd0b75e6dba143ce3b8d025b2b0d24e764cef8` |
| 864 | 36.0 | cel-0153 | [0, 0] | 8.520 | 9055 | 1098 | `567cdfaa0e09c4a37bddfba020add5111eba1f9c5b271a138e778932a80d16b1` |
| 865 | 36.042 | cel-0153 | [0, 0] | 8.373 | 8927 | 1051 | `62a22f3c8411b6e9a24e1631769efb6843c6abe01cf8275c0a4939c1afbb304b` |
| 866 | 36.083 | cel-0153 | [0, 0] | 8.340 | 8945 | 1090 | `09a211de3d5962042e8ab8fabcc96a6d17804dcf7c410fbff9d7701623d8436f` |
| 867 | 36.125 | cel-0153 | [0, 0] | 8.360 | 8852 | 1056 | `4a51ea8feedfed64b176ef2079b98db5b0d917563b0190f198363016cdd469e6` |
| 868 | 36.167 | cel-0154 | [0, 0] | 8.708 | 8724 | 922 | `01e9cd9f9f73fbe976a6a2c2100225ee78b13928480d286313d22fc652770455` |
| 869 | 36.208 | cel-0154 | [0, 0] | 8.604 | 8460 | 719 | `4c18ab6719d284345944a35c54c2236bffd5a9c6a5055a8ffd45ab593f5a74c4` |
| 870 | 36.25 | cel-0154 | [0, 0] | 8.656 | 8565 | 733 | `d59c3da5469eee491cefacd34f6ad90d635ddc6012ce84d6addad45f4b823f71` |
| 871 | 36.292 | cel-0154 | [0, 0] | 8.589 | 8537 | 702 | `bff33ca002d268096cf39978a2ba0625beb3c8ea5fbbd268bc53d8380d2e0dc0` |
| 872 | 36.333 | cel-0154 | [0, 0] | 8.802 | 8862 | 867 | `9288208924dfb7fef79e6a403398fdbb49fe687af8ffaf3e7c6fc39b1a0d6a37` |
| 873 | 36.375 | cel-0155 | [0, 0] | 8.824 | 9904 | 1743 | `9748c94b3d33fa2b0b8965dbdb9cfa4ea52876907a90ef717dfc5bf470e285dd` |
| 874 | 36.417 | cel-0155 | [0, 0] | 8.953 | 9961 | 1795 | `bde80bce96fad160729c7083e27903330479bbc6afc2e8f711b128d1437cfc4e` |
| 875 | 36.458 | cel-0155 | [0, 0] | 8.840 | 9850 | 1747 | `7f3d8c8b7865c3977772c8f16ca8a16423e25f5a18e44ca14cc84caab10c94f3` |
| 876 | 36.5 | cel-0155 | [0, 0] | 8.965 | 10039 | 1864 | `89fa43d82e38617a3d82beedc367398b1b0d9a98ff3a751c979542647a5e7e2a` |
| 877 | 36.542 | cel-0155 | [0, 0] | 8.897 | 9815 | 1804 | `646ee8eb9c8cb35e239221a61cdd0f6488439191889fa19bccf29ba1ea345044` |
| 878 | 36.583 | cel-0155 | [0, 0] | 8.970 | 9808 | 1856 | `f80c2724d2e16602a81bcbd6bd3af3f8824eddbbee4ee3afd4aae1aa046fa2e2` |
| 879 | 36.625 | cel-0155 | [0, 0] | 9.010 | 9690 | 1790 | `daae6b24fe388b21b256b2a1e5c84ba4f2a5b524789c8193d62efeae6b32c333` |
| 880 | 36.667 | cel-0156 | [0, 0] | 10.024 | 11426 | 2713 | `9104aafae9c3d048ba10b75bc9038d9b422d5a762eaa3e4bedc1897aac510b0e` |
| 881 | 36.708 | cel-0156 | [0, 0] | 9.958 | 11132 | 2579 | `505c548b4d02b61f9917a8e64370f2a55904489ef7eeb349d307cce513b14339` |
| 882 | 36.75 | cel-0156 | [0, 0] | 10.078 | 11120 | 2615 | `bfa012a0fc1af2772b9969b25c0beeb6b24107924def10769171d2e176c523dd` |
| 883 | 36.792 | cel-0156 | [0, 0] | 10.107 | 11060 | 2597 | `6e2d9dff907d9b62818808f8009243af3344e649795aee18089864961927edef` |
| 884 | 36.833 | cel-0156 | [0, 0] | 10.236 | 11240 | 2691 | `9d4c93f6569a808c068828f6c3c388d518770388d4a1da52475b89f076e03744` |
| 885 | 36.875 | cel-0156 | [0, 0] | 10.036 | 11278 | 2658 | `2af2c04b4c236ec1fdff97d2d55d30cee499ad49ffdddf040760fdb2192c2ab6` |
| 886 | 36.917 | cel-0156 | [0, 0] | 10.242 | 11329 | 2775 | `fc5ad373fdee5ae2c3f40de29275f2df9692dd899694bd4a919815f2f693b00e` |

## Limits And Next Checks

- Warm-color candidates are not an OCR segmentation: pale source shoe/cuff pixels can be candidates and must not be promoted to glyph support.
- Zero best offsets within the local search support a fixed caption phase, not exact original alpha or perfect source text recovery.
- The hidden plate and AA are reconstructed by inpaint and projection; pink star crossings inside Japanese glyph counters remain uncertain.
- Private dark-underlay simulations exercise the same registered layer formula without extending the production interval; they are not actual new-Klee composites.
- The registered matte must remain separate from character coverage; a broad source-caption rectangle would reintroduce the source boot at crossing frames.
- The second shoe unfolds at f873 and lowers into the caption band at f880; final Klee boots, glyph contrast, masking and frame transitions require new-art composite checks.
- No full-speed watch, OCR certification, 56-frame combined proof or artistic acceptance is claimed.

## Diagnostic Pages

- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-unsupported-warm-core-page-01.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-unsupported-warm-core-page-02.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-unsupported-warm-core-page-03.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-unsupported-warm-core-page-04.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-unsupported-warm-core-page-05.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-unsupported-warm-core-page-06.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-private-transparent-simulation-page-01.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-private-transparent-simulation-page-02.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-private-transparent-simulation-page-03.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-private-transparent-simulation-page-04.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-private-transparent-simulation-page-05.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-private-transparent-simulation-page-06.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-source-rgb-difference-page-01.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-source-rgb-difference-page-02.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-source-rgb-difference-page-03.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-source-rgb-difference-page-04.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-source-rgb-difference-page-05.png
- C:\Users\KLucen\Desktop\kl\production\qa\root-dance-next\extension-source-rgb-difference-page-06.png

## Static Diagnostic Review

All 18 pages were viewed: 6 unsupported-candidate pages, 6 private transparent-simulation pages, and 6 actual RGB-difference pages. All 24 native video decodes are pixel-equal to their separate per-frame source-reference PNG decodes. These are separate actual decodes, not copied 32-frame labels.

The same two-line caption phase remains through f886, and f863 is not a text-phase change. The local search returns [0, 0] for all 24 frames. This supports reusing the fixed geometry and registered donor matte for a scoped extension, conditional on tests and actual new-Klee composite inspection. At this audit's recorded implementation hash, the interval ended at f863 exclusive and all 24 calls were NOOP. The parent subsequently reported extending the production interval to f887 exclusive and running a separate 56-frame audit; those later changes are not evidence produced by this private 24-frame report.

The warm-color mask is not a glyph mask. Unsupported patches include source shoe/cuff areas, moving pale star crossings and compressed edge pixels. The count jumps from 702..1098 for f863..872, to 1743..1864 at f873..879, then 2579..2775 at f880..886, corresponding to boot contacts and stars, not a new subtitle phase. Do not add those candidates to registered glyph support.

The private constant-dark-underlay pages show the two lines without the source boot patches. The Chinese line is stable and clearly separated in this diagnostic; Japanese star-crossing counters and anti-aliased edges remain reconstruction limits. These simulated underlays are not actual Klee composites and cannot establish final contrast over pale cuffs or boots.

Source pose risks remain independent: f863 rotates both wrists to edge-on outward fingers; f868 reopens both palms and tucks the rear leg; f873 unfolds that leg into a long down-right kick; f880 lowers that second shoe into the caption band. At f880..886 the two shoes contact opposite ends of both lines, making broad source-rectangle restoration unsafe. Keep the registered transparent glyph layer separate from character coverage, then inspect actual composite crossings and transitions.

No new source aliases, production-core changes, selection changes, 56-frame combined verification, original-speed watch or artistic acceptance are claimed.
