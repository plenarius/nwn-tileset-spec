# A move request and the tile route (`SET-ROUTE`)

What the server does with one creature's order to walk to a point in the
same area: the straight-line test, the tile route, replanning after a
failed tile, budgets, fallbacks and smoothing. The search inside a tile is
in [intra.md](intra.md). All addresses in this file are `nwserver-linux`.

The request's state lives in a `CPathfindInformation` ("pf" below); its
fields are named by offset where it helps. The rules cover NPCs; where PCs
differ it is said.

## The request

**SET-ROUTE-001** On the first call of a request,
`CNWSModule::PlotPathInArea` (0x54cc00) tests the straight line from start
to goal with `CNWSArea::TestDirectLine` (SET-ROUTE-002), using the
creature's radius (`pf+0x04`) and height (`pf+0x0c`), and keeps the result
for the request's later calls. Then:
- 1 (clear): the path is [start, goal], complete;
- -4: failed;
- -1 or -2: the tile route (`CNWSArea::PlotPath`, SET-ROUTE-020);
- -3: the grid path (SET-ROUTE-014) from the start;
- anything else: the fallback (SET-ROUTE-013).
*Confirmed: T21.*

**SET-ROUTE-002** `CNWSArea::TestDirectLine` (0x646920) returns 1 when
the line is clear; -1 when a tile's walkmesh blocks it (no walkable path
along it in some tile, or a non-walkable face within the creature's width
and the height range `[zmin - 0.1, zmax + 0.1 + height]`, or the radius
past the end reaching into an unwalkable bit of the next tile); -2 when a
placeable's or door's walkmesh blocks it; -3 when a creature does; 0 when
the line leaves the area. The tile walk uses SET-INTRA-060 per tile, and
the width test SET-INTRA-062. *Confirmed: T22.*

**SET-ROUTE-003** When the request has a goal range (`pf+0x58` > 0) and
the start is farther than that from the goal, the target of the straight
line and the fallback is pulled back toward the start to that distance
from the goal. *Confirmed: T21.*

## Budgets

**SET-ROUTE-010** An NPC's request gets 1000 µs a call
(`CNWSObject::AI_TIME_SLICE`, 0xb42034). *Confirmed: T23 (code; gdb).*

**SET-ROUTE-011** An NPC's request gets 100 calls. A plan still in
progress after the 100th call is abandoned for the fallback
(SET-ROUTE-013). *Confirmed: T23 (code); the simulator applies this cap
and agrees with every recorded route.*

**SET-ROUTE-012** A player-controlled creature's calls and budget come
from a module setting (module +0x45c): 0 gives 100 calls of 1000 µs, 1
gives 10 of 7000, 2 gives 5 of 12000, 3 gives 1 of 50000. *Confirmed: T23
(asm). Not exercised by any recorded route.*

**SET-ROUTE-013** The fallback, unless `pf+0x00` is set: a 6-step
bisection along start → target finds the farthest point P reachable by a
clear `TestDirectLine`, each test from the last point found (the start at
first), t starting at 0.5 with step 0.25, halving the step each time. The
path is [start, P], complete; no such point: failed. *Confirmed: T21.*

**SET-ROUTE-014** When the tile route fails while calls remain and the
target is within 20 m of the start (squared distance < 400), the next calls
run `CNWSArea::PlotGridPath` (0x648eb0) instead. *Confirmed: T21, T30.* A
simulator MAY model the grid path's end point only approximately: it
depends on time slices (T30, unknown.md).

## The tile route

**SET-ROUTE-020** `CNWSArea::PlotPath` (0x649b70) finds the start and goal
tiles (SET-TILE-001) and their regions (SET-NODE-011). Either tile outside
the area or without a walkmesh: failed. *Confirmed: T24.*

**SET-ROUTE-021** The route is found by iterative deepening
(`GenerateInterTilePath`, 0x644520). With m the Manhattan distance in
tiles from start tile to goal tile, the first search tries budgets m,
m + 2, …, m + 22 in turn and stops at the first that finds a route. No
route within m + 22: failed. *Confirmed: T25.*

**SET-ROUTE-022** Each search is a depth-first search over (tile x, tile
y, region) states (`InterTileDFS`, 0x644340), budget b:
- at depth 0 with b >= 3 the goal and budget checks are skipped;
  otherwise the goal state ends the search (unless denied,
  SET-ROUTE-032), and b < 1 fails;
