# Changelog

The spec is tagged per engine build. Each entry says which build it was
read on and what changed in the engine's behaviour since the last one.

## Unreleased (build 89.8193.37-17)

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
