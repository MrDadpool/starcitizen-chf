# Resume here — Windows PC

> ## Steps 1–4 are done. Read this first.
>
> This session ran on 2026-08-06 against a live install. Current state:
>
> - **Setup (step 1): complete.** Python, zstd, Git, Rust, Blender all present;
>   `starbreaker.exe` built; `Data.p4k` found on `F:`. Re-running
>   `00_setup.ps1` is a no-op. One prerequisite was missing from the list
>   below — see *Prerequisites*.
> - **Discovery (step 2): complete, and the answer is negative.** The head
>   meshes this plan assumes **do not exist as extractable assets**. See
>   [HEAD-IDS.md](HEAD-IDS.md).
> - **Steps 3–4 (export meshes, render contact sheets): retired.** Nothing to
>   export or render.
> - **The sanity check passed.** `roundtrip_test.chf` — written by our encoder
>   from `mr_val` — imported and rendered as the same face. The writer is
>   validated end to end. Nothing downstream is blocked on it any more.
>
> Read the sanity check, then skip to [PIPELINE.md](PIPELINE.md) and
> [HEAD-IDS.md](HEAD-IDS.md) for where the project actually stands. Steps 1–4
> are kept below as a record of what was run.

---

## Before anything: the 5-minute sanity check

This is the single most valuable thing to do first, because every later step
assumes it passes. It proves our writer produces a file the game accepts.

**Done, and it passed.** `roundtrip_test.chf` was generated from `mr_val.chf`,
imported in the character creator, and looked identical. Automated checks had
already passed — decompressed payload byte-identical to the original (0 diffs
across four characters), 4096-byte size preserved, output reparses — and the
import confirmed the part they could not: the game accepts our container and
reads our payload correctly despite the compressed frame differing.

The commands that produced it, for reference:

```powershell
# 1. Copy one of your own characters out of the game
copy "F:\Robert Space Industries\StarCitizen\LIVE\user\client\0\CustomCharacters\mr_val.chf" test_in.chf

# 2. Read it, write it back unchanged
python tools\chf.py dump test_in.chf
python tools\edit_chf.py test_in.chf samples\noop_edit.json test_out.chf

# 3. Put it back and import in-game
copy test_out.chf "...\CustomCharacters\roundtrip_test.chf"
```

Launch the character creator, import `roundtrip_test`.

- **Loads, looks identical** → writer is good. Everything downstream is unblocked.
- **Refuses to load** → stop. The container is fine (CRC verified) but something
  in the payload is validated in a way we have not found. Tell me and I will
  dig into the trailing GUID tables.

Our output is not byte-identical to the game's own encoder — our zstd settings
differ. The CRC is recomputed correctly and it reparses cleanly, but only an
actual import proves it.

---

## Step 1 — setup

**Look before installing:**

```powershell
.\scripts\preflight.ps1
```

Installs nothing. Reports what you already have, with paths and versions, and
finds `Data.p4k` by scanning every fixed drive (so an F: install is found
automatically). Detection is deliberate about two Windows traps:

- `python.exe` under `WindowsApps` is a Microsoft Store stub, not Python. It is
  rejected, and the `py` launcher is used as a fallback.
- Blender and Rust routinely install without landing on PATH, so their usual
  install roots are searched directly.

Then install only what is missing:

```powershell
.\scripts\00_setup.ps1 -WhatIf   # print the plan, install nothing
.\scripts\00_setup.ps1           # prompts y/N before touching anything
```

It never reinstalls or upgrades a tool you already have, and it skips
`cargo build` if `starbreaker.exe` is already there.

Just the `.chf` tools, no Rust or Blender:

```powershell
.\scripts\00_setup.ps1 -CoreOnly
```

If `Data.p4k` is not found automatically:

```powershell
.\scripts\00_setup.ps1 -P4kPath "F:\Roberts Space Industries\StarCitizen\LIVE\Data.p4k"
```

The Rust build takes several minutes. Normal.

## Step 2 — find the head assets — **DONE, negative result**

```powershell
.\scripts\01_discover.ps1
```

Dumps candidate asset listings to `out\discovery\*.txt`. Ran clean after three
bug fixes (BOM, stderr handling, `**/` globs).

The two known hashes resolved to real assets:

```
Data\Objects\Characters\RigLogic\protos_human_male_face_t1_pu.RigLogic
Data\Objects\Characters\RigLogic\protos_human_female_face_t1_pu.RigLogic
```

But **there is no set of ~60 head meshes to find.** One protos head mesh per
gender, 5584 verts, zero morph targets, driven by a 198-bone facial rig. Full
account of what was searched and ruled out: [HEAD-IDS.md](HEAD-IDS.md).

