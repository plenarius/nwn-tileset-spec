# What the engine does with tilesets and areas

Build 89.8193.37-17. Addresses are objdump addresses (Ghidra adds
0x100000). T1-T40, T56-T59 and T65-T66 are `nwserver-linux` unless marked;
T41-T55, T60-T64 and T67 are `nwmain-linux`. See [README.md](README.md) for the
conventions.

## The .set file (T1-T5)

**T1 Line ends.** The server crashes loading a `.set` written with LF line
ends; with CRLF it loads. *Confirmed (in game: Landscaper's first
generated tilesets).* The research notes place the fault in
`CResSET::CreateSectionTable` (0x43ee30), a buffer overflowed by LF-only
text; that function was not read for this repository, so the mechanism is
inferred. Source:
Landscaper `research/FINDINGS.md`, "Engine rules learned"; Landscaper
`src/main.rs` `crlf()`.

**T2 Tile orientation is in degrees.** A tile's `Orientation` goes through
`CNWTileSurfaceMesh::ConvertToTileOrientation(int)` (0x441770): 0, 360 and
-360 give 0; 90 and -270 give 1; 180 and -180 give 2; 270 and -90 give 3;
anything else gives 4. 4 is not a valid path-node orientation:
`CNWTileSetManager::GetTilePathNode` (0x3f6010) rejects `orient >= 4` and
returns NULL, and the pathfinder then crashes. *Confirmed (code; in game:
writing 1, 2 or 3 crashed pathing; Landscaper's generated tilesets write
0, 90, 180 and 270 and route, `src/main.rs` `set_file`).* That every
invalid value crashes, rather than only those tried, is inferred.

This `Orientation` is the **path-node** orientation of the tile's layout
(walkmesh +0x34). It is not the area's `Tile_Orientation`, which places
the tile (T11).

**T3 PathNode.** A tile's `PathNode` letter is stored in the walkmesh
object (`CNWTileSurfaceMesh::SetPathNode`, 0x441760, offset +0x32) beside
its converted orientation (+0x34). Every planner function gets its layout
from `GetTilePathNode(letter, orientation)` (0x3f6010), which caches the
result of `CNWTileSetManager::ComputePathNodeInformation` (0x3f3ea0) per
letter and orientation. *Confirmed (code; gdb). The store of +0x34 itself
was not traced: inferred from the value's use (spec/unknown.md).*

**T4 Corner and edge keys (client).** `CNWTileSet::LoadTileSet`
(`nwmain-linux` 0x5e1190) stores the corner keys with
`CNWTileData::SetCornerType` (0x632a40) and the edge keys with
`CNWTileData::SetEdgeType` (0x633030): `TopRight` corner 0, `BottomRight`
1, `BottomLeft` 2, `TopLeft` 3 (calls at 0x5e190e, 0x5e1aa9, 0x5e19a6,
0x5e1801); `Top` edge 0, `Right` 1, `Bottom` 2, `Left` 3 (0x5e1b74,
0x5e1dde, 0x5e1c42, 0x5e1d0f). Both run clockwise from north; corner i
follows edge i clockwise. *Confirmed (asm).*

**T5 The `+` marker (client).** `SetCornerType(corner, name, height)`
(`nwmain-linux` 0x632a40) stores `name + "+"` when `height != 0`, else
`name` (test at 0x632a69, concatenation 0x632bc8-0x632c05).
`LoadTileSet` passes `strtol` of the matching `<Corner>Height` key. Any
non-zero height gives exactly one `+`; there is no `++`.
`CNWTileData::GetCornerType` (0x632ee0) returns the stored string as it
is. *Confirmed (asm).*

## Tiles and walkmeshes (T6-T14)

**T6 Loading a tile walkmesh.** `CNWTileSurfaceMesh::LoadWalkMesh`
(0x441820), ASCII branch:
- `position px py pz` gives an offset (px + 5.0, py + 5.0, pz), so a
  walkmesh authored centred on the tile (-5..5) lands in 0..10. With no
  `position` line the offset stays (0, 0, 0) (T60);
- `orientation ax ay az angle` gives a quaternion (axis normalised,
  `sincos(0.5 * angle)`; a zero axis is the identity), applied to each
  vertex before the offset;
- each coordinate is snapped: `i = (int)trunc(512.0 * c + 0.5)`; if
  `i & 0x1ff == 0`, `c = (float)(i >> 9)`. Only values within about
  1/1024 of an integer move;
- a vertex equal (exact float `==` on x, y and z) to one already stored is
  welded to it; face indices are remapped;
- `faces` lines are read as `v0 v1 v2 <four ints ignored> material`. The
  file's adjacency columns are ignored;
- each face's normal is `normalize(cross(v1 - v0, v2 - v1))`, and its plane
  `d = -((n.x*v0.x + n.y*v0.y) + n.z*v0.z)`.

*Confirmed (code; simulator). The binary walkmesh branch was not read.*
Decompile: `nwserver-analysis/decompiled/pathfinding/clean/LoadWalkMesh.c`.

**T7 Walkable and non-walkable faces.** Each face's material is looked up
in `surfacemat.2da`'s `Walk` column (`C2DA::GetINTEntry`). Faces with
`Walk == 0` go to the non-walkable list (offsets +0xf8 count, +0x100
indices), the others to the walkable list (+0x5c count, +0x70 indices).
Each class has its own vertex list, renumbered from 0 in file order, and
faces keep their relative order inside a class. Only the walkable faces
take part in adjacency, regions, point lookup and the in-tile search; the
non-walkable faces are only used by line tests (T38). *Confirmed (code;
simulator).*

**T8 Adjacency.** `CNWTileSurfaceMesh::ComputeTriangleAdjacency`
(0x440510) works on the walkable faces. Two faces are neighbours when they
share an edge by **welded vertex index** (as an unordered pair), so a
T-junction breaks adjacency. An edge whose two vertices both lie on the
same tile border (x or y within 1e-4 of 0, or at least 9.9999) is marked
`TRIADJ_TILE_END` (-2). An edge with no partner stays `TRIADJ_NO_EDGE`
(-3). The inner loop has no `break`: when an edge is shared by more than
two faces, the first face gets the last partner, and every partner points
back to the first. `TRIADJ_UNKNOWN` (-1) is never produced. *Confirmed
(asm).*

**T9 Subdivision.** On the first in-tile search, `Subdivide` (0x449460)
builds two finer levels with `RunSubdivision` (0x449070). Each triangle
splits into four (corner at v0, corner at v1, centre, corner at v2) at its
edge midpoints. Midpoints are not shared between neighbours; the children's
adjacency comes from the parent's by a fixed rule. A level-2 id identifies a
search node; its ancestor at level L is `id >> (4 - 2L)`. *Confirmed
(code; simulator).* The full rule: Landscaper `research/SPEC_INTRATILE.md`
1.4.

