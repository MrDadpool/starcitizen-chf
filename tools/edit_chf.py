#!/usr/bin/env python3
"""Apply an edit spec to a .chf file.

    python3 edit_chf.py base.chf edits.json out.chf

Edits are patched into the payload **in place**. Nothing is re-serialized from
scratch, so the parts of the format we do not fully understand (the trailing
GUID / loadout tables) survive byte-for-byte. Only the bytes we name change.

Edit spec format — every key optional:

    {
      "dna": {
        "Nose": [[16, 0.657], [32, 0.343]],
        "Jaw":  [[14, 0.626], [32, 0.374]]
      },
      "colors": { "BodyColor": "#ae7d66", "EyeColor": "#4a3728" },
      "floats": { "FrecklesAmount": 0.35, "BaseMelanin": 0.6 }
    }

`dna` values are `[[head_id, weight], ...]`, up to 4 blends per part, weights
0.0–1.0. Listing fewer than 4 zeroes the remaining slots.

Names must already exist in the base file. A name that is not present is an
error, not a silent no-op — the record blocks are fixed-size and we do not
know how the game reacts to a resized payload.
"""

import json
import struct
import sys
from pathlib import Path

from chf import (
    FACE_PARTS,
    ChfFile,
    find_blocks,
    name_of,
    parse_dna,
)


def _dna_record_offsets(payload: bytes, dna: dict, dna_offset: int = 0x28) -> dict:
    """Map (part_name, blend_index) -> byte offset of its 4-byte record."""
    # Header is: u64 size, 16 bytes of hashes, u32 zero, then 4 u16 fields.
    base = dna_offset + 8 + 16 + 8
    part_count = dna["part_count"]
    offsets = {}
    for p in range(part_count):
        for b in range(dna["blends_per_part"]):
            # Interleaved: flat index = blend * part_count + part
            flat = b * part_count + p
            offsets[(FACE_PARTS[p], b)] = base + 4 * flat
    return offsets


def _record_offsets(payload: bytes, start: int, count: int) -> dict:
    """Map name -> byte offset of the 4-byte value in each 12-byte record."""
    out = {}
    for i in range(count):
        o = start + 12 * i
        h = struct.unpack_from("<I", payload, o)[0]
        out[name_of(h)] = o + 4
    return out


def _parse_hex_color(value: str) -> tuple:
    s = value.lstrip("#")
    if len(s) not in (6, 8):
        raise ValueError(f"bad color {value!r}, want #rrggbb or #rrggbbaa")
    parts = tuple(int(s[i:i + 2], 16) for i in range(0, len(s), 2))
    return parts if len(parts) == 4 else parts + (255,)


def apply_edits(chf: ChfFile, edits: dict) -> list:
    """Patch `chf.payload` in place. Returns a list of change descriptions."""
    payload = bytearray(chf.payload)
    dna = parse_dna(bytes(payload))
    blocks = find_blocks(bytes(payload), dna["end"])

    floats = _record_offsets(
        bytes(payload), blocks["float_start"],
        (blocks["float_end"] - blocks["float_start"]) // 12,
    )
    colors = _record_offsets(
        bytes(payload), blocks["color_start"], blocks["color_count"]
    )
    blends = _dna_record_offsets(bytes(payload), dna)

    changes = []

    for part, spec in edits.get("dna", {}).items():
        if part not in FACE_PARTS[:dna["part_count"]]:
            raise KeyError(f"unknown face part {part!r}")
        if len(spec) > dna["blends_per_part"]:
            raise ValueError(
                f"{part}: {len(spec)} blends, max {dna['blends_per_part']}"
            )
        total = sum(w for _id, w in spec)
        if abs(total - 1.0) > 0.02:
            print(f"warning: {part} weights sum to {total:.3f}, not 1.0",
                  file=sys.stderr)
        for b in range(dna["blends_per_part"]):
            head_id, weight = spec[b] if b < len(spec) else (0, 0.0)
            value = max(0, min(65535, round(weight * 65535)))
            struct.pack_into("<HH", payload, blends[(part, b)], value, head_id)
        pretty = "  ".join(f"head{i} @ {w * 100:.1f}%" for i, w in spec)
        changes.append(f"dna    {part:<13} {pretty}")

    for name, value in edits.get("colors", {}).items():
        if name not in colors:
            raise KeyError(f"color {name!r} not present in base file")
        r, g, b, a = _parse_hex_color(value)
        struct.pack_into("<4B", payload, colors[name], r, g, b, a)
        changes.append(f"color  {name:<20} #{r:02x}{g:02x}{b:02x}")

    for name, value in edits.get("floats", {}).items():
        if name not in floats:
            raise KeyError(f"float {name!r} not present in base file")
        struct.pack_into("<f", payload, floats[name], float(value))
        changes.append(f"float  {name:<20} {float(value):+.4f}")

    chf.payload = bytes(payload)
    chf.modded = True
    return changes


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 1

    base_path, edits_path, out_path = sys.argv[1:4]
    chf = ChfFile.load(base_path)
    edits = json.loads(Path(edits_path).read_text())

    before = len(chf.payload)
    changes = apply_edits(chf, edits)
    assert len(chf.payload) == before, "payload size must not change"

    chf.save(out_path)

    print(f"{base_path} -> {out_path}")
    for line in changes:
        print(f"  {line}")
    print(f"  ({len(changes)} changes, payload {before}B unchanged)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
