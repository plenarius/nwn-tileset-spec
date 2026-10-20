# The specification

What a Neverwinter Nights: Enhanced Edition tileset is, and what the game
does with it when an area places its tiles, written so a tileset writer, an
area generator or a pathfinding simulator can be built from it.

**Build:** 89.8193.37-17 (Linux `nwserver-linux` and `nwmain-linux`,
commit 26c6e573). Every rule was read on this build. A later patch may
change behaviour; the changelog records what changed and when.

| File | Rules | What |
|---|---|---|
| [set.md](set.md) | `SET-FILE-*` | The `.set` file: line ends, orientation, path-node letters, corner and edge keys |
| [tile.md](tile.md) | `SET-TILE-*` | Tiles in an area: frames and rotation, how a walkmesh is loaded, adjacency, subdivision, point lookup, tile heights, shared edges |
| [pathnode.md](pathnode.md) | `SET-NODE-*` | Path-node layouts, regions, exits, how tiles connect |
| [route.md](route.md) | `SET-ROUTE-*` | A move request: the direct line, the tile route, denials and replanning, budgets, fallbacks, smoothing, where a created creature stands |
| [intra.md](intra.md) | `SET-INTRA-*` | The search inside one tile, the choice of a crossing, line tests, region shapes |
| [edge.md](edge.md) | `SET-EDGE-*` | The client's edge (border) tiles |
| [unknown.md](unknown.md) | — | Observed, inferred or unknown behaviour, and open questions. Not normative. |

## Reading the rules

Each rule has an ID, a statement, and its evidence:

> `SET-NODE-030` Two tiles connect for the tile route only where the
> neighbour's layout has an exit at the same point as the current tile's
> exit (within 1e-4), after both tiles' rotations. *Confirmed: T17.*

- **MUST** / **MUST NOT**: what the engine does, and what an
  implementation has to do to match it (a simulator), or what a writer has
  to do for the engine to accept its output (a tileset or area generator).
- **SHOULD**: what a writer does to get areas the engine paths well, where
  the evidence is a recorded failure and its fix; or engine behaviour that
  is a defect an implementation may avoid where it says so.
- **MAY**: explicitly allowed variation.

"Writer" means anything that writes `.set` files, tile walkmeshes or area
tile lists; "simulator" anything that predicts what the engine does with
them. Rules about what the engine does are statements of fact with their
evidence; rules for implementations follow from them.

Evidence names an engine finding (`T12`, in
[engine/behaviour.md](../engine/behaviour.md)), a route corpus
([conformance/](../conformance/)), or a function and address (objdump
addresses; Ghidra adds 0x100000). Behaviour that is only inferred is not
stated as a rule: it is in [unknown.md](unknown.md).

## Words

- **tile frame, local**: metres from the tile's south-west corner, x east,
  y north, 0..10.
- **canonical frame**: the frame the walkmesh and the path-node layout are
  authored in; the local frame rotated back by the tile's placement
  orientation (SET-TILE-003).
- **layout**: the built-in path-node record for a letter and orientation:
  nodes, exits, and each exit's owning node
  ([tables/pathnodes.json](../tables/pathnodes.json)).
- **region**: a node index of a tile's layout. The tile route moves between
  (tile, region) states.
- **exit**: a point on a tile's edge in its layout.
- **crossing**: the point where a route actually crosses from one tile to
  the next, chosen near an exit (SET-INTRA-040).
- **request**: one move order of one creature, from its first planner call
  to completion or failure.
- **call**: one invocation of `CNWSModule::PlotPathInArea` for a request,
  with a time budget.
- **unit**: the in-tile search's work counter (SET-INTRA-013).
- **component**: a set of walkable faces connected by adjacency
  (SET-TILE-030).
- **EPSILON**: `CNWArea::EPSILON`, 1e-4 (f32 0x38d1b717). **MIN_TILE_EPS**
  1e-4, **MAX_TILE_EPS** 9.9999 (f32 9.99989986). See
  [tables/constants.yaml](../tables/constants.yaml).

All engine arithmetic in the pathfinder is IEEE single precision with
plain SSE scalar operations (no fused multiply-add), evaluated in the order
written, unless a rule says double. A simulator that wants the server's
exact numbers follows the same order.