**T10 Point lookup.** `CNWTileSurfaceMesh::FindTriangle` (0x444140) scans
the walkable triangles of a level in index order and returns the first
whose three edge tests are all `>= 0` (edges inclusive, so a point on a
shared edge goes to the lower index), else -1. Given a hint (a triangle one
level up), it descends into the hint's children without checking the point
is inside the hint. *Confirmed (code; simulator).*

**T11 Frames and rotation.** A world point (x east, y north, metres) is in
tile `((int)(x / 10), (int)(y / 10))`, truncated (`cvttss2si`, so -0.5 maps
to tile 0). The walkmesh and the path-node table are in the tile's
**canonical** frame; `CNWTile::RotateRealToCanonical` (0x44bfc0) and
`RotateCanonicalToReal` (0x44bec0) map between it and the tile-local
placed frame by the tile's placement orientation (tile +0x24), about
(5, 5), with the literal 10.0 at 0xb16048:

| o | real → canonical | canonical → real |
|---|---|---|
| 0 | (x, y) | (x, y) |
| 1 | (y, 10 - x) | (10 - y, x) |
| 2 | (10 - x, 10 - y) | (10 - x, 10 - y) |
| 3 | (10 - y, x) | (y, 10 - x) |

An o outside 0-3 behaves as 3 real → canonical and as 1 canonical → real.
The `…Tile` variants (0x44c030, 0x44bf30) subtract the tile origin
`((float)tx * 10, (float)ty * 10)`, rotate, and add it back. *Confirmed
(code). No recorded route crosses a rotated tile (every corpus tile has
o = 0).*

**T12 Tile height in line tests.** `CNWSTile::ClippedLineSegmentWalkable`
(0x68c9c0) adds the tile's z offset (tile +0x10, a float) to the heights it
returns from the walkmesh, and `CNWSTile::NoNonWalkPolysOnTile` (0x68d5e0)
subtracts it before testing. So walkmesh z is relative to the tile's base,
and the server compares heights between tiles in world z. *Confirmed
(code).* That tile +0x10 holds `Tile_Height × Transition` is inferred (the
simulator sets it so and agrees with the server; the store was not read).

**T13 A crossing is chosen from one side.** When a route leaves a tile,
the crossing point on the edge is chosen from the current tile's walkmesh
only (T37); the next tile's search then starts at that point. If the point
is walkable on the leaving side but not on the entering side, the entering
tile's search fails at once (start off its walkmesh), and the crossing is
denied for the rest of the request (T28). *Confirmed (server and simulator:
all 50 failures of the cliff-4.0 seeds 1-5 corpus, `conformance/routes/v1`;
Landscaper `research/FINDINGS.md`, "Why the cliff-4.0 routes fail").* In
that corpus the ramp's walkable band across the x = 20 seam was y 5..7.75
on one side and y 5..10 on the other, because each side's faces also used
its own interior samples.

