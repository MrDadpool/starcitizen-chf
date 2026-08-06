# Photo → `.chf`

**Goal:** hand the tool one or more reference photos, get back a `.chf` that
loads in Star Citizen and looks like that person.

Automatic. No eyeballing contact sheets, no manual slider hunting.

---

## Why this is tractable

The character creator does not sculpt. Each of 13 face parts is a weighted
blend of preset head meshes:

```
Nose = head16 @ 65.7% + head32 @ 34.3%
```

StarBreaker calls the DNA block "morph blend data", and the mesh chunk table
contains `MESH_MORPH_TARGET (0x1011)`. Morph targets **share one topology** —
vertex 4211 is the same point on the face in every head.

That single fact is what makes this solvable rather than a guessing game:

> A blended face is a **linear combination** of head vertex arrays.

So fitting a photo is not search-by-vibes. It is least squares.

**Assumption, not yet verified.** Shared topology is inferred from the chunk
type and the blend semantics. Step 1 below checks it directly, and the whole
approach depends on the answer. If topology turns out to differ per head, we
fall back to the landmark-from-renders method in "Fallback" at the bottom —
slower, still automatic.

---

## The pipeline

### Phase A — build the head basis (once)

1. Export every head mesh from `Data.p4k` to GLB (`scripts/02_export_heads.ps1`).
2. **Verify shared topology**: identical vertex count and face indices across
   all heads. This is the gate.
3. Stack into a basis array `V[head, vertex, xyz]`.

Cached to disk. Never recomputed.

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

## Fallback if topology is not shared

Render each head from fixed cameras, run the same landmark detector on the
renders, and solve in 2-D landmark space instead of 3-D vertex space. Landmark
position is still close to linear in blend weight, so the same least-squares
structure applies. Slower to set up, no manual matching, works either way.

---

## Status

Phase A is blocked on `Data.p4k` (Windows only). Phases B–E are unwritten.
The `.chf` reader, writer and editor are done and tested — see `README.md`.

Tracking in `project.md`.
