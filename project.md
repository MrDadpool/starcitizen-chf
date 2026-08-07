# Project: Star Citizen character from reference image

**Goal:** hand the tool one or more reference photos, get back a `.chf` that
loads in Star Citizen and looks like that person. Automatic — no manual slider
hunting, no eyeballing preset heads.

Design in [PIPELINE.md](PIPELINE.md).

**Started:** 2026-08-06

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
- **Windows pipeline scripts written** (`scripts/00`–`03`). Since fixed and run
  on a real machine — see the 2026-08-06 Windows session below.
- **`RESUME.md` written.** Turnkey checklist for the Windows session.

### 2026-08-06 — first run on Windows with a live install

- **Toolchain up.** Python 3.14.6, zstd 1.5.7, Git, Rust 1.97.1, Blender 5.2.0
  LTS, `starbreaker.exe` built. `Data.p4k` (152 GB) found on `F:`.
- **Undocumented prerequisite found.** StarBreaker needs MSVC Build Tools with
  the C++ workload — its dependency tree pulls in `zstd-sys`, `ring` and
  `rav1e`, which need a C toolchain. Rust alone fails with
  `linker link.exe not found`. Neither `RESUME.md` nor `00_setup.ps1` mentions
  it.
- **`chf.py` parser bug fixed.** `find_blocks` assumed the float block was
  sorted ascending by hash. That was a property of `combat_veteran.chf`, not an
  invariant: **3 of 6 live characters** store it unsorted and failed outright.
  Now anchors on the declared u64 count. All 7 files parse.
- **Cross-validated.** StarBreaker ships its own `chf to-json`. It agrees with
  `chf.py` on part counts, head IDs and blend weights.
- **Round-trip verified end to end.** Payloads byte-identical (0 diffs), 4096-B
  size preserved, output reparses.
- **Writer validated in-game.** `roundtrip_test.chf`, produced by our encoder
  from `mr_val.chf`, imported in the character creator and rendered as the same
  face. This was the project's top blocker. It confirms the container is
  accepted and the payload survives intact, so byte-identical output is not
  required and the differing zstd settings are a non-issue.
- **Three PowerShell bugs fixed** — see the scripts commit: missing UTF-8 BOMs
  (PS 5.1 read them as ANSI and mangled every em-dash, leaving
  `01_discover.ps1` unparseable), a `2>&1` that aborted the whole discovery
  sweep on the first empty result, and glob patterns using bare `*` where `**/`
  is required, which silently matched nothing on all seven patterns.
- **Head asset hunt completed — negative result.** The 60 heads are not
  extractable as meshes. Details and dead ends in `HEAD-IDS.md`; consequences
  for the design in `PIPELINE.md`.

## Decision log

**2026-08-06 — full lane chosen.** Build the head contact-sheet pipeline rather
than working manually through starchar.app. Rationale: one-time cost, and it is
the only approach that makes reference-image matching repeatable.

Work continues on the user's Windows PC (game is Windows-only). Nothing
installed on the Mac.

## Next up

1. ~~Round-trip import test~~ — **done, passed.** See Completed.
2. **Decide the head-basis route** (see `HEAD-IDS.md`):
   - reverse-engineer `RIG V1.9` for per-head joint deltas, or
   - build the catalog empirically — 60 single-head `.chf` files, import,
     screenshot. Recommended: far less work, uses only tooling that works.
3. Once a basis exists, write Phases B–E from `PIPELINE.md` against 2-D
   landmarks rather than 3-D vertices.

Steps 2–6 of the old plan (`01_discover` → `02_export_heads` →
`03_render_sheets` → match against sheets) are retired. Discovery is done, and
there are no per-head meshes to export or render.

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

- **`RIG V1.9` format is undecoded.** This is now the main unknown. Head
  identity data is presumed to live here. StarBreaker names the chunk type but
  does not parse standalone `.RigLogic` files.
- Container header bytes `0x02..0x04` (flags/version) — preserved, purpose
  unknown.
- `header_unknown` u16 in the DNA block.
- Trailing GUID tables past payload `0x053A` (material variants / loadout).
- ~~Written files are not byte-identical to the game's encoder~~ — no longer a
  gap. The decompressed payload *is* byte-identical across four live
  characters; only the compressed frame differs, and an in-game import
  confirmed the game does not care.
- ~~`part_count` 12 vs 13 unexplained~~ — resolved. `FORMAT.md` already
  records it: `Neck` was added in v8, so pre-v8 characters have 12 parts. It is
  the last entry, so `FACE_PARTS` names stay aligned either way. Confirmed
  against live files: not gender-linked (`combat_veteran` is male with 13,
  `mr_val` male with 12).

## Untested

The read/write path is now fully validated, including in-game. What remains
untested is `scripts/02_export_heads.ps1` and `scripts/03_render_sheets.py` —
and those are moot, since there are no per-head meshes for them to process.
