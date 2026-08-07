# Photo → `.chf`

**Goal:** hand the tool one or more reference photos, get back a `.chf` that
loads in Star Citizen and looks like that person.

Automatic. No eyeballing contact sheets, no manual slider hunting.

---

> ## ⚠️ Phase A does not work as written
>
> Checked 2026-08-06 against a live install. **The per-head meshes this design
> is built on do not exist as extractable assets.** There is one protos head
> mesh per gender (5584 verts, **zero morph targets**) driven by a 198-bone
> facial rig. See [HEAD-IDS.md](HEAD-IDS.md) for the full search.
>
> Phase A steps 1–3 and the `check_topology.py` gate have nothing to operate
> on, and `scripts/02_export_heads.ps1` has no per-head assets to export.
> Phases C–E are unaffected in *structure* — the solver maths below is still
> right — but they need a head basis that must now come from somewhere else.
>
> The cheapest route to that basis is the empirical catalog described in
> HEAD-IDS.md: emit 60 single-head `.chf` files, import, screenshot. That
> yields 2-D renders, which lands you in the **Fallback** section at the
> bottom of this document rather than the 3-D vertex path.

## Why this is tractable

The character creator does not sculpt. Each of 13 face parts is a weighted
blend of preset heads:

```
Nose = head16 @ 65.7% + head32 @ 34.3%
```

The blend is a **linear combination**, so fitting a photo is not
search-by-vibes — it is least squares. That much still holds, and it is what
makes the problem tractable at all.

What does *not* hold is the original justification for solving in 3-D vertex
space. This document previously argued that the mesh chunk table contains
`MESH_MORPH_TARGET (0x1011)` and that morph targets share one topology, so a
blended face is a linear combination of head vertex arrays. Exporting the
protos head yields **no morph targets at all**, so there are no per-head
vertex arrays to stack and the shared-topology question is moot.

Linearity in *landmark* space is the assumption that survives, and that is the
Fallback method.

---

## The pipeline

### Phase A — build the head basis (once)

**Superseded — see the warning at the top.** The original plan was:

1. Export every head mesh from `Data.p4k` to GLB (`scripts/02_export_heads.ps1`).
2. **Verify shared topology**: identical vertex count and face indices across
   all heads. This is the gate.
3. Stack into a basis array `V[head, vertex, xyz]`.

There are no per-head meshes to export, so none of this runs. The replacement
is the empirical catalog: for each face part, emit 60 `.chf` files with one
head at 100%, import each, and screenshot the creator. The result is a set of
2-D renders per head rather than a vertex basis — which is exactly the input
the Fallback method expects.

Still cached to disk, still never recomputed. But it is a one-time *manual*
capture pass, not an automated extraction.

### Phase B — landmark correspondence (once)

Choose which mesh vertices correspond to standard face landmarks (eye corners,
nose tip and alar bases, lip contour, jaw silhouette, brow ridge).

Done by fitting a canonical face topology to the neutral head once, then
storing the vertex indices. A few hundred points, one file, reused forever.

Each landmark is tagged with the face part that owns it, so the solver knows
that a nose landmark constrains the `Nose` blend and nothing else.

### Phase C — solve (per photo set)

1. **Detect landmarks in the reference photo.** MediaPipe FaceMesh gives 468
   points. Multiple photos (front, 3/4, profile) constrain depth far better
   than one; the solver takes any number.

2. **Estimate camera pose** per photo — focal length and head orientation —
   so mesh landmarks can be projected into image space.

3. **Fit each face part independently.** The creator allows only 2 blend slots
   per part, so for each part:

   - for every candidate pair of heads `(a, b)`
   - solve the optimal weight `w` in closed form (it is a 1-D least squares)
   - keep the pair with the lowest landmark reprojection error

   With ~60 heads that is ~1770 pairs per part, 13 parts. Brute force is
   milliseconds. No local minima, no gradient descent, no training.

4. **Joint refinement.** Alternate between camera pose and blend weights until
   the error stops dropping. A handful of iterations.

### Phase D — appearance

Face shape is geometry. The rest is sampled from the photo:

- **`BodyColor`** — skin tone, sampled from cheek and forehead regions with
  specular highlights rejected, white-balanced against the image.
- **`FrecklesAmount` / `SunSpotsAmount`** — from high-frequency texture energy
  in the cheek region.
- **`EyeColor`** — sampled from the iris annulus.
- **Hair, beard, brows** — these are *asset picks*, not blends. The `.chf`
  stores a GUID reference. Best we can do is nearest match from the available
  set, chosen by length and style. Expect to override this by hand.

### Phase E — emit and iterate

`edit_chf.py` writes the file. You import, screenshot, and the screenshot goes
back through Phase C as a second reference — closing the loop against what the
game actually renders rather than what we predicted.

---

## What you will need to provide

| Input | Why |
|---|---|
| **1 front photo, neutral expression** | minimum viable |
| **+ 3/4 view** | resolves depth; strongly recommended |
| **+ profile** | nails nose and jaw projection |

Even lighting, no heavy smile, hair off the forehead. Glasses off.

---

## Honest limits

**The gene pool is the wall.** The creator blends a fixed set of preset heads.
A face outside the span of that set is not reachable at any weight. The solver
will return the closest point in the reachable space and report its residual
error, so you will know whether it is a good likeness or the best of a bad set.
This is a property of the game, not of the tooling.

**Skin and hair are approximations.** Skin is one flat colour plus a few
parameters, not a texture. Hair is a pick from a list.

**Expression is not identity.** A photo mid-smile fits a smiling shape into a
neutral rig. Neutral photos only.

---

## Fallback — now the primary route

Originally written as the contingency "if topology is not shared". It is now
the main path, because there is no vertex basis to solve against.

Capture each head from fixed cameras, run the same landmark detector on those
images, and solve in 2-D landmark space instead of 3-D vertex space. Landmark
position is still close to linear in blend weight, so the same least-squares
structure applies.

One change from the original framing: the renders cannot come from Blender,
because there are no head meshes to render. They come from the game's own
character creator, via the emit-import-screenshot loop. That makes the capture
pass manual and slow — 60 heads × the face parts you care about — but it only
happens once, and it measures what the game actually draws rather than what we
predicted it would.

---

## Status

**Phase A is blocked on format, not tooling.** The Windows toolchain is fully
working — `Data.p4k` located, StarBreaker built, meshes exportable — but the
per-head assets the design assumed are not in the archive. See
[HEAD-IDS.md](HEAD-IDS.md).

Phases B–E are unwritten. The `.chf` reader, writer and editor are done and
tested against six characters from a live install — see `README.md`.

Tracking in `project.md`.