**T14 Walkmeshes need not be BioWare-sized.** Generated tiles of about 320
faces (17 × 17-sample walkmeshes) completed their in-tile searches in one
planner call when their regions were simple (Landscaper
`research/FINDINGS.md`, "Cliff band and time budget"; corpus v3, cliff
cases, 80/80 arrived). For comparison, the stock tilesets' walkmeshes have
a median of about 45 faces a tile, p90 about 78, maximum about 250
(`landscaper wok-stats`, FINDINGS). *Confirmed (server arrival; the call
counts are the simulator's).* Landscaper's first, denser walkmeshes (before
RTIN simplification) left searches "in progress" until the call cap, and
the creature walked the partial straight line (FINDINGS, "How the engine
paths"). What does cost time is the shape of a region, not its face
count (T39).

## Path-node layouts (T15-T20)

**T15 The layout table.** The engine has a built-in table of path-node
layouts. `ComputePathNodeInformation(letter, orientation)` (0x3f3ea0)
returns a layout's node positions, exit points and each exit's owning
node, rotated by `CNWTileSetManager::ComputePathNodeRotation` (0x3f3df0).
The table is authored centred on (0, 0) in -5..5, and each point (x, y)
becomes (x + 5, y + 5) for orientation 0, (5 - y, 5 + x) for 1,
(5 - x, 5 - y) for 2 and (5 + y, 5 - x) for 3: the same anticlockwise
sense as `RotateCanonicalToReal`. An orientation above 3 would write
uninitialised registers; `GetTilePathNode` rejects it first. *Confirmed
(asm; gdb dump of every letter `A`-`Z`, `a`-`x` and orientation 0-3,
[tables/pathnodes.json](../tables/pathnodes.json); all four orientations of
all 48 letters follow the rotation exactly).*

Facts of the dump:
- 48 letters have layouts: `A`-`Z` except `P` and `T`, and `a`-`x`. For
  `P` and `T` the function returned 0 nodes and 0 exits.
- Layouts have 1 to 8 nodes (`r` has 8, `s` 7, `n` and `v` 6) and 1 to 12
  exits. Every node owns at least one exit.
- Every exit lies on the tile edge, at one of 20 points: 1, 2.5, 5, 7.5
  and 9 m along each side.

**T16 Regions.** A tile's region is a node index. `CNWSTile::FindClosestRegion`
(0x68cf10) returns 0 if the tile has no walkmesh, else rotates the point to
canonical and calls `CNWTileSurfaceMesh::FindClosestRegion` (0x444870):
- one node: region 0;
- otherwise it finds the level-0 walkable triangle under each node
  position (may be -1) and under the point. If the point is on no walkable
  triangle, the region is **0** (not the nearest node);
- from the point's triangle, `FindRegionViaTriangle` (0x443f70) searches
  depth-first over adjacency, checking at each triangle (before marking it
  seen) whether it is a node's triangle, nodes in index order, and
  following neighbours `a0, a1, a2` with index >= 0. The first node
  triangle reached wins;
- if none is reached, the node nearest by squared distance (strict `<`,
  ties to the lower index).

So when several nodes lie in one connected walkable component, the region
depends on adjacency order, not on distance. *Confirmed (asm; simulator).*

**T17 Region entrance.** `CNWTileSurfaceMesh::GetRegionEntrance(cx, cy)`
(0x440cb0) returns the owning node of the first exit within 1e-4
(`CNWArea::EPSILON`, 0xb3a948) on both axes of the point, else -1.
`CNWSTile::GetRegionEntrance` (0x68d120) rotates the point to canonical
first. The tile route enters a neighbour only through this call (T27), so
two tiles connect only where the neighbour's layout has an exit at the same
point, after both tiles' rotations. *Confirmed (asm; simulator).*

**T18 Exit number.** `CNWTileSurfaceMesh::GetExitNumber(cx, cy)`
(0x440a50) returns the first exit j whose span contains the point: for an
exit on a north or south edge, x within `min(ex, 10 - ex)` of the exit and
y within 1e-4; for an exit on an east or west edge, the same with axes
swapped. An exit at a corner gets both spans. No match gives 12
(`CNWTile::UNKNOWN_TILE_EXIT`, 0xb3a814). *Confirmed (asm).*

**T19 Nodes sharing a component.** A layout whose nodes do not each sit
in their own walkable component makes FindClosestRegion (T16) answer by
adjacency order. Landscaper's first generated tiles with such layouts
crashed the server in `CNWTileSurfaceMesh::FindClosestRegion`. *The crash
is confirmed (in game, `research/FINDINGS.md`); what in the function
crashes was not found in the code read (spec/unknown.md).*

**T20 Six regions a tile.** The tile route's visited table
(`CNWSArea` +0x260) has `MAX_X_TILES × MAX_Y_TILES × 6` bytes (32 × 32 × 6;
`CNWSArea::MAX_X_TILES` 0xb4c354 and `MAX_Y_TILES` 0xb4c350 are 32), indexed
`region + (32 * tx + ty) * 6`. *Confirmed (code).* Layouts `r` (8 nodes)
and `s` (7 nodes) exceed 6, so their regions 6 and 7 would share bytes with
regions 0 and 1 of tile (tx, ty + 1). *Inferred; untested.*

## The move request and the tile route (T21-T32)

**T21 The request.** `CNWSModule::PlotPathInArea` (0x54cc00) handles one
call of a move request:
1. On the request's first call it runs `CNWSArea::TestDirectLine` (T22)
   from start to goal, with the creature's radius and height, and keeps
   the result for later calls. Result 1: the path is the straight line,
   complete. -4: failed.
2. -1 or -2: it runs `CNWSArea::PlotPath` (T24). -3: it runs
   `CNWSArea::PlotGridPath` (T30). Anything else: the fallback.
3. If PlotPath fails while calls remain and the goal is within 20 m
   (squared distance < 400.0, 0xb3d2f0), the next calls run PlotGridPath.
4. If the call count passes the cap with the plan still in progress, or
   the plan failed otherwise, the fallback: unless `pf+0x00` is set, a
   6-step bisection along start → goal finds the farthest point P reachable
   by a straight line, each test from the last point found (start at
   first), t = 0.5, step 0.25, halving. Waypoints [start, P], complete; no
   point found: failed.
A goal range (`pf+0x58` > 0) pulls the direct-line target back to that
distance from the goal. *Confirmed (asm; simulator).*

**T22 TestDirectLine.** `CNWSArea::TestDirectLine` (0x646920) walks the
segment tile by tile. In each tile it runs the tile's clipped line walk
(T38) and `NoNonWalkPolysOnTile` with the creature's radius, z range
`[zmin - 0.1, zmax + 0.1 + height]`; either failing returns -1. A tile
outside the area returns 0. Past the end, if the radius reaches into
another tile, that bit must be walkable too (-1). Then placeable and door
walkmeshes (`NoNonWalkPolysDetailed`): -2. Then creatures
(`NoCreaturesOnLine`, 0x6447a0): -3. Clear: 1. `CNWSArea::TestLineWalkable`
(0x6452b0) is the same tile walk without the width test. *Confirmed (asm;
simulator, with no placeables, doors or other solid creatures).*

**T23 Time and call budgets.** An NPC's move calls `CNWSModule::PlotPath`
(0x54e120) with `CNWSObject::AI_TIME_SLICE` (0xb42034) = 1000 µs as each call's
budget (from `CNWSCreature::AIActionMoveToPoint`). After 100 calls a plan still in progress becomes the fallback
(T21). For a player-controlled creature the cap and budget come from a
module setting (module +0x45c): 0 → 100 calls of 1000 µs, 1 → 10 of 7000,
2 → 5 of 12000, 3 → 1 of 50000. *NPC values confirmed (code; gdb: budget
1000 µs). PC values read in code, not exercised.*

**T24 PlotPath.** `CNWSArea::PlotPath` (0x649b70), per call:
- start and goal tiles by truncation; start region and goal region by
  FindClosestRegion (T16); either tile missing: failed;
- if no route is stored, `GenerateInterTilePath` (T25) builds one: a list
  of tiles and, for each tile but the last, the exit point where the route
  leaves it, in that tile's real local frame;
- then, while the budget lasts, it runs the in-tile search
  (`CNWSTile::PlotIntraTilePath`, T33) on the route's first tile. On
  success the next tile starts at the last point found, with the
  coordinate across the crossed edge snapped to 0 or 10 (both, if the step
  changes x and y). On failure, see T28. When the last tile completes, the
  raw points are smoothed (T29) and the plan is complete.
- A call that runs out of time returns "in progress"; the route, denials
  and points carry over to the next call. The intra search's own state
  carries over too (T34).
The start position argument passed to the in-tile search is the original
start relative to the previous tile's origin, lagging one tile; the mesh
code never reads it. *Confirmed (asm; simulator).*

**T25 Iterative deepening.** `CNWSArea::GenerateInterTilePath` (0x644520)
runs `InterTileDFS` with a growing budget. With `m` = the Manhattan
distance in tiles between start and goal tile, the first call tries
budgets m, m + 2, …, m + 22 (12 rounds; the limit is `m + 23`, the literal
0x17). After a denial the bound is first lowered by 2 from the last
budget that worked, so the replan restarts there, not at m. The visited
table persists across rounds of one call. *Confirmed (asm).*

**T26 The tile DFS.** `CNWSArea::InterTileDFS` (0x644340) at depth d with
budget b on state (tile x, tile y, region r): records the tile; unless at
depth 0 with b >= 3, returns the goal test (state equals the goal state:
success unless `GoalMoveDenied`, T28) and fails if b < 1; fails if the
Manhattan distance to the goal tile exceeds b; fails if the visited byte
for the state is already >= b, else stores b; then tries the successors
(T27) in order with budget b - 1. *Confirmed (asm).*

**T27 Successors and their order.** `CNWSArea::InterTileDFSGenerateSuccessors`
(0x6431a0), for state (x, y, r):
- exits of the tile's layout owned by node r and not blocked by a denial
  (T28), at most 8 (`MAX_INTER_TILE_SUCCESSORS`, 0xb3a958; the 9th stops
  the loop);
- the neighbour is across the edge the exit lies on (x beyond 9.9999 →
  east, below 1e-4 → west, the same for y); the entry point is the exit
  point with that coordinate wrapped (10 → 0, 0 → 10). The neighbour must
  be in the area and `GetRegionEntrance` (T17) of the entry point must
  give a region;
- score: 1.0 if the segment from the current region's node (world) to the
  goal point crosses a span along the edge centred on the exit and reaching
  to the nearer tile corner (less 1e-4), tested by
  `CNWArea::IntersectLineSegments` (T32); else the larger cosine between
  node → goal and node → either end of the span. Exits not on an edge score
  0;
- sorted by score, descending, stable (equal scores keep exit order).
The stored exit point is in the current tile's frame. All arithmetic is
single precision. *Confirmed (asm; Ghidra mislabels several locals here,
the asm was followed); simulator.*

**T28 Denials.** When an in-tile search fails on route tile T, PlotPath
records a denial (T, a, b) with `CNWSArea::RemoveInterTileExit`
(0x645130): a is the exit number (T18) of the point where the search
started on T (12 if it is not on an exit, as on the start tile), b the
exit number of the point where the route left T (12 on the goal tile). It
then clears the points, lowers the bound by 2 (T25), and plans a new route
from the original start. Denials accumulate for the whole request; only a
route search that fails ends it. In the successor step at depth 0, a
denial on the tile blocks exit b; deeper, it blocks b only when the
current entry point matches exit a's point (within 1e-4), and a denial
with b = 12 that matches stops the state from having any successor.
`CNWSArea::GoalMoveDenied` (0x643060) refuses the goal state when the
goal tile has a denial (a, 12) for the exit the route entered by.
*Confirmed (asm; simulator).*

**T29 Smoothing.** On completion `CNWSArea::SmoothPointsOnPath` (0x6481e0)
turns the raw points into waypoints, unless `pf+0x14` is set (then they
are copied). `SmoothSelection` (0x648120) runs `SmoothSelectNodes`
(0x647c30) three times: (subdivide = r9, uninitialised; shortcut off),
(subdivide on, shortcut on), (subdivide off, shortcut on). The shortcut
pass keeps the farthest later point reachable by `TestDirectLine`;
subdivision splits legs of 1.1 m or more into 1 m steps.
`SmoothCornerOptimize` (0x6477e0) with `ComputeBestCorner` (0x647470) then
cuts corners whose cosine is below 0.9 (`CNWArea::SPLINE_COSINE_LIMIT`,
0xb3a944) by bisection, stopping below 0.1 m. *Confirmed (asm), except the
first pass's subdivide flag, which is uninitialised (spec/unknown.md).
Smoothing changes the waypoints, not whether the creature arrives.*

**T30 Grid path.** `CNWSArea::PlotGridPath` (0x648eb0) with
`GridSearchPath` (0x648820) is a best-first walk on a grid aligned with the
goal → start direction, step 0.1 m for radii in (0.1, 0.65], else
max(0.1, radius); up to 32 paths, each step a `TestDirectLine`. It ends
at the goal, with no path left to extend, or after a call that brought no
new best; the best path then becomes the waypoints. Used after PlotPath
fails within 20 m (T21) and when the first direct test returned -3.
*Confirmed (asm, the direction switch through the jump table at 0xb4c580;
simulator). Where it ends depends on its time slices: one corpus route
ended 3 m from the server's end point, with the same arrival.*

**T31 Where a created creature stands.** `CreateObject` places a creature
with `CNWSArea::ComputeSafeLocation` (0x645b60), search range 20 m. A
point is safe if `CNWSArea::TestSafeLocationPoint` (0x641130) passes: the
horizontal segment (x - radius, y)..(x + radius, y) walkable tile by tile
and clear of non-walkable faces at full width (no 0.1 m clamp), then no
placeables or creatures. Otherwise square rings of step
`min(radius, range / 10)` are searched and the first safe point with a
walkable line back wins. A start within about 0.4 m of non-walkable ground
moves. *Confirmed (code; two corpus starts were moved by the server, and
the simulator moves them the same way).*

**T32 Segment intersection.** `CNWArea::IntersectLineSegments`
(0x44e2e0) intersects two segments by slopes, with special cases for
vertical segments, inclusive range tests (`ucomiss`, so NaN fails), and
no y-range test in the general case. *Confirmed (asm).* The exact
expressions: Landscaper `research/SPEC_INTERTILE.md` 5.4.

## The in-tile search (T33-T40)

**T33 The tile wrapper and coarse mode.** `CNWSTile::PlotIntraTilePath`
(0x68d730) returns failed if the tile has no walkmesh. It rotates the
start, the goal (on the last route tile) or every remaining route exit to
canonical, calls the mesh search, rotates them back (a float round trip
that can change a value by one ulp), and rotates the new points to world.
It passes a **coarse** flag: 1 when the tile's centre is more than 15 m
from the request's start (squared distance > 225.0, 0xb4f7ec), the
creature's +0x894 is 0, and the creature is not a possessed familiar.
*Confirmed (asm 0x68d8cf-0x68dabe; Ghidra's signature for this call drops
the flag; gdb: the flag was 1 on 215 of 732 calls of a scripted NPC move;
simulator).* That creature +0x894 means "is a player character" is
inferred.

**T34 The search driver.** `CNWTileSurfaceMesh::PlotIntraTilePath`
(0x4496d0) is an IDA* over level-2 triangle nodes:
- the target is a goal box: on the last route tile the goal point ±1e-4;
  on other tiles the box from `GenerateBestIntraTileExit` (T37);
- the start must be on a walkable triangle, else failed;
- the first bound is the distance from the start to the box plus 10.0;
  each round adds 5.0 (`CNWTile::INTRATILE_ESTIMATE_INCREMENT`, 0xb3a808);
  a round that finds nothing with the bound now above 40.0 (`TILE_SIZE ×
  4`, double 4.0 at 0xb3a7a0) gives up: failed. The first bound is always
  tried;
- work is counted in units: 12 per node expansion
  (`TIMEUNIT_NODE_EXPANSION`, 0xb3a810), 300 per successor generation
  (`TIMEUNIT_NODE_ALTERNATIVE_GENERATION`, 0xb3a80c). The unit budget is
  the remaining microseconds of the PlotPath call, at least 500. Out of
  budget, the search suspends (its stack, bound and transposition table
  saved in the request) and resumes on the next call.
*Confirmed (asm; simulator).* Units are compared with a wall-clock
budget, so where a search suspends is not deterministic.

**T35 The node expansion.** `CNWTileSurfaceMesh::IntraTileDFS`
(0x448ae0): goal test (inside the box, inclusive; or within the goal range
when one is set and the box is narrow); `f = g + distance to box`, fail if
`f >= bound`; a 128-entry, two-slot transposition table
(`CNWTileSurfaceMeshHashTableEntry`, bucket `((id >> 8) + id) & 127`)
prunes a node whose stored value is at least `bound - g`, and stores
`bound - g - 1e-4`; then the successors in order. The first path found
inside the bound is returned, not the shortest. *Confirmed (asm;
simulator).*

**T36 Successors.** `CNWTileSurfaceMesh::IntraTileDFSGenerateSuccessors`
(0x447b90):
- level 0 first: a straight walkable line (T38) to the goal point makes it
  the only successor; else, if the goal is on the walkmesh, a walkable line
  to a corner of the goal box;
- then for levels 0, 1 and 2 (only 0 in coarse mode), the edges of the
  node's ancestor triangle at that level not yet used, each a successor
  through its midpoint: across a `TILE_END` edge only if the midpoint is in
  the goal box; across an inner edge to the neighbour's centre (or the
  goal point, stepping into the goal's triangle); `NO_EDGE` edges never;
- outside coarse mode each leg must pass the line tests (T38); in coarse
  mode no line tests are made on edges;
- ordered by level, then by cost (true 2D length) plus distance to the
  box, stable.
*Confirmed (asm; simulator).* The full rule, with the "edge already used"
table: Landscaper `research/SPEC_INTRATILE.md` 5.3.

**T37 Choosing the crossing.** On a tile that is not the route's last,
`CNWTileSurfaceMesh::GenerateBestIntraTileExit` (0x446800) chooses where
on the exit edge to aim. It counts the layout's exits on that edge (n) and
the exit's place among them (k), and from
[tables/exit_candidates.yaml](../tables/exit_candidates.yaml) takes five
candidates along the edge: the exit ± inner, ± outer. Each candidate gets a
weight: 3, or 1 to 5 across the five favouring the side the route turns to
two tiles ahead, plus 1 for the candidate whose bin holds the start
coordinate. A candidate reachable by a clear straight line from the start
(on this tile's walkmesh, then placeables, doors and creatures) scores
`weight × 6 × R × 7` (R = max(0.1, radius)); otherwise free space is
probed inward from it in steps of R up to 6.1 R, scoring `weight × d × 0.5`
when blocked after at least R, `weight × 6 × R` when never blocked; a
candidate blocked at the first probe is rejected. The best score wins
(strict `>`, ties to the earlier candidate). The goal box is then the
candidate ± the table's `fin` along the edge and ± 1e-4 across it. No
candidate: failed. *Confirmed (asm; simulator).* Only the current tile's
walkmesh is consulted (T13).

**T38 Line tests.** In-tile line tests are
`CNWTileSurfaceMesh::TestLineForWalkableOnTile` (0x446620) then
`TestLineForWalkableOnArea` (0x441170):
- `ClippedLineSegmentWalkable` (0x445300) clips the segment to the tile
  (`ComputeClippedLineSegment`, 0x443810) and walks the walkable triangles
  from the clipped start toward the end, crossing edges with
  `CNWTileSurfaceMesh::IntersectLineSegments` (0x444e20), up to 512 steps.
  It passes when it reaches the triangle holding the end, or leaves the
  tile through a `TILE_END` edge; a `NO_EDGE` edge, a start off the
  walkmesh or 512 steps fail. It also returns the z range seen;
- with "check end" set, the clipped end must equal the requested end
  (squared distance <= 1e-10): the end must be in the tile;
- `NoNonWalkPolysOnTile` (0x445bf0) tests a rectangle swept along the
  segment (half-width w, extended past the end by w) against the
  non-walkable faces within the z range. **With flag 0 and
  0.1 < w <= 0.65, w becomes 0.1**: every in-tile test of a creature of
  radius up to 0.65 m uses a 0.1 m half-width corridor;
- `TestLineForWalkableOnArea` adds placeables and doors
  (`CNWArea::NoNonWalkPolys`) and creatures.
*Confirmed (asm for NoNonWalkPolysOnTile; code for the clipping and the
mesh intersection, transcribed from the decompile; simulator).*

**T39 Region shapes the search cannot cross.** The bound grows by 5 m a
round from about the straight-line distance, and each round re-explores
every path inside it (T34, T35). A walkable region in which getting from
one point to another means a long detour inside one tile costs very many
expansions. Observed:
- U-shaped regions on terraced noise terrain (the rugged variant): the
  most expensive in-tile crossings run to hundreds of thousands of units,
  and some routes run out of the 100 calls. On the server 72 of the 78
  reachable rugged routes arrived (corpus v3 `rugged-seed33` and
  `rugged-seed34`), and the simulator agreed on all 80, failures included.
  Each such crossing turned out to be the only connection between its
  parts, so no cut could remove it;
- a one-sample walkable ledge across a cliff sent the search exploring for
  millions of steps (simulator only; Landscaper `src/main.rs`, the
  morphological opening);
- a walkable slope in a ring round a blocked crest (a cave entrance's rock
  mound) lost the search; routes to the cave failed;
- a narrow dead-end recess split across tile edges and corners cost
  millions of steps; routes to its end failed;
- a goal box in a walkable component the start is not connected to (T13,
  T37) makes the search exhaust every bound before it fails: up to 2.6
  million units, 80,000 line tests and 55 of the 100 calls (corpus v1,
  cliff 4.0, westbound routes).
*Confirmed as observations: simulator and server (Landscaper
`research/FINDINGS.md`, "Why the cliff-4.0 routes fail" and "Cliff band
and time budget"; landscaper-web `js/entrance.js` and commit 5ff2631:
after the cave entrance was made one compact obstacle inside one tile, 8
of 8 server routes reached its door).* That the cost comes from the IDA*
re-exploring detours is inferred from the code; which shapes are safe in
general is not known (spec/unknown.md).

**T40 A recess needs open ground in its tile.** A recess (a cave mouth
notch) alone in a tile, with only the slope above it, was not reachable
from afar: routes found no way in. With the notch and 3 m of open ground in
front of it in the same tile, the notch is part of that ground's region and
routes reach it like any other recess. *Confirmed as an observation:
simulator and server (landscaper-web `js/entrance.js` `fitInTile`, commit
5ff2631, 8 of 8 routes). Why is not known (spec/unknown.md).*

## Edge tiles (T41-T50, `nwmain-linux`)

Source: Landscaper `research/SPEC_EDGE.md` revision 2; decompiles in
`nwmain-analysis/decompiled/edge-tiles/` (`LoadBorder.c`,
`ReloadBorder.c`, `TileSetGetEdgeType.c`, `TileDataGetEdgeType.c`,
`TileDataSetEdgeType.c`).

**T41 The 2da.** `CNWCArea::LoadBorder` (0x70a5c0) loads the 2da
`<tileset resref>_Edge` (built at 0x70a76b-0x70a7c2). If it does not
load, no border is drawn at all (0x70a7cc → 0x70bac0). *Confirmed (asm).*

**T42 Index rotation.** `CNWTileSet::GetEdgeType(tile, side, orient)`
(0x5e1040) and `GetCornerType(tile, corner, orient)` (0x5e0fe0) read the
tile's data at index `(side_or_corner + orient) & 3`. World sides are
numbered as data sides: 0 north, 1 east, 2 south, 3 west; corners 0 NE,
1 SE, 2 SW, 3 NW. *Confirmed (asm; the v2 decompile garbles these
parameters).*

**T43 Cells.** Four loops place one model per 10 × 10 m cell, 5 cells deep
on every side. West: x = -5..-1, y = -5..H+4, keyed by tile
(0, clamp(y, 0, H-1)). East: x = W..W+4, same y, tile (W-1, clamp(y)).
South: x = 0..W-1, y = -5..-1, tile (x, 0). North: x = 0..W-1,
y = H..H+4, tile (x, H-1). The west and east loops fill the 5 × 5 corner
blocks. The key depends only on the boundary tile, never on the depth, so
one model repeats 5 deep, and all 25 cells of a corner block share one.
There are 10W + 10H + 100 cells. *Confirmed (asm).*

**T44 Keys.** Each cell's key is (C1, E, C2):

| Position | C1 | E | C2 |
|---|---|---|---|
| west strip | NW corner of the tile | west edge | SW corner |
| SW block | "" | "" | SW corner of (0, 0) |
| NW block | NW corner of (0, H-1) | "" | "" |
| east strip | NE corner | east edge | SE corner |
| SE block | SE corner of (W-1, 0) | "" | "" |
| NE block | "" | "" | NE corner of (W-1, H-1) |
| south strip | SW corner of (x, 0) | south edge | SE corner |
| north strip | NW corner of (x, H-1) | north edge | NE corner |

*Confirmed (asm; the edge side arguments are `ecx` immediates, not visible
in the decompile).*

**T45 Row matching.** Rows are scanned in file order. A row matches when
its `Edge` equals E, and either (`Corner1`, `Corner2`) = (C1, C2)
("direct") or (C2, C1) ("swapped"); direct is tried before swapped for the
same row, and the first matching row wins. Strings are compared whole,
after `CExoString::LowerCase` on both sides (lengths equal, then
`strcmp`). `C2DA::Load2DArray` (0x546160) stores `****` as an empty
string, so `****` matches only an empty key part. *Confirmed (asm;
`****` at 0x546f3f-0x546f6d, 0x5474a2-0x5474b8).*

**T46 Rotation.** On a direct match the rotation is 0 on the west and east
strips and 1 on the south and north strips; on a swapped match 2 and 3.
On a miss the model is empty, `Height` is 0, and `Scene::SpawnTile` is
still called with `""`; the rotation byte is never initialised or reset in
`LoadBorder`, so it keeps the last match's value (garbage on the very
first cell). With a row
`T **** ****`, the NW and SE blocks match direct (0), the SW and NE blocks
swapped (2). *Confirmed (asm: the eight writes at 0x70bea6, 0x70c3bc,
0x70c608, 0x70c808, 0x70cb66, 0x70cc12, 0x70cefd, 0x70d10f).* That an
empty model draws nothing is shown in game (T61).

**T47 The rotation is a tile orientation.** `Scene::SpawnTile(model, &pos,
rotation, 1, NULL)` (0x474470, `Scene` vtable slot +0x38) builds the yaw
`rotation × 90°` with `YawPitchRoll` (0x5b6690) when no quaternion is
given. `CNWCTile::LoadModel` (0x80e040) calls the same slot with
`Tile_Orientation` in the same argument (0x80e0fc-0x80e10f), and 0 where
the border passes 1. So an edge rotation r turns its model exactly as
`Tile_Orientation = r` turns an area tile. *Confirmed (asm).* The 4th argument
(stored at TileData +0x54) strips the model to its meshes (T53).

**T48 Placement.** Each cell's model goes to
`(x × 10 + 5, y × 10 + 5, Transition × (Tile_Height + Height))`: 5.0
(0x12ee9e8) is the cell centre, 10.0 is `CNWTile::TILE_WIDTH`/`TILE_LENGTH`
(0x1311850, 0x131184c), `Tile_Height` is the boundary tile's (the area
corner tile's for a corner block), `Height` is the matched row's, added as
an integer before conversion, and Transition is
`CNWTileSet::GetHeightTransition` (tileset +0x44). *Confirmed (asm).*

**T49 Gate.** `LoadBorder` checks no flag itself. Its caller
`CNWCArea::LoadArea` (0x70e010) calls it only when the first client option
is non-zero and area +0x10c is 0 (0x70fa04-0x70fa19, call at 0x711187).
`CNWCArea::ReloadBorder` (0x711ff0) tests the same, deletes each cell's
previous model with `Scene::DeleteTile` (0x4636a0) and spawns again.
*Gate confirmed (asm); ReloadBorder read in the v2 decompile only.* That
the option is the "edge tiles" graphics setting, and +0x10c the server's
per-area "tile border disabled" flag, is inferred.

**T50 Edge models need no walkmesh.** `LoadBorder` reads no walkmesh and
`Scene::SpawnTile` gets only a model name. *Confirmed (asm: LoadBorder's
calls).* Landscaper's exports (from commit d720ec1) ship edge models as
`.mdl` only, with no `.wok`, and areas with them load in the client without
error, and the border is drawn from them (in game: T62). The server knows
nothing of border cells: inferred (`LoadBorder` is client code,
`CNWCArea`).

## Drawing tiles and edge tiles (T51-T55, `nwmain-linux`)

Decompiles in `nwmain-analysis/decompiled/edge-tiles/draw/` (v2 analysis);
every finding marked asm was checked against `objdump -d`.

**T51 The scene's BSP.** `CNWCArea::LoadArea` (0x70e010) calls
`Scene::InitBSP` (0x46c330, `Scene` vtable slot +0x30) with the area's
width and height, 5, 1 and 10.0 (call at 0x70e7da: `esi` = area +0xc,
`edx` = area +0x10, `ecx` = 5, `r8d` = 1, `xmm0` from 0x12eee2c =
`0x41200000`). *Confirmed (asm).* `InitBSP` builds the root box from
(-5 × 10, -5 × 10) to ((W + 5) × 10, (H + 5) × 10) metres and sets the
global `cellsize` to 10. *Read in the v2 decompile only.* So the BSP
covers the area and its 5-cell border ring (T43). Each cell has one
`TileData`, found by position (`SceneBSPGetTileData`, 0x47b480);
`Scene::SpawnTile` creates it when missing and links it with the cells
one cell away in x and in y. *Decompile only.*

**T52 Meshes are culled by their own box.** `SceneBSPAddPart` (0x47ca10)
files a `PartTriMesh` with `BSPFitBox(root, part +0x64, part +0x70)`
(0x5b2620): the node that holds the mesh's whole box. *Decompile only.*
Each frame `ManageSceneBSP` (0x47fa80) walks the BSP against the camera's
planes (`BSPTraverseVolumeApprox`, 0x5b2cf0), and `ProcessTriMeshParts`
(0x480d40) drops a mesh only when `PartOutside(PartTriMesh*, List<Plane>&)`
(0x47a130) finds its box (+0x64 min, +0x70 max) wholly above one plane
(`BoxAbovePlane`, call at 0x47a189; calls from 0x480da3, 0x480e53,
0x480f56). `ProcessStaticParts` (0x470970) computes the box with
`ComputePartBBox` (0x461370, call at 0x470a1f) when the tile is spawned.
*Confirmed (asm).* So a tile mesh that reaches outside the tile's 10 m
cell is kept while its box meets the view, whatever its cell does. It is
then drawn as authored (in game: T60). A box that leaves
the BSP root falls into a border node whose region test is approximate;
whether such a mesh is culled early is inferred (spec/unknown.md).

**T53 The 4th argument of `Scene::SpawnTile` keeps only meshes.**
`SpawnTile` keeps the argument in `r13d` (0x474485) and passes it to
`ProcessStaticParts` as its 5th (0x474573, call at 0x47457f).
`ProcessStaticParts` keeps it at -0x54(%rbp) (0x470996). For a part that
is not a `PartTriMesh`, when the argument is non-zero, it removes the part
from the list and deletes it (test at 0x470abc-0x470ac1, removal and
virtual delete at 0x470ae0-0x470af1). With 0, an emitter (0x470ac3), a part
`ProcessTilePart` (0x461720) took (0x470ac8) and a light (0x470ad4) stay.
`LoadBorder` passes 1 and `CNWCTile::LoadModel` 0 (T47). *Confirmed
(asm).* So an edge model draws its meshes only: its lights, emitters and
other non-mesh nodes are thrown away.

**T54 Tile lights.** `Scene::SetTileLights` (0x45edf0, vtable slot +0x40)
recolours the first two lights of the `TileData` at a position. It is
reached from `CNWCTile::SetMainLightColor` (call at 0x80d369), for area
tiles. `LoadBorder` makes six indirect calls: four to slot +0x38,
`SpawnTile` (0x70abe3, 0x70b06d, 0x70b4fc, 0x70b9ad), and two to the 2da
object's slot +0x8 after `C2DA::Unload2DArray` (0x70ba23, 0x70bac6). It
never calls `SetTileLights`. *Confirmed (asm).* Edge models keep no
lights anyway (T53).

**T55 The per-area border flag.** `CNWCArea::LoadArea` reads area +0x10c
(the flag of T49) with `CNWMessage::ReadBOOL` (0x710353-0x710358), inside a
branch taken only when `CNWCMessage::ServerSatisfiesBuild(0x2001, 0x24, 5)`
holds: servers from 8193.36.5. *Confirmed (asm for the read; the build test
from the v2 decompile).* `nwserver-linux` contains the area field name
`TileBrdrDisabled` and `CNWSVirtualMachineCommands::ExecuteCommandSetAreaTileBorderDisabled`
(0x6f79d0); that the BOOL is this field is inferred.

## Area transition triggers (T56-T59, `nwserver-linux`)

Decompiles in `nwserver-analysis/decompiled/walk-in-transition/` (v2
analysis) and `pathfinding/movement/WalkUpdateLocation.c`.

The server run cited below: a module of two 8 × 32 areas of a stock
tileset side by side, with 16 transition triggers (`Type` 1, 20 m × 1.5 m)
along the shared side of each, each `LinkedTo` a waypoint 4 m into the
other area (`LinkedToFlags` 2) facing away from the side; `nwserver-linux`
without NWNX; creatures (`nw_badger`) created 10 m from the side and told
`ActionMoveToLocation` to a point 0.2 m short of it, their area, position
and facing logged 8 s later.

**T56 Walking into a trigger runs only its OnEnter.** Entering a trigger
signals event 0xc to it. `CNWSTrigger::EventHandler` (0x5e3380) branches on
the event (0xc at 0x5e3b04, 0xd, 0xb, 0x18, 0x1e at 0x5e3b2c). For 0xc it
stores the entering object at trigger +0x3b0 (0x5e3f86) and runs
`OnEnterTrap` (0x5e3f9b) when the trigger is a trap (+0x3d4), else script
slot 1, OnEnter (0x5e4218-0x5e4222). Nothing else. *Confirmed (asm; server
run: a creature walking into a transition trigger with no OnEnter stood in
it and stayed in its area).*

**T57 A transition fires on event 0x1e, from a walk to the trigger.**
`CNWSCreature::WalkUpdateLocation` (0x496790) signals event 0x1e to the
creature's movement target when that target is a trigger, not a trap
(+0x3d4), and the creature is within its use range
(`CNWSCreature::GetIsInUseRange(target, 0.0, 0)`) (0x496b50-0x496bda).
`EventHandler` case 0x1e stores the creature at +0x3b0 (0x5e3b40), sets the
loading screen from +0x42c when the creature is a player, and runs script
slot 6, OnClick (0x5e3c3a-0x5e3c46); with no OnClick script, and a link,
the script it runs is `NW_G0_Transition`. *Confirmed (asm); the default
script name read in the v2 decompile.* A player's click on a trigger makes
it the movement target; that path was not run on the server
(`ActionMoveToObject` on a trigger walks to its first vertex and fires
nothing).

**T58 On a trigger, the entering and the clicking object are one field.**
`CNWSVirtualMachineCommands::ExecuteCommandGetEnteringObject` (0x6a3130)
returns trigger +0x3b0 for an object of type 7 (trigger), the field both
events write (T56, T57); there is no separate implementation of
`GetClickingObject` in the binary. *Decompile; confirmed by the server
run:* a creature walking into a trigger whose OnEnter is
`nw_g0_transition` arrived at the linked waypoint in the other area.

**T59 Jumping to a waypoint takes its facing.**
`CNWSCreature::AIActionJumpToObject` (0x4b28b0), for a waypoint target,
takes the waypoint's position and orientation and calls
`CNWSObject::SetOrientation` with that orientation before moving the
creature, into another area with `AddToArea` when needed. *Decompile;
confirmed by the server run:* the creature of T58 arrived facing 0 (east)
at a waypoint whose orientation was (1, 0).

## Tiles and edge tiles seen in game (T60-T64, `nwmain-linux`)

The client run cited below: NWN:EE 89.8193.37-17 (`nwmain-linux` of
engine/README.md), single player (`+TestNewModule`), drawn with Mesa's
llvmpipe in an off-screen X display at 1280 × 720, edge tiles on, the
camera placed by `SetCameraFacing` and each picture taken 10 s after a
jump. The areas were generated by nwn-landscaper (master `fff4987`) from
one height field of 30 × 30 tiles:

- a **reference area**: a 20 × 20 tile export, as generated;
- a **10 × 10 area** from its middle, whose tiles are the reference
  area's (same meshes, materials, baked shadow maps). Variants of it:
  - *overhang*: each boundary tile carries, as extra trimesh nodes
    (`parent` the tile, `position` the offset), the meshes of the
    reference area's tiles that lie outside the area and nearer to it
    than to any other boundary tile: every cell up to 50 m out. Every
    row of its edge 2da has `Model` `****`.
  - *per-position edge models*: no extra nodes; each edge strip model is
    the meshes of the reference area's tile just beyond its cell, each
    corner block model the diagonal one (south and north strips turned
    -90° in the model, against the strip's rotation 1).
- each area twice, with `FogClipDist` 45 and 90; no skybox, sun fog
  amount 0, sun fog colour `0x00917F68`.

**T60 Tile meshes outside their cell are drawn, lit and fogged.** In the
overhang area the extra meshes are drawn out to 50 m past the area's edge,
from low and high cameras over three sides and a corner. Within that
distance the pictures match the reference area's from the same spot: no
step in brightness, paint or height at the area's edge, and they fade with
distance like the area's own tiles. *Confirmed (in game).* Whether a mesh
stays while its tile's own cell is off screen (a turning camera) was not
filmed; the code says it does (T52).

**T61 An edge row whose model is `****` draws nothing.** In the overhang
area nothing is drawn past the extra meshes: the background shows there,
in every picture. *Confirmed (in game).* This settles the inferred part
of T46.

**T62 Edge models are drawn darker than the same meshes as area tiles.**
In the per-position area the edge models are visibly darker than the same
ground drawn as area tiles in the reference area, from the same camera;
the area tiles next to them are not. *In game; consistent with T54 (edge
models get no tile light colours).* The same run shows edge models
without a walkmesh drawn (the generator ships none; T50).

**T63 How far the client draws follows `FogClipDist`.** Two areas that
differ only in `FogClipDist` (45 and 90), seen from the same spot and
camera: in the first the ground fades into the fog colour about 45 m from
the camera, in the second about 90 m, with sun fog amount 0 in both.
*Confirmed (in game).* That area +0x108 holds the value is still inferred
(T55, unknown.md).

**T64 Past the drawn geometry the client shows the fog colour.** With no
skybox, the background behind every picture of T60-T63 was (104, 126, 145)
against the sun fog colour (104, 127, 145). *Confirmed (in game, one
renderer).* With a skybox, not checked.


## Walkmesh offset and surface materials (T65-T67)

Decompiles and notes in `nwserver-analysis/decompiled/surface-material/`
(with the run's scripts in `repro/`) and
`nwmain-analysis/decompiled/footstep/` (v2 analyses).

The server run cited below: a NWN Landscaper area of 10 × 10 tiles
(rolling ground, a river, a road, several walkable materials;
nwn-landscaper fff4987), on `nwserver-linux` without NWNX and with no
player; creatures (`nw_commale`, event scripts cleared) told
`ActionMoveToLocation` to random points 4-12 m away, one after another,
their position logged every 20 ms; and `GetGroundHeight` and
`GetSurfaceMaterial` sampled on a 0.5 m grid over four tiles. Each was
run with the area's walkmeshes as exported (`position 0 0 0`) and with the
same walkmeshes rewritten without the `position` line.

**T65 A walkmesh with no `position` line is not centred.**
`CNWTileSurfaceMesh::LoadWalkMesh` (0x441820) sets the offset to
(0, 0, 0) (0x441965-0x441979). Only a `position` line (compared at
0x441a67, read at 0x441ffc) replaces it, with (px + 5.0, py + 5.0, pz)
(the 5.0 at 0xb31908, added at 0x442009-0x442035). So a walkmesh authored
at -5..5 with no `position` line keeps those coordinates: only the
tile's south-west quarter (0..5, 0..5) has ground, the walkmesh's
north-east quarter. *Confirmed (asm; server run):* with the line removed,
393 of 1,681 grid points had ground, all in that quarter, and their
heights matched the uncentred walkmesh (393 of 393); with
`position 0 0 0`, all 1,447 points over walkable faces matched the centred
one. With the line removed, 6-9% of the random walks ended at their goal,
against 83-91% with it, in each of six copies of the area; walks that
crossed a tile edge almost never did (1%). Creatures walked across the
three quarters with no ground at the tile's base height, and one, stepping
from there onto ground 3.6 m lower, crept at 0.03 m/s for 0.3 s before it
crossed (T66 has the step rule that likely causes this).

**T66 Walkable materials do not change movement.** On the server the
`surfacemat.2da` table is read in three places: `Walk` in `LoadWalkMesh`
(T7) and in `CNWSArea::PositionWalkable` (0x635440), and `LineOfSight` in
`CNWTileSurfaceMesh::GetLOSMaterials` (0x43f9c0). The walkable faces'
materials (mesh +0x90) are read by `CNWTileSurfaceMesh::GetSurfaceMaterial`
(0x4444f0) and by the line-of-sight tests `CheckAABBNode` (0x43ff10) and
`CheckAABBNodeOneWay` (0x440250). `CNWSArea::GetSurfaceMaterial`
(0x635380) is called only by `PositionWalkable` (whose only caller is
`CNWSDoor::GetNearestActionPoint`) and by the script command
`GetSurfaceMaterial`. None of these is on the move or route path, so two
walkable faces with different materials are walked and routed like faces
of one material. *Confirmed (code; server run: 54 steps across a material
change moved at 0.98 of the creatures' median speed).*

`CNWSCreature::WalkUpdateLocation` (0x496790) does treat height: when a
step's height change is outside ±0.001 (0x496914-0x49692c, constants at
0xb3d2d8 and 0xb3d2dc), it takes the step again with its distance d
multiplied by the x of `normalize(d, 0, dz)` (0x496a90-0x496ae8). *Read in
asm; untested.* The runs showed no slowdown on slopes up to a grade of 1,
so how this plays out is open (unknown.md).

**T67 The client uses a face's material for footsteps only.**
(`nwmain-linux`.) `CNWCArea::GetSurfaceMaterial` (0x703390) is called by
`CNWCCreature::PlayFootstep` (0x72ff90), `CNWCItem::UpdatePosition`
(0x7cfec0) and `CNWCTile::CreateMenuByID` (0x80c160). `PlayFootstep` takes
`surfacemat.2da`'s `Name` for the material under the creature, adds
`rand() % 3` when it is not empty, and plays the WAV in that column of
`footstepsounds.2da` for the creature's footstep type
(`CExoSound::Play3DOneShotSound` at 0x730404); `Visual` and `IsWater` go to
`CNWCCreature::DoFootstepVisual` (0x72f8d0), which loads a visual effect
model for the step. Nothing there moves the creature. *Confirmed (code).*
