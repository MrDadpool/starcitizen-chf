# Head IDs — the open problem

## Why this matters

`.chf` is a solved format. Reading and writing one is done (`tools/chf.py`).
What is **not** solved is turning a reference photo into a character.

The face is not free-form sculpt. Each of the 13 face parts is a weighted
blend of preset head meshes:

```
Nose = head16 @ 65.7% + head32 @ 34.3%
```

To match a photo you must answer: *which head has the nose closest to this
one?* Nothing public maps a head ID to what it looks like. StarBreaker's
name table covers parameter names, not head appearance.

## Observed ID range

From one sample file, IDs seen: 1, 5, 7, 8, 11, 14, 15, 16, 32, 44, 46, 47, 53.
`max_head_id` is `0xFFFF`, which is a sentinel, not a real bound. Actual
count is likely ~60 per gender, matching the creator's preset grid.

## Plan to close it

StarBreaker ships a P4k extractor and a Blender addon. That is the whole
pipeline:

1. **Extract** head meshes from the local game install's `.p4k`.
   `protos_human_male_face_t1_pu` / `protos_human_female_face_t1_pu` are the
   known asset name hashes to start from.
2. **Render** a contact sheet per face part — 60 noses, 60 jaws, 60 mouths,
   front and 3/4 view, neutral lighting.
3. **Match** a reference image against the sheets, part by part. Pick the two
   nearest heads and a weight.
4. **Emit** a `.chf`, drop it in `CustomCharacters`, import in-game, screenshot,
   refine.

Step 1–2 is the only real build. One-time cost, reusable for every character
after.

## Hard limit to expect

The creator is a DNA blend of a fixed gene pool, not a sculpt tool. A face
far outside that pool is not reachable at any weight. Bone structure and
ethnicity are usually the wall, not the tooling.

## Status

Not started. See `project.md`.
