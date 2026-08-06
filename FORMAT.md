# Star Citizen `.chf` Format

Custom Head File. Stores one character's face, colors, materials, and equipped
cosmetic items. Written by the in-game character creator.

Game path: `StarCitizen\LIVE\user\client\0\CustomCharacters\`

Everything below was verified against `combat_veteran.chf` and cross-checked
with the [StarBreaker](https://github.com/diogotr7/StarBreaker) `starbreaker-chf`
crate (Rust, active). Our independent parse and theirs agree.

---

## 1. Container

Every `.chf` is **exactly 4096 bytes**, zero-padded.

```
offset  size  field
0x00    2     magic            = 0x4242 ("BB", little-endian u16)
0x02    2     flags/version    (purpose unknown; preserve for round-trip)
0x04    4     crc32c           checksum of bytes[0x10..0x1000]
0x08    4     compressed_size
0x0C    4     decompressed_size
0x10    N     zstd frame (level 1), N = compressed_size
0x10+N  ...   zero padding to 4096
```

### CRC

CRC32C (Castagnoli, poly `0x82F63B78`), computed over `bytes[16..4096]` —
**including the zero padding**, not just the zstd frame. Verified:

```
combat_veteran.chf: header 0x8b316b5c == computed 0x8b316b5c
```

The client validates this. Any edit requires recomputing it.

### Gotcha: zstd CLI fails on the raw tail

`zstd -d` on `bytes[16:]` errors with `unsupported format` because of the
trailing zero padding. Slice to exactly `compressed_size` first:

```python
frame = data[16:16 + compressed_size]
```

### Modded marker

StarBreaker writes the ASCII bytes `diogotr7` into the final 8 bytes of the
container as a "this file was tool-generated" marker. All-zero tail is the
vanilla case. Both are accepted by the game.

---

## 2. Payload layout

Decompressed size for `combat_veteran.chf` is 2246 bytes.

| Offset  | Block                     | Notes                                    |
|---------|---------------------------|------------------------------------------|
| 0x0000  | version / header words    | `02 00 00 00`, `08 00 00 00`             |
| 0x0008  | 16-byte GUID              | preset/head asset reference              |
| 0x0028  | `u64` DNA size            | `232` in the sample                      |
| 0x0030  | **DNA blend matrix**      | see §3                                   |
| 0x0118  | itemport GUID table       | hair / beard / brow / eye asset refs     |
| 0x0266  | `u64` float count         | `33`                                     |
| 0x026E  | **float parameter list**  | 33 records, stride 12, see §4            |
| 0x03FA  | `u64` color count         | `26`                                     |
| 0x0402  | **color list**            | 26 records, stride 12, see §5            |
| 0x053A  | trailing GUID tables      | material variants, loadout               |

Offsets shift per file. Parse sequentially rather than hardcoding them.

---

## 3. DNA blend matrix — the face shape

This is the part that actually determines what the character looks like.
It is **not** a set of free sculpt sliders. Each face part is a weighted
blend of preset head meshes.

```
u32   name hash of "dna matrix 1.0"   (validation magic)
u32   gender hash
u32   variant hash
u32   0
u16   part_count      = 13 (12 pre-v8, Neck added in v8)
u16   blends_per_part = 4  (always)
u16   unknown
u16   max_head_id     = 0xFFFF
      part_count * 4 records of:
        u16 value     scaled 0..65535 -> 0..100%
        u16 head_id   which preset head mesh
```

### Record order is interleaved

Not part-major. Blend index is the outer loop:

```
index i  ->  part = i % part_count,  blend = i / part_count
```

### Face parts (index order)

```
0  EyebrowLeft    7  CheekLeft
1  EyebrowRight   8  CheekRight
2  EyeLeft        9  Mouth
3  EyeRight      10  Jaw
4  Nose          11  Crown
5  EarLeft       12  Neck      (v8 only)
6  EarRight
```

### Decoded sample

```
part        blend0            blend1            blend2   blend3
EyebrowL    head 15 @ 63.8%   head 53 @ 36.2%   --       --
EyebrowR    head 15 @ 63.8%   head 53 @ 36.2%   --       --
EyeL        head  5 @ 67.2%   head 46 @ 32.8%   --       --
EyeR        head  5 @ 67.2%   head 46 @ 32.8%   --       --
Nose        head 16 @ 65.7%   head 32 @ 34.3%   --       --
EarL        head  7 @ 70.3%   head 14 @ 29.7%   --       --
EarR        head  7 @ 70.3%   head 14 @ 29.7%   --       --
CheekL      head 11 @ 61.7%   head 47 @ 38.3%   --       --
CheekR      head 11 @ 61.7%   head 47 @ 38.3%   --       --
Mouth       head 44 @ 64.2%   head  7 @ 35.8%   --       --
Jaw         head 14 @ 62.6%   head 32 @ 37.4%   --       --
Crown       head 47 @ 69.8%   head  8 @ 30.2%   --       --
Neck        head 47 @ 62.7%   head  1 @ 37.3%   --       --
```

Slots 2 and 3 are unused in practice — the in-game creator only exposes a
2-way blend, though the format allows 4.

Left/right pairs are identical here because the creator ships symmetric.
The format does not require symmetry.

---

## 4. Float parameter records

Skin, makeup, freckle, and tattoo parameters. A `u64` count sits 8 bytes
before the first record. Stride 12 bytes:

```
u64   record count
u32   name hash (CRC32C of the parameter name)
f32   value
u32   0 (padding)
```

Records are **sorted ascending by hash** — which makes this block the reliable
anchor for locating everything after it. Decoded sample (33 records):

```
Makeup1MetalnessR    0.70   Makeup2MetalnessR   0.00   Makeup3MetalnessR   1.00
Makeup1MetalnessG    0.70   Makeup2MetalnessG   0.00   Makeup3MetalnessG   0.20
Makeup1MetalnessB    0.70   Makeup2MetalnessB   0.70   Makeup3MetalnessB   0.20
Makeup1SmoothnessR   0.30   Makeup2SmoothnessR  1.00   Makeup3SmoothnessR  1.00
Makeup1SmoothnessG   0.30   Makeup2SmoothnessG  1.00   Makeup3SmoothnessG  0.50
Makeup1SmoothnessB   0.30   Makeup2SmoothnessB  0.30   Makeup3SmoothnessB  0.50
Makeup1OpacityR      1.00   Makeup2OpacityR     1.00   Makeup3OpacityR     1.00
Makeup1OpacityG      1.00   Makeup2OpacityG     1.00   Makeup3OpacityG     1.00
Makeup1OpacityB      1.00   Makeup2OpacityB     0.25   Makeup3OpacityB     1.00

