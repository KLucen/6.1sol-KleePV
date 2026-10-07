# Standing Private Proposal

This is an unaccepted composition proposal for source frames `[1043,1162)`.
It does not modify production hooks, selections, source maps, or old exports.

## Entry Point

`standing_layers_private.compose_private(source, generated, frame, asset_name)`
requires native 1920x1080 BGR inputs and exact interval/filename registration
from `timeline-private-1043-1162.json`. It returns the output and ownership,
original-subject, new-subject, caption, effects, and vacated-region masks.
The helper reads its own timeline and `short-caption-f1161-real.npz` from this
directory, plus the unchanged shared authorized long-caption builder.

## Sources And Captions

- All 119 current source frames were sequentially decoded from the same source
  through frame 3504; canonical references were compared in native BGR.
- The original exposure intervals, source PTS, aliases, and identity transforms
  are retained; repeating a character asset does not repeat the background.
- `[1043,1144)` uses the existing authorized f3402 real Japanese donor, integer
  translation `(-12,0)`, with its measured palette/AA reconstruction.
- `[1144,1162)` uses the real f3504 `分け合う` prefix, integer translation
  `(214,0)`, and real f1161 `彼此分担` Chinese. The f1161 Japanese `分` overlaps
  an original button and is not a complete glyph donor.
- Short glyphs receive a complete one-pixel contrast ring only where edited
  new-character pixels lie beneath them. The text, size, position, and timing
  remain unchanged. No AI text or guessed glyph stroke is used.

## Observed Matte Failures And Fixes

The original dark-contour flood alone leaked pale hair, sleeves, and trousers
through decoded gaps. Actual source pink fill has `R >= G + 24` and
`R >= B + 12`, unlike blue sky and cream stars. This observed color support is
retained within the original-character standing or closeup crop. No new
character geometry is programmatically drawn.

Warm effect support is taken outside the expanded original-character mask.
Using the unexpanded mask had preserved warm antialiased character edges as
if they were stars. Original visible stars outside expanded original ownership
and new-character coverage are preserved; inseparable contact AA is not claimed
recovered, and unseen portions are not invented.

## Limits

The vacated source character receives a fitted current-source gradient, not
an unavailable clean original plate. Slight local plate differences remain
possible. The selected character drawings retain known coat/boot decoration
switches, pose-amplitude approximations, and pupil simplification. Cream boot
badges still visually interfere with some Japanese glyphs from f1129 onward.
The short real `う` donor is weaker than the other glyphs. Native/static checks and raw
pixel tests do not constitute encoded, original-speed, or final art acceptance.

`private-119frame-report.json` is the technical report. A separate static-review
record will list actually viewed evidence, remaining differences, and hashes.
