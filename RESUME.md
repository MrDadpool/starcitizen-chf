# Resume here — Windows PC

Everything that can be built without the game is built and tested. What is left
needs `Data.p4k`, which only exists on the Windows install.

**Read this top to bottom. It is the whole night's work.**

---

## Before anything: the 5-minute sanity check

This is the single most valuable thing to do first, because every later step
assumes it passes. It proves our writer produces a file the game accepts.

```powershell
# 1. Copy one of your own characters out of the game
copy "$env:USERPROFILE\...\StarCitizen\LIVE\user\client\0\CustomCharacters\<yours>.chf" test_in.chf

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

```powershell
.\scripts\00_setup.ps1
```

Installs Python, zstd, Git, Rust and Blender via winget; clones and builds
StarBreaker; finds `Data.p4k` and sets `SC_DATA_P4K`. Full list under
[Prerequisites](#prerequisites) below.

If it cannot find `Data.p4k`, set it by hand and re-run:

```powershell
[Environment]::SetEnvironmentVariable("SC_DATA_P4K","D:\path\to\Data.p4k","User")
```

The Rust build takes several minutes. Normal.

## Step 2 — find the head assets

```powershell
.\scripts\01_discover.ps1
```

Dumps candidate asset listings to `out\discovery\*.txt`.

**We do not know the real head asset paths yet.** This is the actual unknown in
the whole project. The script casts a wide net; the answer is somewhere in
those files. Two known-good starting hashes from the CHF name table:

```
protos_human_male_face_t1_pu
protos_human_female_face_t1_pu
```

**Send me the contents of `out\discovery\` and I will pick the exact paths.**
Do not guess at this step — a wrong pattern means exporting thousands of
irrelevant meshes.

## Step 3 — export meshes

Once we have the right paths:

```powershell
.\scripts\02_export_heads.ps1 -PathList out\discovery\<the_right_one>.txt
```

Writes `.glb` per mesh into `out\heads\`.

## Step 4 — render contact sheets

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

Send me the contact sheets plus your reference image. I map each face part to
its two nearest heads, write an edit spec, and `edit_chf.py` emits the file.
Then we iterate: you import, screenshot, I adjust.

---

## What is already done and tested

| Thing | Status |
|---|---|
| `.chf` container spec, CRC32C, zstd | verified against a real file |
| DNA blend matrix, floats, colors | fully decoded, `FORMAT.md` |
| `tools/chf.py` read/write | round-trips, CRC valid |
| `tools/edit_chf.py` | tested: 23 bytes changed, all inside targeted records |

## What is untested

Everything in `scripts/`. Written on macOS with no game install and no Blender.
The PowerShell may have path bugs; the Blender script's API calls
(`BLENDER_EEVEE_NEXT`, `import_scene.gltf`) are version-sensitive. Expect to fix
one or two things. Send me errors rather than fighting them.

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
