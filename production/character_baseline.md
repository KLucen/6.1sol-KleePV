# Klee replacement baseline

Source: local 3658-frame MIMI PV. Preserve original scenes, source drawing exposures, audio, burned-in subtitles, independent effects, props and camera cuts.

Character: Genshin Impact Klee, default Shooting Spark outfit. Pale blonde short side ponytails, pointed ears, red beret with cream clover and white feather, red coat with cream trim, brown gloves and boots, small backpack where visible. Preserve each source cel's eye state, expression, visible hands, body pose and cropping.

Style: loose dark source-like outlines, large flat patches, orange blush ovals and restrained source-like shading. Keep a stable hat, ponytail topology, clothing cut and color palette across cels. Do not increase the rendering complexity to a game splash illustration.

Anchor: generated/anchor-gesture.png, edited from analysis/source_cels/source-cel-040.jpg with the built-in imagegen tool. This is a candidate style/identity anchor, not a substitute for the other poses.

Reference provenance: character identity checked against https://genshin.hoyoverse.com/en/character/mondstadt?char=4 and the official Klee character entry at https://wiki.hoyolab.com/pc/genshin/entry/3457. No remote character image has been used as an edit target.

Exposure strategy: strict_source. Do not add optical flow, morphing, mirrored drawings, arbitrary uniform A/B alternation or nearest-keyframe matching.