## Step 3 — export meshes — **RETIRED**

Nothing to export. Kept for the record.

Once we have the right paths:

```powershell
.\scripts\02_export_heads.ps1 -PathList out\discovery\<the_right_one>.txt
```

Writes `.glb` per mesh into `out\heads\`.

## Step 4 — render contact sheets — **RETIRED**

No meshes to render. Kept for the record. The equivalent capture now happens
in-game (emit → import → screenshot); see [HEAD-IDS.md](HEAD-IDS.md).

Smoke test on 4 meshes first — do not sit through a full run of a broken script:

```powershell
blender --background --python scripts\03_render_sheets.py -- `
    --glb-dir out\heads --out-dir out\sheets --limit 4
```

Look at `out\sheets\tiles\*.png`. If the framing and lighting are sane, drop
`--limit` and run the lot.

Output: `out\sheets\contact_sheet_front.png`,
`contact_sheet_threequarter.png`, and `index.txt` giving tile order.

## Step 5 — the actual goal

**Read [PIPELINE.md](PIPELINE.md).** The end state is unchanged: photos in,
`.chf` out, solved by least squares. What changed is the basis it solves
against.

The `check_topology.py` gate that used to live here is moot — it compared
vertex counts across exported head meshes, and there are none. The design now
takes the **Fallback** route in `PIPELINE.md`: solve in 2-D landmark space
against captured renders instead of 3-D vertex space.

Before any of that, the head basis has to exist at all. That is the open
decision in [HEAD-IDS.md](HEAD-IDS.md) — decode `RIG V1.9`, or build the
catalog empirically by emitting 60 single-head `.chf` files and screenshotting
each in the creator. The second is recommended.

---

## What is already done and tested

| Thing | Status |
|---|---|
| `.chf` container spec, CRC32C, zstd | verified against a real file |
| DNA blend matrix, floats, colors | fully decoded, `FORMAT.md` |
| `tools/chf.py` read/write | round-trips, CRC valid; parses 6 live characters + sample |
| `tools/edit_chf.py` | tested: 23 bytes changed, all inside targeted records |
| Payload round-trip | byte-identical across 4 live characters |
| Cross-check vs StarBreaker `chf to-json` | agrees on parts, head IDs, weights |
| **In-game import of our own output** | **passed — loads and looks identical** |
| `scripts/preflight.ps1`, `00_setup.ps1`, `01_discover.ps1` | run on a real machine |

## What is untested

- `scripts/02_export_heads.ps1` and `scripts/03_render_sheets.py`. Never run,
  and now moot — there are no per-head meshes for them to operate on. The
  Blender script's version-sensitive API calls (`BLENDER_EEVEE_NEXT`,
  `import_scene.gltf`) remain unverified against the installed Blender 5.2.

## The known hard limit

The creator blends a fixed gene pool. A face far outside it is not reachable at
any weight. Bone structure is usually the wall, not the tooling. See
`HEAD-IDS.md`.

---

## Prerequisites

`scripts\00_setup.ps1` installs all of these via winget. Listed here so you
know what is landing on the machine.

| Tool | Why | Size |
|---|---|---|
| **winget** | package manager. Ships with Win11; on Win10 install "App Installer" from the Microsoft Store | — |
| **MSVC Build Tools** | **was missing from this list.** StarBreaker's deps (`zstd-sys`, `ring`, `rav1e`) are C/asm, so Rust's msvc target needs a real C toolchain. Without it the build dies with `linker link.exe not found`. Install `Microsoft.VisualStudio.2022.BuildTools` with the `VCTools` workload | ~3–6 GB |
| **Python 3** | runs `chf.py` / `edit_chf.py` | ~100 MB |
| **zstd** | `chf.py` shells out to it for the payload | ~5 MB |
| **Git** | clone StarBreaker | ~300 MB |
| **Rust** (rustup) | builds StarBreaker's extractor. No prebuilt binary is published | ~1.5 GB, plus ~2 GB of build artifacts |
| **Blender** | headless mesh rendering for the contact sheets | ~1.5 GB |

Roughly **6 GB** of tooling, plus whatever the extracted meshes come to
(unknown until step 2 — likely a few GB, not the full 100 GB p4k; we export
only head assets).

Star Citizen itself must already be installed — we read `Data.p4k` in place and
never modify it.

### If you want to skip Rust and Blender

Steps 1–2 of the sanity check only need **Python + zstd**. That is enough to
read your own `.chf` files, edit colors and DNA numerically, and confirm the
round-trip import works. Rust and Blender are only for rendering the head
contact sheets in steps 3–5.
