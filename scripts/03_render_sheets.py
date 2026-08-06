"""Render head meshes to contact sheets for visual matching.

UNTESTED — written without Blender or the meshes on hand.

Run headless:

    blender --background --python scripts/03_render_sheets.py -- \
        --glb-dir out/heads --out-dir out/sheets

Produces, per head, a front and a 3/4 view on a neutral grey background with
flat three-point lighting, then tiles them into numbered contact sheets.
Deliberately unlit-looking and shadow-light: we are comparing silhouette and
proportion, not admiring renders.
"""

import argparse
import math
import os
import sys
from pathlib import Path

import bpy  # noqa: provided by Blender
import mathutils  # noqa: provided by Blender

RES = 512
SHEET_COLS = 8


def argv_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_world_and_lights():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = RES
    scene.render.resolution_y = RES
    scene.render.film_transparent = False

    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.18, 0.18, 0.18, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    scene.world = world

    # Three-point: key front-left, fill front-right, rim behind.
    for name, loc, energy in (
        ("key",  (-2.0, -3.0,  1.5), 400),
        ("fill", ( 2.5, -2.5,  0.5), 150),
        ("rim",  ( 0.0,  3.0,  2.0), 250),
    ):
        light = bpy.data.lights.new(name, type="AREA")
        light.energy = energy
        light.size = 2.0
        obj = bpy.data.objects.new(name, light)
        obj.location = loc
        obj.rotation_euler = _look_at(mathutils.Vector(loc), mathutils.Vector((0, 0, 0)))
        bpy.context.collection.objects.link(obj)


def _look_at(from_v, to_v):
    direction = to_v - from_v
    return direction.to_track_quat("-Z", "Y").to_euler()


def frame_camera(target_objs, angle_deg):
    """Place a camera at `angle_deg` around Z, framing the imported mesh."""
    # Bounding box across all imported objects, in world space.
    corners = []
    for obj in target_objs:
        for corner in obj.bound_box:
            corners.append(obj.matrix_world @ mathutils.Vector(corner))
    if not corners:
        raise RuntimeError("nothing to frame")

    lo = mathutils.Vector((min(c[i] for c in corners) for i in range(3)))
    hi = mathutils.Vector((max(c[i] for c in corners) for i in range(3)))
    center = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-4)

    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 85  # portrait-ish, minimal perspective distortion
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    theta = math.radians(angle_deg)
    dist = radius * 3.2
    cam.location = center + mathutils.Vector(
        (math.sin(theta) * dist, -math.cos(theta) * dist, radius * 0.15)
    )
    cam.rotation_euler = _look_at(cam.location, center)


def render_one(glb_path: Path, out_dir: Path) -> list:
    """Render a single GLB from two angles. Returns the written image paths."""
    written = []
    for label, angle in (("front", 0), ("threequarter", 35)):
        reset_scene()
        setup_world_and_lights()

        bpy.ops.import_scene.gltf(filepath=str(glb_path))
        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        if not meshes:
            print(f"  skip (no mesh): {glb_path.name}")
            return []

        frame_camera(meshes, angle)

        dest = out_dir / f"{glb_path.stem}__{label}.png"
        bpy.context.scene.render.filepath = str(dest)
        bpy.ops.render.render(write_still=True)
        written.append(dest)
    return written


def build_sheets(images: list, out_dir: Path, label: str):
    """Tile rendered PNGs into contact sheets using Blender's image API."""
    if not images:
        return
    rows = math.ceil(len(images) / SHEET_COLS)
    sheet_w = SHEET_COLS * RES
    sheet_h = rows * RES

    sheet = bpy.data.images.new(f"sheet_{label}", sheet_w, sheet_h, alpha=True)
    buf = [0.0] * (sheet_w * sheet_h * 4)

    for idx, path in enumerate(images):
        img = bpy.data.images.load(str(path))
        px = list(img.pixels)
        col = idx % SHEET_COLS
        row = rows - 1 - (idx // SHEET_COLS)  # Blender images are bottom-up
        for y in range(RES):
            src = y * RES * 4
            dst = ((row * RES + y) * sheet_w + col * RES) * 4
            buf[dst:dst + RES * 4] = px[src:src + RES * 4]
        bpy.data.images.remove(img)

    sheet.pixels = buf
    sheet.filepath_raw = str(out_dir / f"contact_sheet_{label}.png")
    sheet.file_format = "PNG"
    sheet.save()
    print(f"[ok] contact_sheet_{label}.png  ({len(images)} tiles)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb-dir", required=True)
    parser.add_argument("--out-dir", default="out/sheets")
    parser.add_argument("--limit", type=int, default=0,
                        help="render only the first N meshes (smoke test)")
    args = parser.parse_args(argv_after_dashdash())

    glb_dir = Path(args.glb_dir)
    out_dir = Path(args.out_dir)
    (out_dir / "tiles").mkdir(parents=True, exist_ok=True)

    glbs = sorted(glb_dir.glob("*.glb"))
    if args.limit:
        glbs = glbs[:args.limit]
    if not glbs:
        sys.exit(f"no .glb files in {glb_dir}")

    print(f"rendering {len(glbs)} meshes")

    fronts, quarters = [], []
    for i, glb in enumerate(glbs, 1):
        print(f"[{i}/{len(glbs)}] {glb.name}")
        for path in render_one(glb, out_dir / "tiles"):
            (fronts if "__front" in path.name else quarters).append(path)

    build_sheets(fronts, out_dir, "front")
    build_sheets(quarters, out_dir, "threequarter")

    index = out_dir / "index.txt"
    index.write_text("\n".join(
        f"{i}\t{g.stem}" for i, g in enumerate(glbs)
    ))
    print(f"[ok] tile order written to {index}")


if __name__ == "__main__":
    main()
