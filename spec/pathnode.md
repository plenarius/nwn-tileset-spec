# Path-node layouts (`SET-NODE`)

The server's tile route does not read walkmeshes. It moves between
(tile, region) states using a built-in **layout** per tile: nodes (the
regions), exits on the tile edge, and which node owns each exit. A tile's
`.set` `PathNode` letter and `Orientation` choose its layout
(SET-FILE-010, SET-FILE-012). All addresses in this file are
`nwserver-linux`.

## The table

**SET-NODE-001** The layouts are those in
[tables/pathnodes.json](../tables/pathnodes.json): for each letter and
path-node orientation 0-3, the node positions, the exit points and each
exit's owning node, in the canonical frame. A simulator MUST use this
table; a writer choosing layouts MUST choose from it. *Confirmed: T15
(dumped from `CNWTileSetManager::ComputePathNodeInformation`, 0x3f3ea0,
under gdb).*

**SET-NODE-002** The four orientations of a letter are one layout rotated
about the tile centre: from the orientation-0 point (x, y), orientation 1
is (10 - y, x), 2 is (10 - x, 10 - y), 3 is (y, 10 - x), anticlockwise as
`RotateCanonicalToReal`. Exit order and owners are the same in all four.
*Confirmed: T15 (`ComputePathNodeRotation` 0x3f3df0; every letter of the
dump).*

**SET-NODE-003** Layouts exist for 48 letters: `A`-`Z` except `P` and `T`,
and `a`-`x`. They have 1 to 8 nodes and 1 to 12 exits, and every node owns
at least one exit. *Confirmed: T15.*

**SET-NODE-004** Every exit is one of 20 points on the tile edge: 1, 2.5,
5, 7.5 and 9 m along each side. *Confirmed: T15.*

## Regions

**SET-NODE-010** A tile's region is a node index of its layout.
*Confirmed: T16 (`CNWSTile::GetRegionCoords` 0x68d090 returns node r's
position).*

**SET-NODE-011** The region of a point is found so
(`CNWTileSurfaceMesh::FindClosestRegion`, 0x444870):
1. a tile with no walkmesh: 0; a layout with one node: 0;
2. find the level-0 walkable triangle under each node position, and
   under the point (SET-TILE-041);
3. the point on no walkable triangle: **0**;
4. from the point's triangle, search depth-first over adjacency: at each
   triangle not yet seen, if it is a node's triangle return that node
   (nodes in index order), else mark it seen and visit its neighbours
   `a0`, `a1`, `a2` that are >= 0, in that order;
5. nothing found: the node nearest to the point by squared distance,
   ties to the lower index.
A simulator MUST follow this order: the first node triangle reached wins,
not the nearest node. *Confirmed: T16.*

**SET-NODE-012** A writer SHOULD place each node of a tile's layout in its
own walkable component, and every walkable component that routes use
should hold exactly one node. Otherwise the region of a point depends on
triangle order (SET-NODE-011), and the server has crashed on such tiles.
*Confirmed: T16 (code), T19 (in game, the crash).*

## Exits

**SET-NODE-020** A point's exit number is the first exit whose span holds
it. An exit on a north or south edge spans x within `min(ex, 10 - ex)` of
the exit and y within 1e-4; an exit on an east or west edge the same with
the axes swapped; a corner exit gets both spans. No exit: 12
(`UNKNOWN_TILE_EXIT`, which equals `GOAL_TILE_EXIT`). *Confirmed: T18
(`GetExitNumber` 0x440a50).*

**SET-NODE-021** Exit numbers are used only to record and match denials
(SET-ROUTE-030). *Confirmed: T18, T28.*

## How tiles connect

**SET-NODE-030** Two tiles connect for the tile route only where the
neighbour's layout has an exit at the same point as the current tile's
exit (within 1e-4 on both axes), after both tiles' rotations: the entry
point is the exit point with the coordinate across the edge wrapped (10 to
0, 0 to 10), rotated to the neighbour's canonical frame, and the region
entered is that exit's owner. *Confirmed: T17 (`GetRegionEntrance`
0x440cb0, `CNWSTile::GetRegionEntrance` 0x68d120), T27.*

**SET-NODE-031** From region r a route can leave only through the exits r
owns, and it enters only the region owning the matching exit. Walkable
ground between regions or between tiles that no pair of matching exits
joins is invisible to the route; ground joined by exits but not walkable
fails only when the in-tile search tries it. A writer SHOULD therefore
choose layouts so that:
- two exits share a node only if the walkmesh joins them;
- every walkable component touching an edge where routes cross is owned
  by a node with an exit there, or is made non-walkable;
- where a walkable component reaches the neighbour, both layouts have an
  exit at the same point.
*Confirmed: T13, T16, T17 (code); corpus v2 and v3 (Landscaper
`src/pathnode.rs` chooses layouts so, and prunes components no node owns:
198 of 200 v2 routes and all 80 v3 cliff routes arrived, and the two v2
failures were predicted by the simulator).*

**SET-NODE-032** The tile route plans on the layout alone; it never reads
the walkmesh between two exits of one node. Whether a creature can cross a
tile between them is decided only when the in-tile search runs
(intra.md). *Confirmed: T24, T27.*
