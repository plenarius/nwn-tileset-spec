# Contributing

This repository describes what the game does with tilesets and areas.
Every statement about the engine needs evidence, and the text keeps what
is known apart from what is guessed.

## Evidence

A claim about the engine carries:

- **the build** it was read on (today 89.8193.37-17, Linux, commit
  26c6e573):
  - `nwserver-linux`, sha256 `d6d95282…8e051111d`, for everything the
    server does (`.set` loading as the server sees it, walkmeshes, path
    nodes, pathfinding);
  - `nwmain-linux`, sha256 `6d19c39b…5925e700`, for everything the client
    does (edge tiles, the client's `.set` parser);
  - full checksums in [engine/README.md](engine/README.md);
- **its evidence**, one or more of:
  - a function and address, and the binary. Use objdump/nm addresses (file
    virtual addresses). Ghidra loads the binary at 0x100000, so its
    addresses are 0x100000 higher: `CNWSArea::PlotPath` is 0x649b70 in
    objdump, 0x749b70 in Ghidra. Say which function, and what in it;
  - a recorded server run: a route in `conformance/routes/` (what was
    generated, what the creature did);
  - an in-game result: what was loaded, how, and what was seen;
  - gdb on the running server: what was read or called, and where;
  - data in the game's own files, named by resref (never copied here);
- **a status**:
  - **confirmed**: read in the code and checked (against the disassembly,
    under gdb, or by a simulator that agrees with recorded server runs),
    or shown by a server run or an in-game result;
  - **inferred**: follows from the code or the data, not shown directly;
  - **untested**: written down so it is not lost, not checked at all.

Only confirmed behaviour goes into normative text (MUST, SHOULD). Inferred
and untested behaviour goes into [spec/unknown.md](spec/unknown.md) or is
marked as such in [engine/behaviour.md](engine/behaviour.md), and is never
promoted without new evidence.

## Rule IDs

Each normative rule has an ID `SET-<AREA>-<NNN>`:

| Area | File | What |
|---|---|---|
| `FILE` | [spec/set.md](spec/set.md) | The `.set` file: text format, the keys the engine reads, what they mean |
| `TILE` | [spec/tile.md](spec/tile.md) | Tiles in an area: frames, rotation, heights, walkmesh loading and use |
| `NODE` | [spec/pathnode.md](spec/pathnode.md) | Path-node layouts, regions and exits |
| `ROUTE` | [spec/route.md](spec/route.md) | A move request, the tile route, replanning, smoothing, fallbacks |
| `INTRA` | [spec/intra.md](spec/intra.md) | The search inside one tile, the choice of a crossing, line tests |
| `EDGE` | [spec/edge.md](spec/edge.md) | The client's edge (border) tiles |

IDs are stable: never renumber or reuse one. Numbers leave gaps so a rule
can be added beside its neighbours. A rule that turns out wrong is marked
withdrawn, with the reason, and a new ID replaces it. Implementations may
cite IDs in comments and tests.

Engine findings are numbered `T1`, `T2`, … in
[engine/behaviour.md](engine/behaviour.md). The numbers are this
repository's own.

## Pull requests

- A change to normative text needs evidence: a recorded server run, or an
  engine citation with the build. Say which.
- A new pathfinding behaviour should come with routes that show it: an
  area anyone can regenerate, the routes walked on the server, and the
  results as JSON (see below).
- Tables change with the text that justifies them. Implementations
  generate their tables from `tables/`, so a table error spreads; check it
  twice.
- Write plainly. Short sentences, one claim each, the address or route
  next to it.

## Route corpora

1. Make the area reproducible: a generator revision, its settings and a
   seed, so anyone can rebuild the same walkmeshes, path nodes and tile
   heights. Do not commit `.mod` or `.hak` files.
2. Walk the routes on the server: one creature per route, created at the
   start, told to move to the goal, its position logged after a fixed time.
   Say how the creature was set up (see
   [conformance/README.md](conformance/README.md) for the current method).
3. Add the results under `conformance/routes/<corpus>/` and the case to
   [conformance/manifest.json](conformance/manifest.json).

## Assets

- No Beamdog game assets: no stock tilesets, models, walkmeshes, textures
  or BIF/KEY content. Refer to them by resref; tools extract them from the
  user's install.
- No third-party content, and nothing whose licence you cannot give as CC0.
- Engine decompiles are not copied here; cite them by path in the shared
  analysis folders ([engine/method.md](engine/method.md)).

## Licences

By contributing you agree that text you add is licensed CC-BY 4.0 and
tables, routes, code and data CC0 1.0 (see the README).
