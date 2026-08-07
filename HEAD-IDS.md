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

`max_head_id` is **59**, confirmed across six characters from a live install
and independently by StarBreaker's own `chf to-json`. An earlier note here
claimed the field was a `0xFFFF` sentinel; that was read from a single sample
and is wrong. The gene pool is 60 heads (0–59) per gender, as guessed.

## Where the heads are NOT

Searched on 2026-08-06 against a live 152 GB `Data.p4k`. Recording the dead
ends so nobody repeats them:

- **Not separate mesh assets.** There is exactly one protos head mesh per
  gender, at
  `Data/Objects/Characters/Human/heads/{male,female}/pu/protos_human_*_face_t1_pu/`.
  Exported to GLB it is **1 mesh, 5584 verts, 0 morph targets**.
- **Not the `.RigLogic` file.** `protos_human_male_face_t1_pu.RigLogic` is
  CIG's own `RIG V1.9` format (not Epic's DNA). Its `0x38` field is
  `0xdd6c67f6`, exactly the `gender_hash` in the `.chf`, so it is the right
  asset — but its string table is entirely `CTL_*` *expression* controls
  (`CTL_R_brow_raiseIn`, `CTL_expressions blinkR`). That is the facial
  animation solver, not identity. No count of 59/60 appears anywhere in it.
- **Not `PROTOSINFO`.** The name is a red herring given the `protos_` prefix.
  The chunk is 76 bytes of metadata: `count=1`, name `head`, pointing back at
  `protos_human_male_face_t1_pu` / `0xdd6c67f6`.
- **Not the RigLogic archetypes.** `Data/Objects/Characters/RigLogic/` holds 77
  files, but only 15 male and 14 female `*_archetype_*`. Nowhere near 60, and
  head IDs are not an index into them.
- **Not found in DataCore** under any head/customizer record-type name tried.

The head mesh is driven by a **198-bone facial rig** (`FACIAL_LOD0_C_Skull`,
`FACIAL_LOD1_L_EyelidUpper`, …). Head identity is therefore almost certainly
bone-pose data inside the `RIG V1.9` container, which nothing public parses —
StarBreaker only *names* the chunk type.

## Two ways to close it

1. **Reverse-engineer `RIG V1.9`** far enough to pull per-head joint deltas.
   Real work, no prior art, unknown payoff.
2. **Build the catalog empirically.** Emit 60 `.chf` files that put a single
   head at 100% for one face part, import each, screenshot the creator. That
   produces exactly the visual reference this document asks for, using only
   tooling that already works. Far less effort, and it sidesteps the format
   entirely.

Option 2 is the recommended path, and as of 2026-08-06 it is known to be
viable: a `.chf` written by our own encoder was imported and rendered
correctly, which is the single capability the whole approach rests on.

## Hard limit to expect

The creator is a DNA blend of a fixed gene pool, not a sculpt tool. A face
far outside that pool is not reachable at any weight. Bone structure and
ethnicity are usually the wall, not the tooling.

## Status

Investigated 2026-08-06 on Windows against a live install. The asset hunt is
done and the answer is negative: the 60 heads are not extractable as meshes.
See "Two ways to close it" above. See `project.md`.
