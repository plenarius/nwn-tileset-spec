# Observed, inferred and unknown

Nothing on this page is normative. Each item says what is known, how, and
what would settle it. Addresses are objdump addresses in `nwserver-linux`
unless marked.

## The .set file

- **Why LF line ends crash** (T1). The crash is confirmed; the research
  notes put the overflow in `CResSET::CreateSectionTable` (0x43ee30). The
  function was not read for this repository. *Settle:* read it, or run the
  server under gdb on an LF-only `.set` and take the backtrace.
- **Letters without a layout.** `P` and `T` give 0 nodes and 0 exits
  (T15), and characters between `Z` and `a` were not tried. What a tile
  with such a letter does in the planner (region 0 of an empty layout, no
  exits) is untested. *Settle:* a tileset with one `P` tile and routes
  across it.
- **Every invalid `Orientation` crashes** (T2): only 1, 2 and 3 were
  tried. That 45 or 100 crash too follows from the code (they convert to
  4): inferred.
- **The `WalkMesh` key.** Every corpus tile writes `WalkMesh=msb01` and has
  its own `.wok` named after its `Model`, and the server used the per-tile
  walkmeshes (the simulator, which loads them, agrees with every recorded
  route). So the server loads the walkmesh named by `Model`, not by
  `WalkMesh`: inferred. `CNWTileSurfaceMesh::SetWalkMesh(CResRef)`
  (0x441800) was not traced. *Settle:* read its callers in the server's
  tileset loader (`CNWTileSet::LoadTileSet`, 0x43cec0).
- **The store of the path-node orientation** (walkmesh +0x34) was not
  traced; its value (`ConvertToTileOrientation` of the `.set` degrees) and
  its use are certain. Likewise that the server's tile +0x24 is the area's
  `Tile_Orientation` (the client's is: `CNWCTile::SetOrientation`,
  `nwmain-linux`). *Settle:* gdb, read +0x32/+0x34 of the walkmesh and
  +0x24 of the tile for a known rotated tile.

## Tiles and heights

- **Tile z = `Tile_Height × Transition`** (T12). The line tests add tile
  +0x10; the simulator sets it to `Tile_Height × Transition` and agrees
  with the server, and every corpus walkmesh is written relative to that
  base. The store was not read (`CNWTile::SetPosition(int, int, int,
  float)`, 0x44c0d0, is the likely site). *Settle:* read SetPosition's
  caller, or gdb.
- **Ground far from the tile's base.** Landscaper's notes say pathing
  across tiles failed once ground strayed about 2.5-4 m from
  `Tile_Height × Transition` (`src/main.rs`, `tile_level`). Not
  isolated; untested as a rule. The corpus areas choose each tile's height
  as the rounded mean ground height in transition steps.
- **Rotated tiles.** Every corpus tile has `Tile_Orientation` 0. The
  rotations (SET-TILE-003) are read in code, and the round trips of exits
  through them can change a value by one ulp (SET-INTRA-002); whether any
  later code compares those values with `==` was not checked. *Settle:*
  route corpora over areas with rotated tiles.
- **Binary walkmeshes.** `LoadWalkMesh`'s binary branch reads normals and
  planes from the file; not covered.
- **Missing `surfacemat.2da` rows.** If `C2DA::GetINTEntry` fails it does
  not write, so a face would inherit the previous face's `Walk` (for face
  0, a stale value). Read in code; untested. *Settle:* a walkmesh with an
  out-of-range material, then inspect the non-walkable face count.
- **Dense walkmeshes.** Landscaper's first walkmeshes (before RTIN
  simplification) left searches in progress until the call cap; RTIN-simplified
  ones of ~320 faces finish in one call (T14). The boundary is not known,
  and region shape matters more (T39).

## Path nodes

- **The crash with nodes in one component** (T19) is confirmed; nothing
  in the code read for T16 explains it (the search is bounded by the seen
  flags). *Settle:* reproduce under gdb and take the backtrace.
- **More than six regions** (T20). The visited table has 6 bytes a tile;
  layouts `r` (8 nodes) and `s` (7) exceed it, so regions 6 and 7 of tile
  (x, y) would share bytes with regions 0 and 1 of tile (x, y + 1).
  (Landscaper's research notes said the maximum was 4 nodes; the dumped
  table shows otherwise.) Inferred; untested. *Settle:* a route over an
  `r` tile whose region 6 or 7 matters.
- **How well stock tiles fit the layout model.** Landscaper's
  `validate-pathnodes` finds 74-84% of the stock tiles it checked
  consistent with "nodes join only edge points their walkmesh joins"
  (with exits snapped up to about 1.25 m); the rest look like loose hand
  assignments. Observed on stock tilesets by resref; not a rule.

## The tile route

- **Denials with a = 12 deeper than depth 0.** `GetExit(12)` writes
  nothing, so the comparison point is a stale stack value (in practice the
  last `GetExit` result). The simulator treats it as no match. *Settle:*
  fail an in-tile search on the start tile, then make a route re-enter
  that tile; log the stack slot at 0x643a69.
