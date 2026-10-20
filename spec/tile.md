# Tiles in an area (`SET-TILE`)

How the server places a tile's walkmesh in an area and reads it: frames
and rotation, loading, walkable faces, adjacency, subdivision, point
lookup and heights. All addresses in this file are `nwserver-linux`.

The walkmesh file format itself (the `aabb` node, its faces and tree) is
nwn-mdl-spec's subject (`MDL-MESH-012`, `MDL-MESH-051`, `MDL-MESH-052`).
This file covers what the server does with a tile walkmesh once an area
uses it.

## Frames

**SET-TILE-001** A world point (x, y) is in tile
`((int)(x / 10), (int)(y / 10))`, truncated toward zero, so -0.5 is in
tile 0. Tiles are 10 m (`CNWArea::TILE_SIZE`, 0xb3a954); tile (0, 0) is
the south-west tile, x runs east and y north. *Confirmed: T11.*

**SET-TILE-002** A tile's walkmesh and its path-node layout are in the
tile's canonical frame. Every server function that takes a world or
tile-local point rotates it to canonical first, and rotates results back.
*Confirmed: T11, T16, T17, T33.*

**SET-TILE-003** With o the tile's placement orientation (the area's
`Tile_Orientation`, tile +0x24), tile-local real (x, y) and canonical
(cx, cy) relate as:

| o | real → canonical | canonical → real |
|---|---|---|
| 0 | (x, y) | (cx, cy) |
| 1 | (y, 10 - x) | (10 - cy, cx) |
| 2 | (10 - x, 10 - y) | (10 - cx, 10 - cy) |
| 3 | (10 - y, x) | (cy, 10 - cx) |

The constant is the literal 10.0 (0xb16048), not `TILE_SIZE`. A
simulator MUST treat an o outside 0-3 as 3 for real → canonical and as 1
for canonical → real. *Confirmed: T11 (`CNWTile::RotateRealToCanonical`
0x44bfc0, `RotateCanonicalToReal` 0x44bec0). No recorded route crosses a
rotated tile.*

**SET-TILE-004** The world-coordinate variants subtract the tile origin
`((float)tx * 10.0, (float)ty * 10.0)`, rotate, and add it back, in that
order. *Confirmed: T11 (`RotateRealToCanonicalTile` 0x44c030,
`RotateCanonicalToRealTile` 0x44bf30).*

## Loading a walkmesh

**SET-TILE-010** The walkmesh's `position px py pz` is applied as the
offset (px + 5.0, py + 5.0, pz). A writer MUST author a tile walkmesh
centred on the tile (x and y in -5..5 with `position 0 0 0`) so that it
lands in 0..10. *Confirmed: T6.*

**SET-TILE-011** The walkmesh's `orientation ax ay az angle` is applied as
a quaternion (axis normalised, half-angle `sincos(0.5 * angle)`, a zero
axis giving the identity) before the offset. *Confirmed: T6.*

**SET-TILE-012** Each vertex coordinate c is snapped after the transform:
`i = (int)trunc(512.0 * c + 0.5)`; if `(i & 0x1ff) == 0`, c becomes
`(float)(i >> 9)`. Only values within about 1/1024 of an integer change.
*Confirmed: T6.*

**SET-TILE-013** A vertex exactly equal (float `==` on x, y and z, after
snapping) to an earlier one is welded to it, and face indices are
remapped. Adjacency is by welded index (SET-TILE-030), so a writer MUST
write a shared vertex with identical coordinates on every face that uses
it, and SHOULD NOT leave T-junctions, if the faces are meant to connect.
*Confirmed: T6, T8.*

