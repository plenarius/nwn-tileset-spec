# Changelog

Releases follow semantic versioning. Each entry says which engine build it
was read on and what changed in the engine's behaviour since the last one.

## Unreleased (build 89.8193.37-17)

- Engine findings T51-T55 (`nwmain-linux`): the scene's BSP covers the
  area and its 5-cell border ring; tile meshes are culled by their own
  bounding box, not by their cell; the 4th argument of `Scene::SpawnTile`
  (1 for edge tiles) deletes every non-mesh node; tile light colours reach
  area tiles only; the per-area border flag is read from servers of
  8193.36.5 on.
- Engine findings T56-T59 (`nwserver-linux`): walking into a trigger runs
  only its OnEnter script; a transition fires on event 0x1e when a walk to
  the trigger ends in its use range; on a trigger the entering and the
  clicking object are one field; jumping to a waypoint takes its facing.
  Shown in a server run of two areas joined by transition triggers.
- Rules SET-EDGE-061, SET-EDGE-062 (edge models keep only meshes and get
  no tile light colours) and SET-TILE-070 (tile meshes may reach outside
  their cell, within 50 m of the area).
- unknown.md: the meaning of `SpawnTile`'s 4th argument is settled (T53);
  new open items for meshes outside their cell in game, past the BSP ring,
  the fog clip distance, and transition triggers.

## 1.0.0 (build 89.8193.37-17)

First draft, from NWN Landscaper's research (2026-10-19 to
2026-10-20):
- spec text for the `.set` file, tiles and walkmeshes, path-node layouts,
  the tile route, the in-tile search and the client's edge tiles, with rule
  IDs; engine findings T1-T50;
- tables: the built-in path-node layouts (48 letters, 4 orientations each,
  dumped from the running server), the engine's pathfinding constants, the
  in-tile exit candidate table, the `.set` corner and edge indices;
- a route corpus: 1,000 routes over 25 generated areas (three generator
  revisions), walked by an NPC on the server, with a manifest saying how
  to regenerate each area and a standard-library comparison script.

Addresses from the research notes were normalised to objdump addresses and
checked against `nm` on both binaries; the constants in
`tables/constants.yaml` were read back from `nwserver-linux`.

Corrections to the research notes:
- the built-in layouts have up to 8 nodes (`r`), not 4; layouts `r` and
  `s` exceed the route search's 6 regions a tile (T20, spec/unknown.md).
