# Star Citizen character tooling

Reverse-engineering notes and tools for Star Citizen `.chf` character files,
aimed at building a character from a reference image.

**Start at [RESUME.md](RESUME.md)** if you are picking this up on the Windows box.

## Docs

| File | What |
|---|---|
| [RESUME.md](RESUME.md) | Turnkey next session: setup → discover → export → render |
| [FORMAT.md](FORMAT.md) | Complete `.chf` binary spec — container, CRC, DNA matrix, parameters, colors |
| [HEAD-IDS.md](HEAD-IDS.md) | The one unsolved piece: which preset head looks like what |
| [project.md](project.md) | Current work, next up, done |

## Tools

Pure Python. No dependencies beyond the `zstd` CLI.

```bash
brew install zstd        # macOS
winget install zstd      # Windows
```

**Read a character:**

```bash
python3 tools/chf.py dump character.chf   # human-readable
python3 tools/chf.py json character.chf   # machine-readable
```

**Edit a character:**

```bash
python3 tools/edit_chf.py base.chf edits.json out.chf
```

Edits are patched in place, so the parts of the format we have not fully
decoded survive byte-for-byte. See `samples/example_edit.json`:

```json
{
  "dna":    { "Nose": [[16, 0.657], [32, 0.343]] },
  "colors": { "BodyColor": "#ae7d66" },
  "floats": { "FrecklesAmount": 0.0 }
}
```

An empty spec (`{}`) produces a byte-identical payload — verified.

Example output:

```
DNA  gender=0xdd6c67f6  variant=0x69d4f6f4  parts=13
  Nose          head 16 @  65.7%  head 32 @  34.3%
  Jaw           head 14 @  62.6%  head 32 @  37.4%
  ...
COLORS
  BodyColor            #ae7d66
  EyeMakeupColor2      #fe6d42
FLOATS
  Makeup1OpacityR        +1.0000
  TattooHueRotation      +0.5656
```

Output is not byte-identical to the game's own encoder (different zstd
settings) but reparses cleanly and passes CRC validation. **Not yet confirmed
by an actual in-game import** — that is the first task in `RESUME.md`.

## Scripts (Windows, untested)

`scripts/` holds the asset-extraction pipeline. All of it was written on macOS
without a game install, so expect to fix something.

```
00_setup.ps1        install Rust + Blender, build StarBreaker, locate Data.p4k
01_discover.ps1     search the p4k for head mesh assets
02_export_heads.ps1 export those meshes to .glb
03_render_sheets.py Blender headless: render per-head contact sheets
```

## Game paths

```
Windows   StarCitizen\LIVE\user\client\0\CustomCharacters\
```

## Prior art

Credit where it is due — [diogotr7/StarBreaker](https://github.com/diogotr7/StarBreaker)
did the original reverse-engineering. Our spec was derived independently from a
sample file and then cross-checked against their `starbreaker-chf` crate; the
two agree. Their `name_hash.rs` name table is the source for the hash→name
mappings reproduced in `tools/chf.py`.

Others: [starchar](https://github.com/diogotr7/starchar) (web editor,
[starchar.app](https://starchar.app)) ·
[SCCharacters](https://github.com/Spieler1ONE1/SCCharacters) (Python preset
manager) · [star-citizen-characters.com](https://www.star-citizen-characters.com/)
(community sharing).
