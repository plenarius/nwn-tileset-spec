# The search inside a tile (`SET-INTRA`)

How the server finds a path across one tile of a route: the wrapper and
coarse mode, the IDA* search and its budget, the successors, the choice
of a crossing on the exit edge, and the line tests. Then what this means
for the shapes a walkmesh should have. All addresses in this file are
`nwserver-linux`; points are in the tile's canonical frame unless said.

The full expression-level description (the "edge already used" table, the
transposition table's eviction, the subdivision adjacency rule) is in
Landscaper `research/SPEC_INTRATILE.md`. The rules here are what an
implementation must get right to predict arrival.

## The wrapper

**SET-INTRA-001** `CNWSTile::PlotIntraTilePath` (0x68d730) fails at once
when the tile has no walkmesh. *Confirmed: T33.*

**SET-INTRA-002** It rotates the start, and either the goal (last route
tile) or every remaining route exit, to the tile's canonical frame for the
search, and back afterwards; the round trip can change a value by one
ulp, and the change stays. New points are rotated to world. *Confirmed:
T33.*

**SET-INTRA-003** It runs the search in **coarse mode** when the tile's
centre is more than 15 m from the request's start (squared distance >
225), the creature's +0x894 is 0 and it is not a possessed familiar.
Coarse mode searches level 0 only and makes no line tests on edges
(SET-INTRA-030). A simulator of NPC routes MUST apply the 15 m rule.
*Confirmed: T33 (gdb; the simulator applies it to every NPC and agrees
with every recorded route).* For player characters see unknown.md.

## The search

**SET-INTRA-010** The search (`CNWTileSurfaceMesh::PlotIntraTilePath`,
0x4496d0) is an iterative-deepening A* over level-2 triangles toward a
**goal box**: the goal point ± 1e-4 on the route's last tile, else the box
from SET-INTRA-040. A start on no walkable triangle fails at once.
*Confirmed: T34.*

**SET-INTRA-011** The first bound is the distance from the start to the
box plus 10.0; each later round adds 5.0. *Confirmed: T34.*

**SET-INTRA-012** A round that finds nothing when the bound is then above
40.0 gives up: the tile fails (and the tile route records a denial,
SET-ROUTE-030). The first bound is always tried, even above 40. So no
path of 40 m or more is found inside one tile (unless the first bound,
d + 10 for a start at distance d from the box, is larger). *Confirmed:
T34.*

**SET-INTRA-013** Work is counted in units: 12 per node expansion, 300 per
successor generation. A call's unit budget is the remaining microseconds
of the PlotPath call, at least 500. Out of budget, the search suspends with
its stack, bound and table and resumes on the next call. Units are
compared with a wall-clock budget, so where it suspends is not
deterministic; a simulator MAY run each search uninterrupted.
*Confirmed: T34 (the simulator runs searches uninterrupted and charges
time per line test, and agrees with every recorded route).*

## Node expansion

**SET-INTRA-020** A node is at the goal when it is inside the box
(inclusive), or, with a goal range set, a narrow box and depth > 0, within
the range of the goal point. Otherwise, with g the path length so far and
h the distance to the box, the node is cut when `g + h >= bound`, or when
the transposition table holds at least `bound - g` for its triangle; else
it stores `bound - g - 1e-4` and tries its successors in order.
*Confirmed: T35.*

**SET-INTRA-021** The first path inside the bound is returned, not the
shortest. *Confirmed: T35.*

## Successors

