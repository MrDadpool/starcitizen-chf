#!/usr/bin/env python3
"""Check whether exported head meshes share one topology.

    python3 check_topology.py out/heads

This is the gate for the whole photo-to-.chf design (see PIPELINE.md).

If every head has the same vertex count and the same triangle indices, the
heads are morph targets over a shared topology. Vertex i is then the same
point on the face in every head, a blended face is a linear combination of
vertex arrays, and fitting a photo reduces to least squares.

If topology differs, we fall back to solving in 2-D landmark space from
rendered views.

No dependencies — GLB is parsed directly.
"""

import json
import struct
import sys
from collections import Counter
from pathlib import Path

GLB_MAGIC = 0x46546C67  # "glTF"
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

# glTF componentType -> (struct format, byte size)
COMPONENT = {
    5120: ("b", 1), 5121: ("B", 1),
    5122: ("h", 2), 5123: ("H", 2),
    5125: ("I", 4), 5126: ("f", 4),
}
NUM_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path: Path):
    """Return (gltf_json, binary_chunk)."""
    data = path.read_bytes()
    if len(data) < 12:
        raise ValueError("too short to be a GLB")
    magic, version, _length = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC:
        raise ValueError(f"not a GLB (magic 0x{magic:08x})")
    if version != 2:
        raise ValueError(f"unsupported GLB version {version}")

    gltf, binary = None, b""
    offset = 12
    while offset + 8 <= len(data):
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        body = data[offset + 8:offset + 8 + chunk_len]
        if chunk_type == CHUNK_JSON:
            gltf = json.loads(body)
        elif chunk_type == CHUNK_BIN:
            binary = body
        offset += 8 + chunk_len + (-chunk_len % 4)  # chunks are 4-byte aligned

    if gltf is None:
        raise ValueError("no JSON chunk")
    return gltf, binary


def read_accessor(gltf, binary, index):
    """Read an accessor into a flat list. Sparse accessors are not supported."""
    acc = gltf["accessors"][index]
    if "sparse" in acc:
        raise ValueError("sparse accessors not supported")

    count = acc["count"]
    ncomp = NUM_COMPONENTS[acc["type"]]
    fmt, size = COMPONENT[acc["componentType"]]

    if "bufferView" not in acc:
        return [0] * (count * ncomp)  # spec: absent bufferView means zeros

    view = gltf["bufferViews"][acc["bufferView"]]
    base = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = view.get("byteStride") or (size * ncomp)

    out = []
    for i in range(count):
        off = base + i * stride
        out.extend(struct.unpack_from(f"<{ncomp}{fmt}", binary, off))
    return out


def summarize(path: Path) -> dict:
    """Vertex count, triangle count, and a hash of the index buffer."""
    gltf, binary = read_glb(path)

    verts = 0
    tris = 0
    index_sig = []

    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            pos = prim.get("attributes", {}).get("POSITION")
            if pos is None:
                continue
            verts += gltf["accessors"][pos]["count"]
            if "indices" in prim:
                idx = read_accessor(gltf, binary, prim["indices"])
                tris += len(idx) // 3
                # Hash rather than keep the whole buffer — these are large.
                index_sig.append(hash(tuple(idx)))

    return {
        "file": path.name,
        "vertices": verts,
        "triangles": tris,
        "index_hash": hash(tuple(index_sig)),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1

    glb_dir = Path(sys.argv[1])
    files = sorted(glb_dir.glob("*.glb"))
    if not files:
        print(f"no .glb files in {glb_dir}", file=sys.stderr)
        return 1

    print(f"checking {len(files)} meshes in {glb_dir}\n")

    results = []
    for path in files:
        try:
            results.append(summarize(path))
        except Exception as exc:
            print(f"  [skip] {path.name}: {exc}", file=sys.stderr)

    if not results:
        print("nothing parsed", file=sys.stderr)
        return 1

    vert_counts = Counter(r["vertices"] for r in results)
    index_hashes = Counter(r["index_hash"] for r in results)

    print(f"{'vertices':>10}  {'meshes':>7}")
    for count, n in vert_counts.most_common():
        print(f"{count:>10}  {n:>7}")

    shared_verts = len(vert_counts) == 1
    shared_index = len(index_hashes) == 1

    print()
    if shared_verts and shared_index:
        print("SHARED TOPOLOGY confirmed.")
        print("  Same vertex count and identical triangle indices across all heads.")
        print("  The blend is linear -> solve the photo fit directly in vertex space.")
        print("  Proceed with the main path in PIPELINE.md.")
        return 0

    print("TOPOLOGY DIFFERS.")
    if not shared_verts:
        print(f"  {len(vert_counts)} distinct vertex counts.")
    if not shared_index:
        print(f"  {len(index_hashes)} distinct index buffers.")
    print()
    print("  The heads are not a single morph set, at least not as exported.")
    print("  Two things to rule out before falling back:")
    print("    1. The export may be merging LODs or extra submeshes (eyes, lashes).")
    print("       Check whether the largest common vertex count dominates.")
    print("    2. Male and female heads are probably separate morph sets.")
    print("       Re-run this against one gender at a time.")
    print()
    print("  If it still differs, use the landmark fallback in PIPELINE.md.")

    # Grouping hint: a dominant cluster usually means the outliers are noise.
    top_count, top_n = vert_counts.most_common(1)[0]
    print(f"\n  largest group: {top_n}/{len(results)} meshes at {top_count} vertices")
    if top_n > len(results) * 0.6:
        print("  -> that group alone may well be a valid shared-topology basis")

    return 2


if __name__ == "__main__":
    sys.exit(main())