**SET-TILE-014** A face line is read as `v0 v1 v2 <four integers>
material`; the four integers (smoothing group and the file's adjacency)
are ignored. *Confirmed: T6.*

**SET-TILE-015** Each face's normal is `normalize(cross(v1 - v0, v2 - v1))`
with `cross(a, b) = (a.y*b.z - a.z*b.y, a.z*b.x - a.x*b.z, a.x*b.y -
a.y*b.x)`, and `normalize(v)` returns v when `s = (x*x + y*y) + z*z` is 1
or within [0.99998999, 1.00001001], (1, 0, 0) when s is 0, else
`v * sqrt(1 / s)`. The plane offset is `d = -((n.x*v0.x + n.y*v0.y) +
n.z*v0.z)`. *Confirmed: T6.*

**SET-TILE-016** The ASCII branch is the only one specified here. A
writer SHOULD write tile walkmeshes as ASCII. *Confirmed: T6 (every corpus
tile is ASCII); the binary branch was not read (unknown.md).*

## Walkable and non-walkable faces

**SET-TILE-020** A face is walkable when `surfacemat.2da`'s `Walk` for its
material is non-zero, else non-walkable. Walkable and non-walkable faces
are kept in separate lists, each with its own vertices renumbered from 0
in file order; faces keep their file order within each list. *Confirmed:
T7.*

**SET-TILE-021** Only walkable faces take part in adjacency, regions,
point lookup and the in-tile search. Non-walkable faces are only used to
block line tests (SET-INTRA-062). A creature can stand only on walkable
faces. *Confirmed: T7, T38.*

## Adjacency

**SET-TILE-030** Two walkable faces are neighbours when they share an
edge, compared as an unordered pair of welded vertex indices. *Confirmed:
T8.*

**SET-TILE-031** An edge whose two vertices lie on the same tile border
(both x <= 1e-4, both x >= 9.9999, both y <= 1e-4 or both y >= 9.9999) is
`TRIADJ_TILE_END` (-2): the route may leave the tile there. Any other edge
without a partner is `TRIADJ_NO_EDGE` (-3): a wall. *Confirmed: T8.*

**SET-TILE-032** For each edge of face i not yet set, every later face j
sharing it is linked to i, and i ends linked to the last such j. A
simulator MUST reproduce this for non-manifold edges. *Confirmed: T8.*

**SET-TILE-033** A writer SHOULD put a tile's border vertices exactly on
the border (0 or 10 after the offset, within 1e-4), or the border edge is a
wall to the search. *Confirmed: T8.*

## Subdivision and point lookup

**SET-TILE-040** The in-tile search runs on two subdivided levels built
from the walkable faces: each triangle (v0, v1, v2) splits at its edge
midpoints m01, m02, m12 (each computed as `(a + b) * 0.5`) into children
4i (v0, m01, m02), 4i+1 (m01, v1, m12), 4i+2 (m02, m01, m12, the centre)
and 4i+3 (m02, m12, v2). Midpoints are not shared between neighbours.
Children's adjacency is inherited from the parent's by the rule in
Landscaper `research/SPEC_INTRATILE.md` 1.4. A search node is a level-2
triangle id; its ancestor at level L is `id >> (4 - 2L)`. *Confirmed: T9.*

**SET-TILE-041** The triangle under a point is the first walkable
triangle, in index order, whose three edge tests are all >= 0:
`(A.y-B.y)*(x-A.x) + (y-A.y)*(B.x-A.x)`,
`(B.y-C.y)*(x-B.x) + (C.x-B.x)*(y-B.y)`,
`(A.x-C.x)*(y-C.y) + (C.y-A.y)*(x-C.x)`; none: -1. Edges are inclusive, so
a point on a shared edge belongs to the lower index. Descending levels from
a hint does not check the point is inside the hint. *Confirmed: T10.*

## Heights

**SET-TILE-050** Line tests add the tile's z offset (tile +0x10) to the
walkmesh heights they return, and subtract it before testing faces, so a
walkmesh's z is relative to its tile's base. *Confirmed: T12.* A writer
SHOULD write walkmesh z relative to `Tile_Height × Transition`: every
corpus area does, and it paths as recorded. *Confirmed: conformance
corpus.* That the server's tile z equals `Tile_Height × Transition` is
inferred (unknown.md).

## Shared edges between tiles

**SET-TILE-060** When a route crosses from one tile to the next, the
crossing point is chosen from the leaving tile's walkmesh only, and the
next tile's search starts there (SET-INTRA-050). A writer SHOULD make
neighbouring tiles agree on walkability at every point of their shared
edge: ground at a point of the edge walkable on one side if and only if it
is on the other. *Confirmed: T13 (corpus v1 cliff 4.0: every failure of
seeds 1-5 started at such a point; corpus v2 and v3, written with shared
border vertices and reconciled walkability: 198 of 200 and 80 of 80 cliff
routes arrived, the two misses predicted by the simulator).*

**SET-TILE-061** A simple way to meet SET-TILE-060 is to give both tiles
the same border vertices and make a border face walkable exactly when both
its border vertices are walkable ground. *Confirmed: corpus v2 and v3 were
generated so (Landscaper `src/rtin.rs` `full_border`, `src/seams.rs`).*