FrecklesAmount       0.00   SunSpotsAmount      0.00   TattooAge           0.00
FrecklesOpacity      0.00   SunSpotsOpacity     0.00   TattooHueRotation   0.5656
```

Other known names not present in this file: `BaseMelanin`,
`BaseMelaninRedness`, `BaseMelaninVariation`, `DyeAmount`, `DyeFadeout`,
`DyePigmentVariation`, `DyeShift`.

---

## 5. Color records

Same `u64` count prefix and 12-byte stride, RGBA8 instead of a float:

```
u64   record count
u32   name hash
u8    R, G, B, A
u32   0 (padding)
```

Unlike the float block, colors are **not** sorted by hash. Do not try to find
this block by looking for an ascending run — anchor off the float block's end
instead.

Decoded sample:

```
BodyColor          #ae7d66  a=255
LipMakeupColor1    #c5bc6e  a=255
LipMakeupColor2    #170e49  a=255
LipMakeupColor3    #734145  a=255
CheekMakeupColor1  #b8b8b8  a=255
CheekMakeupColor2  #b8b8b8  a=255
CheekMakeupColor3  #8c0a45  a=255
EyeMakeupColor1    #000000  a=255
EyeMakeupColor2    #fe6d42  a=255
EyeMakeupColor3    #4d261a  a=255
```

The remaining 16 entries in this block are UV transform values
(`Makeup1/2/3 NumTilesU/V`, `OffsetU/V`, `TattooNumTilesU/V`, `TattooOffsetU/V`)
packed into the same 4-byte field with `a=0`. Treat `a=0` as "not a color".

Other known color names: `EyeColor`, `HairDye`, `HairDye2`, `HairDye3`,
`HairDyeColor1`, `HairDyeColor2`, `BeardDye`, `StubbleDye`, `EyebrowDye`,
`EyebrowDye2`, `EyebrowDye3`.

---

## 6. Name hashing

All identifiers are **CRC32C of the ASCII name string**. No name strings appear
anywhere in the file.

```python
NameHash("BodyColor") == 0xbd530797
```

Some hashes do not match the CRC32C of their display name and are known only
from manual reverse-engineering. StarBreaker keeps these in a
`MANUAL_MAPPINGS` table — including every color name in §5, plus material
handles: `Head Material 0xa98beb34`, `HairDyeMaterial 0x6c836947`,
`EyebrowDyeMaterial 0x078ac8bd`, `EyeMaterial 0xa047885e`,
`BeardDyeMaterial 0x9b274d93`, `BodyMaterial 0x27424d58`,
`DyeMaterial 0xa8770416`.

The combined table (`KNOWN_NAMES` CRC'd + `MANUAL_MAPPINGS`) is 210 entries and
resolves **100% of the hashes** in `combat_veteran.chf`.

Source: `crates/starbreaker-common/src/name_hash.rs` in StarBreaker.

---

## 7. What is still unknown

- **Head ID → appearance.** Nothing published maps `head 15` to what that nose
  actually looks like. This is the blocker for reference-image matching.
  See `HEAD-IDS.md`.
- Bytes `0x02..0x04` of the container header (flags/version).
- `header_unknown` u16 in the DNA block.
- The trailing GUID tables past `0x053A` (material variants / loadout).

---

## 8. Prior art

| Project | Language | What |
|---|---|---|
| [diogotr7/StarBreaker](https://github.com/diogotr7/StarBreaker) | Rust | Full toolkit: P4k, DataCore, CryEngine assets, Wwise, `.chf`. Includes a Blender addon and MCP server. The authoritative source. |
| [diogotr7/starchar](https://github.com/diogotr7/starchar) | TS/React | Web editor at [starchar.app](https://starchar.app). DNA import/export, out-of-range colors. |
| [diogotr7/StarCitizenChf](https://github.com/diogotr7/StarCitizenChf) | C# | Predecessor. **Archived Oct 2024.** |
| [Spieler1ONE1/SCCharacters](https://github.com/Spieler1ONE1/SCCharacters) | Python | Preset manager / library browser, Windows. |
| [star-citizen-characters.com](https://www.star-citizen-characters.com/) | — | Community `.chf` sharing site. |
