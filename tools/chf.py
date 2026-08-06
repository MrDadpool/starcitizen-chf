#!/usr/bin/env python3
"""Star Citizen .chf reader/writer.

Format spec: ../FORMAT.md

Requires the `zstd` CLI on PATH (Homebrew: `brew install zstd`).

    python3 chf.py dump  path/to/file.chf
    python3 chf.py json  path/to/file.chf
"""

import json
import struct
import subprocess
import sys
from pathlib import Path

CHF_SIZE = 4096
MAGIC = 0x4242
MODDED_MARKER = b"diogotr7"

# ---------------------------------------------------------------- crc32c

_POLY = 0x82F63B78
_TABLE = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ (_POLY if _c & 1 else 0)
    _TABLE.append(_c)


def crc32c(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc = _TABLE[(crc ^ byte) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF


# ---------------------------------------------------------------- zstd


def zstd_decompress(frame: bytes) -> bytes:
    return subprocess.run(
        ["zstd", "-dc"], input=frame, capture_output=True, check=True
    ).stdout


def zstd_compress(raw: bytes) -> bytes:
    return subprocess.run(
        ["zstd", "-1", "-c"], input=raw, capture_output=True, check=True
    ).stdout


# ---------------------------------------------------------------- names

FACE_PARTS = [
    "EyebrowLeft", "EyebrowRight", "EyeLeft", "EyeRight", "Nose",
    "EarLeft", "EarRight", "CheekLeft", "CheekRight", "Mouth",
    "Jaw", "Crown", "Neck",
]

# Names whose CRC32C equals their identifier.
KNOWN_NAMES = [
    "BaseMelanin", "BaseMelaninRedness", "BaseMelaninVariation",
    "DyeAmount", "DyeFadeout", "DyePigmentVariation", "DyeShift",
    "FrecklesAmount", "FrecklesOpacity",
    "SunSpotsAmount", "SunSpotsOpacity",
    "TattooAge", "TattooHueRotation",
    "TattooNumTilesU", "TattooNumTilesV", "TattooOffsetU", "TattooOffsetV",
    "dna matrix 1.0", "head", "material_variant", "body_m", "limbs_m",
    "f_limbs_m", "f_torso_m",
    "shader_Head", "shader_head", "shader_eyeInner", "shader_eyeinner",
    "protos_human_male_face_t1_pu", "protos_human_female_face_t1_pu",
    "beard_itemport", "body_itemport", "eyebrow_itemport",
    "eyelashes_itemport", "eyes_itemport", "hair_itemport", "head_itemport",
    "stubble_itemport", "universal_scalp_itemport",
    "piercings_eyebrows_itemport", "piercings_l_ear_itemport",
    "piercings_mouth_itemport", "piercings_nose_itemport",
    "piercings_r_ear_itemport",
]
for _n in range(1, 4):
    for _suffix in ("MetalnessR", "MetalnessG", "MetalnessB",
                    "SmoothnessR", "SmoothnessG", "SmoothnessB",
                    "OpacityR", "OpacityG", "OpacityB", "Opacity",
                    "NumTilesU", "NumTilesV", "OffsetU", "OffsetV"):
        KNOWN_NAMES.append(f"Makeup{_n}{_suffix}")

# Hashes that are not the CRC32C of their display name.
MANUAL_MAPPINGS = {
    0xA98BEB34: "Head Material",
    0x6C836947: "HairDyeMaterial",
    0x078AC8BD: "EyebrowDyeMaterial",
    0xA047885E: "EyeMaterial",
    0x9B274D93: "BeardDyeMaterial",
    0x27424D58: "BodyMaterial",
    0xA8770416: "DyeMaterial",
    0xBD530797: "BodyColor",
    0xB29B1D90: "EyeMakeupColor1",
    0xE3230E2F: "EyeMakeupColor2",
    0x2EC0E736: "EyeMakeupColor3",
    0x1A081A93: "CheekMakeupColor1",
    0x4BB0092C: "CheekMakeupColor2",
    0x8653E035: "CheekMakeupColor3",
    0x7D86E792: "LipMakeupColor1",
    0x2C3EF42D: "LipMakeupColor2",
    0xE1DD1D34: "LipMakeupColor3",
    0x442A34AC: "EyeColor",
    0x15E90814: "HairDyeColor1",
    0xA2C7C909: "HairDyeColor2",
    0x4E865B74: "EyebrowDye",
    0x3B73D344: "StubbleDye",
    0x8792319B: "BeardDye",
    0x2C6279E6: "HairDye",
    0x75196D10: "EyebrowDye2",
    0x9F37AD63: "EyebrowDye3",
    0x1F1FAD17: "HairDye2",
    0x13170B02: "HairDye3",
}

HASH_TO_NAME = {crc32c(n.encode()): n for n in KNOWN_NAMES}
HASH_TO_NAME.update(MANUAL_MAPPINGS)


def name_of(h: int) -> str:
    return HASH_TO_NAME.get(h, f"0x{h:08x}")


# ---------------------------------------------------------------- container


class ChfFile:
    def __init__(self, payload: bytes, flags: bytes = b"\xce\x12",
                 modded: bool = False):
        self.payload = payload
        self.flags = flags
        self.modded = modded

    @classmethod
    def load(cls, path) -> "ChfFile":
        raw = Path(path).read_bytes()
        if len(raw) != CHF_SIZE:
            raise ValueError(f"expected {CHF_SIZE} bytes, got {len(raw)}")

        magic = struct.unpack_from("<H", raw, 0)[0]
        if magic != MAGIC:
            raise ValueError(f"bad magic 0x{magic:04x}")

        flags = raw[2:4]
        expected_crc, comp_size, decomp_size = struct.unpack_from("<III", raw, 4)

        actual_crc = crc32c(raw[16:CHF_SIZE])
        if actual_crc != expected_crc:
            raise ValueError(
                f"CRC mismatch: header 0x{expected_crc:08x}, "
                f"computed 0x{actual_crc:08x}"
            )

        # Slice to exactly comp_size — the zero padding breaks zstd otherwise.
        payload = zstd_decompress(raw[16:16 + comp_size])
        if len(payload) != decomp_size:
            raise ValueError(
                f"size mismatch: header {decomp_size}, got {len(payload)}"
            )

        return cls(payload, flags, raw[-8:] == MODDED_MARKER)

    def save(self, path) -> None:
        frame = zstd_compress(self.payload)
        body = bytearray(CHF_SIZE - 16)
        if len(frame) > len(body):
            raise ValueError(f"payload too large: {len(frame)} > {len(body)}")
        body[:len(frame)] = frame
        if self.modded:
            body[-8:] = MODDED_MARKER

        header = struct.pack(
            "<H2sIII", MAGIC, self.flags, crc32c(bytes(body)),
            len(frame), len(self.payload),
        )
        Path(path).write_bytes(header + bytes(body))


# ---------------------------------------------------------------- payload


def parse_dna(payload: bytes, offset: int = 0x28) -> dict:
    """Parse the DNA blend matrix (face shape)."""
    size = struct.unpack_from("<Q", payload, offset)[0]
    o = offset + 8

    magic, gender, variant, zero = struct.unpack_from("<IIII", payload, o)
    if magic != crc32c(b"dna matrix 1.0"):
        raise ValueError(f"bad DNA magic 0x{magic:08x} at 0x{o:x}")
    o += 16

    part_count, blends_per_part, unknown, max_head = struct.unpack_from(
        "<HHHH", payload, o
    )
    o += 8

    flat = [
        struct.unpack_from("<HH", payload, o + 4 * i)
        for i in range(part_count * blends_per_part)
    ]

    parts = {}
    for p in range(part_count):
        # Interleaved: index i -> part = i % part_count, blend = i // part_count
        parts[FACE_PARTS[p]] = [
            {"head_id": flat[b * part_count + p][1],
             "weight": round(flat[b * part_count + p][0] / 65535, 5)}
            for b in range(blends_per_part)
        ]

    return {
        "size": size,
        "gender_hash": f"0x{gender:08x}",
        "variant_hash": f"0x{variant:08x}",
        "part_count": part_count,
        "blends_per_part": blends_per_part,
        "header_unknown": unknown,
        "max_head_id": max_head,
        "parts": parts,
        "end": offset + 8 + size,
    }


def _scan_records(payload: bytes, start: int, end: int, decode):
    """Walk 12-byte records: u32 hash, 4-byte value, u32 zero padding."""
    out = []
    o = start
    while o + 12 <= end:
        h = struct.unpack_from("<I", payload, o)[0]
        out.append((name_of(h), h, decode(payload[o + 4:o + 8])))
        o += 12
    return out


def find_blocks(payload: bytes, dna_end: int) -> dict:
    """Locate the float and color record blocks.

    Both use a 12-byte stride. The float block is sorted ascending by hash,
    which makes it the reliable anchor: find the longest run of stride-12
    records whose hashes are ascending and all resolve. The u32 immediately
    after it is the color count, and the colors follow 8 bytes later.

    Colors are NOT sorted, so they cannot be found the same way.
    """
    best = (0, 0)  # (start, length)
    for start in range(dna_end, len(payload) - 12):
        prev = None
        n = 0
        o = start
        while o + 12 <= len(payload):
            h = struct.unpack_from("<I", payload, o)[0]
            if h not in HASH_TO_NAME or (prev is not None and h <= prev):
                break
            prev = h
            n += 1
            o += 12
        if n > best[1]:
            best = (start, n)

    float_start, n = best
    if n < 4:
        raise ValueError("could not locate float parameter block")

    # Both blocks carry a u64 count 8 bytes ahead of their first record.
    # Use it to confirm the scan landed on the true start.
    declared = struct.unpack_from("<Q", payload, float_start - 8)[0]
    if declared != n:
        raise ValueError(
            f"float block count mismatch: declared {declared}, scanned {n}"
        )

    float_end = float_start + n * 12

    color_count = struct.unpack_from("<I", payload, float_end)[0]
    color_start = float_end + 8
    if not (0 <= color_count <= 128) or color_start + color_count * 12 > len(payload):
        raise ValueError(f"implausible color count {color_count}")

    return {
        "float_start": float_start,
        "float_end": float_end,
        "color_count": color_count,
        "color_start": color_start,
    }


def parse(path) -> dict:
    chf = ChfFile.load(path)
    p = chf.payload
    dna = parse_dna(p)
    blocks = find_blocks(p, dna["end"])

    floats = _scan_records(
        p, blocks["float_start"], blocks["float_end"],
        lambda b: round(struct.unpack("<f", b)[0], 6),
    )
    colors_raw = _scan_records(
        p, blocks["color_start"],
        blocks["color_start"] + blocks["color_count"] * 12,
        lambda b: tuple(b),
    )

    # a=0 entries are packed UV transforms, not colors.
    colors = {n: f"#{r:02x}{g:02x}{b:02x}"
              for n, _h, (r, g, b, a) in colors_raw if a == 255}
    uv = {n: list(v) for n, _h, v in colors_raw if v[3] == 0}

    return {
        "file": str(path),
        "payload_size": len(p),
        "modded": chf.modded,
        "dna": dna,
        "floats": {n: v for n, _h, v in floats},
        "colors": colors,
        "uv_params": uv,
    }


# ---------------------------------------------------------------- cli


def dump(path) -> None:
    d = parse(path)
    print(f"{d['file']}  payload={d['payload_size']}B  modded={d['modded']}")

    dna = d["dna"]
    print(f"\nDNA  gender={dna['gender_hash']}  variant={dna['variant_hash']}"
          f"  parts={dna['part_count']}")
    for part, blends in dna["parts"].items():
        active = [b for b in blends if b["weight"] > 0]
        cells = "  ".join(
            f"head{b['head_id']:>3} @ {b['weight'] * 100:5.1f}%" for b in active
        )
        print(f"  {part:<13} {cells}")

    print("\nCOLORS")
    for name, hexval in sorted(d["colors"].items()):
        print(f"  {name:<20} {hexval}")

    print("\nFLOATS")
    for name, val in sorted(d["floats"].items()):
        print(f"  {name:<22} {val:+.4f}")


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in ("dump", "json"):
        print(__doc__)
        return 1
    if sys.argv[1] == "dump":
        dump(sys.argv[2])
    else:
        print(json.dumps(parse(sys.argv[2]), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
