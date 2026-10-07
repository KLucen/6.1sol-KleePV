# Klee PV replacement workspace

The source is a 1920x1080 H.264 video with a nominal 24 fps video stream and a 44.1 kHz stereo AAC track. The video contains burned-in Chinese and Japanese subtitles, title text, credits, props, and effects; there is no separate subtitle stream.

Prepared analysis artifacts:

- `scene_candidates.json`: 115 conservative scene or drawing-change candidates from the source.
- `scene_candidates_contact.jpg`: candidate frames with timestamps and scene scores.
- `contacts/one-sec-contact.jpg`: one-second overview contact sheet.
- `source_cels/source-cel-*.jpg`: 115 full-resolution candidate source frames for image-edit references.
- `_inspect/pv_inspection_report.txt`: manual shot-group and occlusion review.

The replacement plan uses strict source exposure boundaries as the baseline: preserve the original 24 fps timing and redraw each meaningful source cel or key pose as Klee. Burned-in captions and credits remain the top layer. Pillow/blanket, sack, scroll, and star effects require explicit foreground masks. The blue-lit secondary character inserts are also character replacement targets.

The current environment has no built-in image generation tool and no `OPENAI_API_KEY`, so generated Klee cels have not been created yet. Once an image-generation path is available, run the tasks from `shot_plan.json`, then review every hard cut and key-pose boundary at full resolution before compositing.
