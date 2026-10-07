# Klee PV Production Archive

Engineering snapshot of the character-replacement PV project, 2026-10-07.
The full-length video is a first draft, not an artistically accepted final.

## Complete Files

Scripts, JSON timelines, generation jobs, production notes, test sources and
textual QA evidence are tracked directly in this repository. Their original
bytes are preserved, without Git line-ending conversion.

**All workspace files**, including generated images and rejected versions,
source references, difference images, masks, QA screenshots, every historical
video, the source video, bundled Python dependencies and caches, are preserved
in the [engineering snapshot Release](https://github.com/KLucen/6.1sol-KleePV/releases/tag/engineering-snapshot-2026-10-07).
The Release volumes store identical byte sequences only once; no file path or
version is discarded. `archive/project-files.json` maps every original path to
its size and SHA-256. `archive/volumes.json` records the volume hashes.

Download every `engineering-objects-*.zip` asset into one directory, then:

```powershell
python tools/engineering_archive.py restore --volumes C:/Downloads/klee-volumes --destination C:/Projects/klee-restored
```

The restorer checks all archive and file hashes, restores original paths, and
refuses to overwrite a different existing file. It does not use Git LFS.
GitHub's automatic source ZIP alone does **not** contain the large assets.

## Full Videos

- [Complete first draft, 1920x1080](https://github.com/KLucen/6.1sol-KleePV/releases/download/engineering-snapshot-2026-10-07/klee-full-oct7-draft-v1.mp4)
- [Source-left/draft-right comparison](https://github.com/KLucen/6.1sol-KleePV/releases/download/engineering-snapshot-2026-10-07/klee-full-oct7-comparison-draft-v1.mp4)
- [Actual encoded-sample observations](production/qa/full-draft-one-pass-2026-10-07/encoded-static-visual-review.md)
- [Technical delivery record](production/qa/full-draft-one-pass-2026-10-07/delivery.json)

Both videos contain all 3658 source frames and copied original AAC packets;
each passed 17 technical checks. 81 regression tests passed. Known subtitle,
matte, anatomy, occlusion and continuity defects remain pending feedback.
These technical results do not constitute artistic acceptance.

## Production Records

Start with `production/PRODUCTION_WORKFLOW.md`, `production/PRODUCTION_LESSONS.md`
and `production/CONTINUATION_STATE_2026-10-03.md`. The selected full timeline is
`production/timeline-full-oct7-draft-v1.json`.

Historical records intentionally retain original Windows absolute paths.
Restoration preserves them verbatim; it does not automatically make every
historical script portable. The original root was `C:/Users/KLucen/Desktop/kl`.
Rendering uses Python, OpenCV, NumPy, Pillow, FFmpeg and FFprobe.

The song, original PV, character and third-party dependencies belong to their
respective rightsholders. This archive does not grant a new license to them;
existing credits, dependency licenses and provenance records are retained.