- a state farther from the goal tile (Manhattan) than b fails;
- a state whose visited byte is already >= b fails; else the byte is set
  to b (the visited table persists across the budgets of one search);
- the successors (SET-ROUTE-023) are tried in order with budget b - 1.
*Confirmed: T26.*

**SET-ROUTE-023** The successors of (x, y, r)
(`InterTileDFSGenerateSuccessors`, 0x6431a0) are the exits of the tile's
layout, in table order, that region r owns and no denial blocks, at most
8 (the 9th ends the list): the neighbour across the exit's edge, entered
by SET-NODE-030. A neighbour outside the area, or with no region at the
entry point, is skipped. Each is scored:
- 1.0 if the segment from region r's node (world) to the goal point
  crosses the span along the edge centred on the exit and reaching to the
  nearer tile corner less 1e-4 (`CNWArea::IntersectLineSegments`,
  SET-ROUTE-060);
- else the larger of the cosines between node → goal and node → each end
  of the span (a vector shorter than 1e-4 on both axes is not
  normalised);
- 0 for an exit not on an edge;
and sorted by score, descending, keeping exit order on ties. *Confirmed:
T27.*

**SET-ROUTE-024** The route stores, for each tile but the last, the exit
point where it leaves that tile, in that tile's local real frame. *Confirmed:
T24, T27.*

**SET-ROUTE-025** The tiles of the route are then searched one at a time
(intra.md). When a tile completes, the next starts at the last point
found, with the coordinate across the crossed edge snapped to 0 or 10 (both
coordinates for a diagonal step). *Confirmed: T24.*

**SET-ROUTE-026** A call that runs out of budget returns "in progress".
The route, the denials, the points found and the in-tile search's state
carry over to the next call (the route search's bound is recomputed
there as m - 2).
*Confirmed: T24, T34.*

## Failed tiles

**SET-ROUTE-030** When the in-tile search fails on route tile T, a denial
(T, a, b) is recorded (`RemoveInterTileExit`, 0x645130): a is the exit
number (SET-NODE-020) of the point the search started from on T, b the
exit number of the route's exit from T, or 12 on the goal tile.
*Confirmed: T28.*

**SET-ROUTE-031** After a denial the points found are discarded and a new
route is searched from the **original start**, beginning at the budget
that found the last route (not at m). Denials accumulate for the whole
request and are never lifted: a crossing that failed once is not tried
again by that request. Only a route search that finds nothing ends the
tile route with failure. *Confirmed: T28; corpus v1 cliff 4.0 (one failed
crossing left no route to the plateau).*

**SET-ROUTE-032** A denial on tile T blocks, at depth 0, its exit b
(unless b is 12); deeper, exit b when the route entered T at exit a's point
(within 1e-4), and when that b is 12 the state has no successors at all.
The goal state is refused when the goal tile has a denial (a, 12) for the
exit the route entered by (`GoalMoveDenied`, 0x643060). *Confirmed: T28.*

## Completion

**SET-ROUTE-040** When the last tile completes, the points are smoothed
into waypoints (`SmoothPointsOnPath`, 0x6481e0), unless `pf+0x14` is set.
Smoothing shortcuts to the farthest later point with a clear
`TestDirectLine`, splits legs of 1.1 m or more into 1 m steps, and cuts
corners sharper than cosine 0.9. *Confirmed: T29; one input flag is
uninitialised (unknown.md).* Smoothing changes the waypoints, not whether
the creature arrives.

## Where a created creature stands

**SET-ROUTE-050** `CreateObject` places a creature with
`CNWSArea::ComputeSafeLocation` (0x645b60), search range 20 m: the asked
point if the horizontal segment of the creature's radius either side is
walkable and clear of non-walkable faces at full width, else the first
such point on square rings around it with a walkable line back. A
simulator of scripted routes MUST start from the placed point, not the
asked one. *Confirmed: T31 (two corpus starts within about 0.4 m of
non-walkable ground were moved).*

## Geometry

**SET-ROUTE-060** `CNWArea::IntersectLineSegments` (0x44e2e0) is
specified expression by expression in Landscaper
`research/SPEC_INTERTILE.md` 5.4 (vertical cases first, inclusive range
tests, no y test in the general case, NaN failing every test). A
simulator SHOULD reproduce it exactly: route scores depend on it.
*Confirmed: T32.*
