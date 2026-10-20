# NWN:EE tilesets and areas: specification and route corpus

A shared, evidenced description of how Neverwinter Nights: Enhanced Edition
uses tilesets and areas: the `.set` file, tile models and walkmeshes as an
area places them, tile heights, path nodes, the server's pathfinding across
and within tiles, and the client's edge (border) tiles. With a corpus of
routes walked on the real server that any implementation can check itself
against.

**Status:** draft, read on engine build 89.8193.37-17 (Linux
`nwserver-linux` and `nwmain-linux`, commit 26c6e573). Nothing here is
official: it is what the game was seen to do, with the evidence for each
claim. The corpus holds 1,000 routes over 25 generated areas.

## Why

Tools that build areas from scratch (terrain generators, tileset makers,
area editors) need to know what the server does with what they write. The
toolset hides most of it; the rest is folklore. Three examples, each of
which cost a crash or a broken area before it was understood:

- a `.set` file with LF line ends crashes the server (SET-FILE-001);
- a tile's `Orientation` is in degrees: 1, 2 or 3 crashes the pathfinder
  (SET-FILE-010);
- tiles only connect for pathing where both path-node layouts have an exit
  at the same point, whatever the walkmeshes say (SET-NODE-030).

The server's pathfinder is also strict in ways that matter to anyone
generating walkmeshes: it picks a tile crossing from one tile's walkmesh
only (SET-INTRA-050), gives up an in-tile search after a fixed bound
(SET-INTRA-012), and once a crossing fails, it does not try it again for
that request (SET-ROUTE-031). A generator that does not respect this makes
areas where creatures stop at cliff feet.

## What is here

| Folder | What it is |
|---|---|
| [spec/](spec/) | The normative text: the `.set` file, tiles and walkmeshes, path-node layouts, the tile route, the in-tile search, edge tiles. Every rule has a stable ID (`SET-NODE-012`) and cites its evidence. |
| [engine/](engine/) | What the engine does, finding by finding (T1, T2, …), with function addresses, build and status (confirmed, inferred, untested). The spec's evidence. |
| [tables/](tables/) | Machine-readable data (CC0): the built-in path-node layouts for every letter and orientation, the engine's constants, the in-tile exit candidate table, the `.set` corner and edge indices. Generate your tables from these. |
| [conformance/](conformance/) | Routes walked by a creature on the real server over generated areas (CC0), a manifest saying how each area is made, and a comparison script. |

## How it relates to nwn-mdl-spec

This is a sibling of [nwn-mdl-spec](../nwn-mdl-spec/), which describes the
model files (`.mdl`) themselves, walkmesh nodes included. This repository
starts where that one stops: what the server and client do with a tile's
model and walkmesh once a `.set` and an area place them. It follows the same
conventions: the same evidence rules, statuses and licences, rule IDs of the
same shape (`SET-<AREA>-<NNN>` here, `MDL-<AREA>-<NNN>` there) and objdump
addresses throughout.

## The reference implementation

Layonara Landscaper's simulator (`src/sim/`, to be published) is the
reference implementation of the pathfinding rules. It is an offline port of
`CNWSModule::PlotPathInArea` for NPCs, written from the findings here, and
it agrees with the server on whether the creature arrived for every route
in [conformance/](conformance/) (with the area regenerated at the
landscaper revision the manifest names). Landscaper's generator is also
what made the corpus areas.

## Using the corpus

Your implementation needs to load an area (tile walkmeshes, path-node
letters and orientations, tile heights) and answer one question per route:
does a creature starting at `from` and told to walk to `to` arrive? Write
your answers as JSON and run:

```sh
python3 conformance/tools/compare.py --predictions my-predictions/
```

The areas themselves are not in this repository: they are regenerated with
Landscaper at the revision and settings the manifest gives. See
[conformance/README.md](conformance/README.md).

## Evidence

Every claim about the engine names the build it was read on, its evidence (a
function and address, a recorded server run, or an in-game test) and a
status: **confirmed**, **inferred** or **untested**. Only confirmed
behaviour is normative; the rest is in [spec/unknown.md](spec/unknown.md).
[engine/behaviour.md](engine/behaviour.md) has the findings themselves.
[CONTRIBUTING.md](CONTRIBUTING.md) has the rules.

### Not done yet

- Rotated tiles: every corpus area places its tiles with orientation 0.
  The rotation rules are read in code and their arithmetic checked, but no
  recorded route crosses a rotated tile.
- Player characters: the corpus walks NPCs. PCs get other call caps and no
  coarse mode (SET-ROUTE-012, SET-INTRA-003); neither was exercised.
- Placeables, doors and other creatures on the line tests: read as calls,
  not specified (spec/unknown.md).
- The Windows build: everything here was read on the Linux build.

### Versioning and governance

The spec is tagged per engine build, with a changelog of behaviour that
changed between builds ([CHANGELOG.md](CHANGELOG.md)). A change to
normative text needs evidence: a recorded server run, or an engine citation
with the build. The repository is meant to belong to no single tool.

## Licences

- Text (`spec/`, `engine/`, the Markdown files): [CC-BY 4.0](LICENSE-TEXT).
- Tables, the route corpus, the manifest and the scripts: [CC0 1.0](LICENSE-DATA).
  The routes are our own measurements of the server walking our own
  generated areas.
- **No Beamdog game assets are in this repository.** Stock tilesets,
  models, walkmeshes and creatures are named by resref, never copied. The
  path-node table is numbers the engine computes, dumped from the running
  server.

## Related

- [nwn-mdl-spec](../nwn-mdl-spec/) — the model format, walkmesh nodes
  included.
- [nwn.wiki](https://nwn.wiki) — the community wiki; its tileset pages
  describe the `.set` keys for builders. This repository links to it rather
  than duplicating it.