- **Smoothing's first pass.** `SmoothSelection` passes an uninitialised
  register (r9d) as the first pass's subdivide flag. If it is non-zero,
  the raw path is split into 1 m steps before shortcutting. Waypoint shape
  only. *Settle:* gdb at `SmoothSelectNodes` (0x647c30), log r9d on the
  first call from 0x648155.
- **`pf+0x14` (no smoothing), `pf+0x74` (start and end flipped),
  `pf+0x1a0`, creature +0x7c**: who sets them was not traced. All were 0
  for the corpus's scripted NPC moves (gdb). A flipped request would
  change which tiles are coarse (SET-INTRA-003).
- **Grid path end points** depend on its time slices; one corpus route
  ended 3 m from the server's end point (same arrival).
- **Time model.** The simulator charges about 0.7 µs per line test,
  fitted to three gdb-counted requests (55 and 42 calls for two heavy
  searches, 1 for a coarse one). Only heavy searches depend on it.
- **Placeables, doors and other creatures.** `CNWArea::NoNonWalkPolys`
  (placeable and door walkmeshes, `NoNonWalkPolysDetailed`) and
  `CNWSArea::NoCreaturesOnLine` (0x6447a0) are called by the line tests
  but not specified here. The corpus has none of them in the way
  (ghosted creatures, no placeables). `pf+0xc8`, passed to
  `NoNonWalkPolys`, is not analysed.

## The in-tile search

- **Player characters.** Coarse mode depends on creature +0x894, assumed
  to mean "is a player character", so PCs would never search coarsely.
  Not checked with a PC.
- **`allin` in `NoNonWalkPolysOnTile`** (stack at rbp-0x8c..-0x84, asm
  0x4460f8). The flags are only ever cleared, never set to 1, so "a
  non-walkable face entirely inside the test rectangle" blocks only if
  stale stack bytes equal 1. The simulator treats them as 0. *Settle:* gdb
  at 0x446159, dump the three ints over many calls.
- **Stale z range in the crossing probes.** When the clipped line walk
  fails before writing its z range, `GenerateBestIntraTileExit`'s probes
  use the previous candidate's range (or uninitialised stack for the
  first), widened by ± 20.01 m, so it rarely matters. *Settle:* break at
  0x447064, log rbp-0x88 and rbp-0x84.
- **Expression order** of `ComputeClippedLineSegment` (0x443810) and the
  mesh's `IntersectLineSegments` (0x444e20) was taken from the decompile,
  not checked instruction by instruction. Arrival agrees on every route.
  *Settle:* compare with the server on random segments with gdb `call`.
- **Time slicing.** Where a search suspends depends on the wall clock.
  A resumed search can differ from an uninterrupted one when the goal box
  moves between slices (creatures), when re-stores on the re-descent evict
  a different transposition-table slot, or when a failed round straddles a
  time-out. Second-order; the simulator ignores it.
- **Which region shapes are safe** (T39). Observed: U-shaped regions,
  rings round a blocked crest, narrow dead ends across tile edges or
  corners, one-sample ledges. That the cost comes from the IDA*
  re-exploring detours each round is inferred from the code. No general
  criterion is known. A candidate: compare each in-tile crossing's
  shortest walkable path with the straight line, or cost each crossing
  with a simulator (Landscaper's `check-tiles` lists crossings over
  200,000 units).
- **Why a lone recess gets no crossing** (T40). Not traced. A guess
  consistent with SET-NODE-031 and SET-INTRA-031: alone in its tile, the
  recess is a region whose exits do not line up with walkable ground the
  route can reach, so the tile route never plans into it. Untested.

## Edge tiles (`nwmain-linux`)

- **The gate's names.** That the first client option is the "edge tiles"
  graphics setting, and area +0x10c the server's per-area "tile border
  disabled" flag (`SetAreaTileBorderDisabled`), is inferred from the
  flag's source (read from the server's area message in
  `CNWCArea::LoadArea`, 0x710353-0x710358).
- **An empty model draws nothing** (T46): inferred. The miss still calls
  `Scene::SpawnTile` with `""`.
- **The 4th argument of `Scene::SpawnTile`** (1 for edge tiles, 0 for
  area tiles; stored at TileData +0x54) has an unknown meaning.
- **`ReloadBorder`** (0x711ff0) was read in the decompile only: it applies
  the same gate, deletes each cell's model with `Scene::DeleteTile`
  (0x4636a0) and spawns again, with rotation 0 on a miss.
- **The absolute sense of rotation** (anticlockwise from above) is the
  usual `Tile_Orientation` convention; it was not re-derived (the yaw
  axis is a runtime-initialised vector). Not needed to match area tiles.
- **Name lengths.** The 2da name is built from the tileset resref plus
  `_Edge` and turned into a 16-character `CResRef`; whether a longer name
  is truncated or fails was not checked. Model names are resrefs (16
  characters). A tileset resref of at most 11 characters keeps the 2da
  name within 16.
- **The server and border cells.** `LoadBorder` is client code; that the
  server has nothing for border cells (no walkmesh, no pathing) is
  inferred.
- **Stock edge models are symmetric** across their local y axis, as
  shared rows on opposite strips require (SET-EDGE-043): inferred, not
  surveyed.
