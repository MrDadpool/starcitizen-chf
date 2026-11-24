# Project: Star Citizen character from reference image

**Goal:** hand the tool one or more reference photos, get back a `.chf` that
loads in Star Citizen and looks like that person. Automatic — no manual slider
hunting, no eyeballing preset heads.

Design in [PIPELINE.md](PIPELINE.md).

**Started:** 2026-08-06

Waiting on: David's Windows PC with Star Citizen installed to run the pipeline (scripts untested)
Next action: Round-trip import test: write an unmodified .chf, import in-game, confirm nothing changed

---

## Completed

- **Container format cracked.** 4096-byte file, `0x4242` magic, CRC32C over
  `bytes[16..4096]`, zstd-compressed payload. Verified against
  `combat_veteran.chf`: header CRC `0x8b316b5c` == computed.
- **Payload decoded.** DNA blend matrix (13 face parts × 4 blend slots),
  33 float parameters, 26 color/UV records. Documented in `FORMAT.md`.
- **Name hashing identified.** All identifiers are CRC32C of the ASCII name.
  Combined known-names table (210 entries) resolves 100% of hashes in the
  sample file.
- **Prior art surveyed.** StarBreaker is the authoritative reverse-engineering
  effort; our independent parse agrees with theirs. No separate slider-map
  grind needed.
- **`tools/chf.py` written.** Reads and writes `.chf`, pure Python + `zstd`
  CLI. Round-trip verified: reparses cleanly, CRC valid.

- **`tools/edit_chf.py` written.** Applies a JSON edit spec by patching payload
  bytes in place, so undecoded regions survive untouched. Tested: a 5-change
  spec altered 23 bytes, all inside the targeted records. An empty spec
  produces a byte-identical payload.
- **Windows pipeline scripts written** (`scripts/00`–`03`). Untested — no game
  install or Blender on the Mac they were written on.
- **`RESUME.md` written.** Turnkey checklist for the Windows session.

## Decision log

**2026-08-06 — full lane chosen.** Build the head contact-sheet pipeline rather
than working manually through starchar.app. Rationale: one-time cost, and it is
the only approach that makes reference-image matching repeatable.

Work continues on the user's Windows PC (game is Windows-only). Nothing
installed on the Mac.

## Next up

1. **Round-trip import test.** Write an unmodified `.chf`, import in-game,
   confirm nothing changed. Everything downstream assumes this passes.
2. `scripts/00_setup.ps1` — toolchain + StarBreaker build + locate `Data.p4k`.
3. `scripts/01_discover.ps1` — find head asset paths. **This is the real
   unknown.** Results need review before exporting.
4. `scripts/02_export_heads.ps1` → `.glb` per head.
5. `scripts/03_render_sheets.py` — contact sheets. Smoke-test with `--limit 4`.
6. Match reference image against sheets, emit `.chf`, iterate.

## Deferred until it works

Distribution as a free standalone app. Revisit once the solver produces a
likeness. Researched 2026-08-06, decided not to act on yet:

- **Head meshes cannot ship.** CIG copyright. The app must extract from the
  user's own install on first run and cache locally. This constrains the
  architecture, so it is worth remembering before packaging, not after.
- StarBreaker is **MIT** — vendoring or bundling a prebuilt binary is fine
  with attribution. MediaPipe (Apache 2.0), numpy/scipy (BSD) all fine.
- Rust is the awkward user dependency. Either bundle a prebuilt
  `starbreaker.exe` or port just the P4k reader to Python.
- Repo currently has **no LICENSE**, which means all rights reserved by
  default. Pick one before any release.
- Precedent: starchar.app distributes publicly and has been tolerated. Not
  permission — the EULA does restrict reverse engineering.

## Known gaps

- Container header bytes `0x02..0x04` (flags/version) — preserved, purpose
  unknown.
- `header_unknown` u16 in the DNA block.
- Trailing GUID tables past payload `0x053A` (material variants / loadout).
- Written files are not byte-identical to the game's encoder (zstd settings
  differ). Functionally fine; worth confirming with an actual in-game import
  before relying on it.

## Untested

Nothing has been imported into the game yet. First real validation should be:
write an unmodified round-trip `.chf`, import it, confirm the character is
unchanged.