**SET-INTRA-030** A node's successors (`IntraTileDFSGenerateSuccessors`,
0x447b90) are, in this order:
1. the goal point, alone, if a line to it passes SET-INTRA-060;
2. else, on the last tile when the goal is on the walkmesh, the first
   corner of the goal box (on the start's side) a line to which passes,
   alone;
3. else, for level 0, then 1, then 2 (coarse mode: 0 only), the edges of
   the node's ancestor triangle at that level not yet used at a coarser
   level: through the edge's midpoint to the neighbour's centroid (or to
   the goal point when stepping into the goal's triangle). Outside coarse
   mode both legs must pass SET-INTRA-060. Within a level, sorted by leg
   length plus distance to the box, stable.
*Confirmed: T36.*

**SET-INTRA-031** A `TILE_END` edge is a successor only if its midpoint is
inside the goal box; a `NO_EDGE` edge never is. On a tile that is not the
route's last, the search therefore reaches the box only by a straight line
from a node, or through a border edge whose midpoint lies in the box.
*Confirmed: T36, T37.*

## Choosing the crossing

**SET-INTRA-040** On a tile that is not the route's last,
`GenerateBestIntraTileExit` (0x446800) picks the goal box on the exit's
edge. With n the number of the layout's exits on that edge and k the
number of them before this exit (lower coordinate), it takes from
[tables/exit_candidates.yaml](../tables/exit_candidates.yaml):

| n | step | inner | outer | half | fin |
|---|---|---|---|---|---|
| 1 (also 0 or 4+) | 1.0 | 2.0 | 4.0 | 5.0 | 0.45 |
| 2 | 0.5 | 1.0 | 2.0 | 2.5 | 0.225 |
| 3, k = 1 | 0.6 | 1.2 | 2.4 | 3.0 | 0.27 |
| 3, k ≠ 1 | 0.2 | 0.4 | 0.8 | 1.0 | 0.09 |

and five candidates on the edge: exit - outer, exit - inner, exit,
exit + inner, exit + outer. *Confirmed: T37.*

**SET-INTRA-041** Each candidate has an integer weight: 3 each; or, when
the route has at least two more tiles and turns, 1, 2, 3, 4, 5 rising
toward the side the route goes two tiles ahead; plus 1 for the candidate
whose bin (width 2 × step) holds the start's coordinate along the edge.
*Confirmed: T37.* The exact rule: Landscaper `research/SPEC_INTRATILE.md`
section 6.

**SET-INTRA-042** With R = max(0.1, radius), a candidate whose straight
line from the start is walkable on this tile and clear of non-walkable
faces, placeables, doors and creatures scores `weight × 6 × R × 7`.
Otherwise free space is probed inward from it, steps of R from 0.5 R up to
6.1 R: blocked at the first probe, the candidate is out; blocked later at
depth d, it scores `weight × d × 0.5`; never blocked, `weight × 6 × R`.
The highest score wins (ties to the earlier candidate). No candidate: the
tile fails. *Confirmed: T37.*

**SET-INTRA-043** The goal box is the winning candidate ± fin along the
edge and ± 1e-4 across it. *Confirmed: T37.*

**SET-INTRA-050** The crossing is chosen from the **current tile's**
walkmesh only, anywhere within the candidate spread (exit ± outer). The
next tile then starts there. If the chosen point is not on the next
tile's walkmesh, or not in the region the route expects, that tile's
search fails and the crossing is denied for the request (SET-ROUTE-031).
*Confirmed: T13, T37.*

**SET-INTRA-051** A writer SHOULD keep, for every exit routes can use, the
whole candidate spread (exit ± outer: ± 4 m on an edge with one exit, ± 2 m
with two, ± 2.4 m for the middle of three, ± 0.8 m for the others)
walkable on both sides of the edge and inside the exit's own region on
both sides, or keep other walkable ground out of the spread. Using layouts
with more exits on such an edge narrows the spread. *Confirmed: T13, T37
(corpus v1 cliff 4.0: every failure; corpus v2 and v3 generated with this
check, Landscaper `src/pathnode.rs` `crossing_breaks`).*

## Line tests

**SET-INTRA-060** An in-tile line test (`TestLineForWalkableOnTile`,
0x446620) clips the segment to the tile and walks the walkable triangles
from the clipped start toward the end (`ClippedLineSegmentWalkable`,
0x445300), at most 512 steps. It passes when it reaches the triangle
holding the end or leaves through a `TILE_END` edge; it fails on a
`NO_EDGE` edge, a start on no walkable triangle, or 512 steps. With "check
end" set, the end must also lie in the tile. Then the width test
(SET-INTRA-062), and outside coarse mode placeables, doors and creatures.
*Confirmed: T38.*

**SET-INTRA-061** A simulator SHOULD follow the clipping and edge-crossing
expressions of Landscaper `research/SPEC_INTRATILE.md` 7.4-7.5. They were
transcribed from the decompile, not checked instruction by instruction
(unknown.md). *Confirmed: T38 (simulator agreement).*

**SET-INTRA-062** The width test (`NoNonWalkPolysOnTile`, 0x445bf0) sweeps
a rectangle of half-width w along the segment, extended past the end by w
but not before the start, against the non-walkable faces in the z range.
When called with flag 0 and 0.1 < w <= 0.65, **w becomes 0.1**. Every
in-tile test passes flag 0, so for creatures of radius up to 0.65 m the
search tests a 0.1 m corridor, not the creature's width. Placing a created
creature (SET-ROUTE-050) uses the full width. *Confirmed: T38, T31.*

## Shapes the search handles badly

These rules come from recorded failures and the generator changes that
fixed them. They are guidance for writers; the engine behaviour behind
them is SET-INTRA-012, SET-INTRA-021 and SET-INTRA-050.

**SET-INTRA-070** A writer SHOULD NOT make walkable regions in which
getting from one point of a tile to another needs a long detour inside
that tile: U-shaped regions, a walkable ring round a blocked crest, a
narrow dead end split across tile edges or corners, a one-sample ledge
across a cliff. The search can spend millions of units on them, run out of
calls or give up, and routes through them fail on the server. *Confirmed
as observations: T39 (simulator and server).* Which shapes are safe in
general is open (unknown.md).

**SET-INTRA-071** A writer SHOULD give a recess (a cave mouth, an alcove)
open ground in front of it within the same tile, so that the recess is
part of that ground's region. A recess alone in its tile with only a slope
above it was not reachable from afar. *Confirmed as an observation: T40
(simulator and server, 8 of 8 routes after the fix).*

**SET-INTRA-072** A writer SHOULD check generated areas with a simulator
of these rules over many random routes before export: the corpus areas
whose routes the simulator predicted to fail failed on the server at the
predicted places. *Confirmed: conformance corpus; Landscaper
`research/FINDINGS.md`, "Generator fixes".*
